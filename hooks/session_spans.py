"""Claude Code hook: one span per session event, so AI Center can link sessions to git branches.

Sends ids, the remote host and owner/repo, and the branch only: never prompts, tool input or
output, local paths, or credentials.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlsplit

DOMAIN_OPTION = "CLAUDE_PLUGIN_OPTION_CORALOGIX_DOMAIN"
SEND_DATA_KEY_OPTION = "CLAUDE_PLUGIN_OPTION_CORALOGIX_SEND_DATA_KEY"
SENDER_ARGUMENT = "--send"
LAST_ERROR_FILE = "session_spans_last_error.txt"

AGENT_NAME = "claude-code"
SERVICE_NAME = "claude-code-hook"
# Coralogix routes spans of this source type to the Claude Code spans dataset.
SOURCE_TYPE = "claude_code_agent"
SPAN_NAME_PREFIX = "agent_hook."
SPAN_KIND_INTERNAL = 1
# W3C trace context: version-traceid-parentid-flags.
TRACEPARENT_PATTERN = re.compile(r"[0-9a-f]{2}-([0-9a-f]{32})-([0-9a-f]{16})-[0-9a-f]{2}")
# The variables that turn Claude Code tracing on, and the values it reads as on.
TRACING_FLAGS = ("CLAUDE_CODE_ENHANCED_TELEMETRY_BETA", "ENABLE_ENHANCED_TELEMETRY_BETA")
ON_VALUES = ("1", "true", "yes", "on")
# Events outside a turn: Claude Code sets no turn span for them.
NO_TURN_EVENTS = ("SessionStart", "SessionEnd")

EDITED_FILE_KEYS = {
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "Write": "file_path",
    "NotebookEdit": "notebook_path",
}

GIT_TIMEOUT_SECONDS = 5
SEND_TIMEOUT_SECONDS = 5


def main() -> None:
    raw_domain = os.environ.get(DOMAIN_OPTION, "")
    send_data_key = os.environ.get(SEND_DATA_KEY_OPTION, "").strip()
    if not raw_domain.strip() or not send_data_key:
        return
    domain = coralogix_domain(raw_domain)
    if not domain:
        record_error("coralogix_domain is not a domain such as eu2.coralogix.com")
        return
    # Bytes: on Windows, Python before 3.15 decodes piped text with the ANSI code page.
    event = json.loads(sys.stdin.buffer.read())
    if sys.argv[1:] == [SENDER_ARGUMENT]:
        send(domain, send_data_key, traces_payload(event, span_attributes(event)))
        return
    fields = hook_fields(event)
    if fields:
        start_sender(fields)


def coralogix_domain(value: str) -> str:
    """eu2.coralogix.com from what users paste: a URL, a trailing slash, or the ingress host."""
    domain = value.strip().lower().split("://")[-1].strip("/")
    if domain.startswith("ingress."):
        domain = domain[len("ingress.") :]
    is_host = "." in domain and all(c.isascii() and (c.isalnum() or c in ".-") for c in domain)
    return domain if is_host else ""


def hook_fields(event: dict) -> dict | None:
    """Only what the span needs leaves this process: never the prompt or the tool input."""
    session_id = event.get("session_id")
    hook_event = event.get("hook_event_name")
    if not isinstance(session_id, str) or not session_id:
        return None
    if not isinstance(hook_event, str) or not hook_event:
        return None
    fields = {
        "session_id": session_id,
        "hook_event": hook_event,
        # The event time: the sender can start late and spend seconds in git.
        "time_unix_nano": str(time.time_ns()),
        "directory": edited_file_directory(event) or event.get("new_cwd") or event.get("cwd"),
        "traceparent": turn_traceparent(hook_event),
    }
    if hook_event == "PostToolUse":
        fields["tool_name"] = event.get("tool_name")
    return fields


def turn_traceparent(hook_event: str) -> str | None:
    """Claude Code sets TRACEPARENT to the turn's span only during a turn with its tracing on.
    Otherwise the hook inherits TRACEPARENT from the shell, which names an unrelated trace."""
    tracing = any(os.environ.get(flag, "").strip().lower() in ON_VALUES for flag in TRACING_FLAGS)
    if not tracing or hook_event in NO_TURN_EVENTS:
        return None
    return os.environ.get("TRACEPARENT")


def edited_file_directory(event: dict) -> str | None:
    """The edit goes to the branch of the edited file, which can differ from the cwd's."""
    file_key = EDITED_FILE_KEYS.get(event.get("tool_name"))
    tool_input = event.get("tool_input")
    if not file_key or not isinstance(tool_input, dict) or not tool_input.get(file_key):
        return None
    return os.path.dirname(tool_input[file_key])


def start_sender(fields: dict) -> None:
    """Git and the send run in a detached child, so the session never waits for them, and they
    outlive the 1.5 s SessionEnd budget and the end of a `claude -p` run."""
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        detached = {"creationflags": flags}
    else:
        detached = {"start_new_session": True}
    sender = subprocess.Popen(
        [sys.executable, "-I", os.path.abspath(__file__), SENDER_ARGUMENT],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **detached,
    )
    sender.stdin.write(json.dumps(fields).encode())
    sender.stdin.close()


def span_attributes(fields: dict) -> dict:
    attributes = {
        "agent_name": AGENT_NAME,
        "hook_event": fields["hook_event"],
        "session_id": fields["session_id"],
    }
    if isinstance(fields.get("tool_name"), str):
        attributes["tool_name"] = fields["tool_name"]
    directory = fields.get("directory")
    if isinstance(directory, str) and directory:
        attributes.update(repository_attributes(directory))
    return attributes


def repository_attributes(directory: str) -> dict[str, str]:
    origin = remote(git(directory, "remote", "get-url", "origin"))
    if not origin:
        return {}
    url, name = origin
    attributes = {"vcs_repository_url_full": url, "vcs_repository_name": name}
    # Not --short: it prints heads/<name> when a tag has the same name. Fails on a detached HEAD.
    ref = git(directory, "symbolic-ref", "--quiet", "HEAD")
    if ref.startswith("refs/heads/"):
        attributes["vcs_ref_head_name"] = ref[len("refs/heads/") :]
    return attributes


def git(directory: str, *args: str) -> str:
    # An inherited GIT_DIR would point `git -C` at another repository, and git needs no key.
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("GIT_", "CLAUDE_PLUGIN_OPTION_"))
    }
    try:
        completed = subprocess.run(
            ["git", "-C", directory, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def remote(url: str) -> tuple[str, str] | None:
    """(URL without user info, query or fragment; owner/repo). None for an origin on this machine:
    /path, C:\\path, file://, or a remote helper address such as hg::/path."""
    if "://" in url:
        try:
            parts = urlsplit(url)
        except ValueError:
            return None
        host = parts.netloc.rpartition("@")[2]
        if parts.scheme == "file" or not host:
            return None
        return f"{parts.scheme}://{host}{parts.path}", repository_name(parts.path)
    prefix, colon, path = url.partition(":")
    host = prefix.rpartition("@")[2]
    if not colon or path.startswith(":") or "/" in prefix or "\\" in prefix or len(host) < 2:
        return None
    return f"ssh://{host}/{path.lstrip('/')}", repository_name(path)


def repository_name(path: str) -> str:
    """owner/repo, as GitHub events name it, so hook and PR rows join."""
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return "/".join(path.split("/")[-2:])


def traces_payload(fields: dict, attributes: dict) -> dict:
    """A span inside a turn joins the turn's trace; the other spans of a session share one trace."""
    event_time = fields["time_unix_nano"]
    turn_span = TRACEPARENT_PATTERN.fullmatch(fields.get("traceparent") or "")
    if turn_span and turn_span.group(1).strip("0") and turn_span.group(2).strip("0"):
        trace_id, parent_span_id = turn_span.group(1), turn_span.group(2)
    else:
        trace_id = hashlib.sha256(fields["session_id"].encode()).hexdigest()[:32]
        parent_span_id = None
    span = {
        "traceId": trace_id,
        "spanId": secrets.token_hex(8),
        "name": SPAN_NAME_PREFIX + fields["hook_event"],
        "kind": SPAN_KIND_INTERNAL,
        "startTimeUnixNano": event_time,
        "endTimeUnixNano": event_time,
        "attributes": otlp_attributes(attributes),
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id
    resource = {"service.name": SERVICE_NAME, "cx.source.integration.type": SOURCE_TYPE}
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": otlp_attributes(resource)},
                "scopeSpans": [{"scope": {"name": SERVICE_NAME}, "spans": [span]}],
            }
        ]
    }


def otlp_attributes(attributes: dict) -> list:
    return [
        {"key": key, "value": {"stringValue": value}}
        for key, value in attributes.items()
        if isinstance(value, str) and value
    ]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry the key to another URL, maybe over plain http."""

    def redirect_request(self, *args, **kwargs):
        return None


def send(domain: str, send_data_key: str, payload: dict) -> None:
    request = urllib.request.Request(
        f"https://ingress.{domain}/v1/traces",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {send_data_key}", "Content-Type": "application/json"},
    )
    with urllib.request.build_opener(NoRedirect).open(request, timeout=SEND_TIMEOUT_SECONDS):
        pass


def record_error(message: str) -> None:
    """The sender runs detached, so this file is the only place where a failure shows."""
    data_directory = os.environ.get("CLAUDE_PLUGIN_DATA")
    if not data_directory:
        return
    try:
        os.makedirs(data_directory, exist_ok=True)
        path = os.path.join(data_directory, LAST_ERROR_FILE)
        with open(path, "w", encoding="utf-8") as last_error:
            last_error.write(f"{datetime.now(timezone.utc).isoformat()} {message}\n")
    except OSError:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # A telemetry failure must never fail the session.
        # Never str(error): an invalid header error repeats the key.
        if isinstance(error, urllib.error.HTTPError):
            record_error(f"HTTP {error.code}")
        else:
            record_error(type(error).__name__)

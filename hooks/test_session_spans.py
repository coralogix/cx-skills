"""Run with: python3 -m unittest discover -s hooks"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from unittest import mock

import session_spans

CONFIGURED = {
    session_spans.DOMAIN_OPTION: "eu2.coralogix.com",
    session_spans.SEND_DATA_KEY_OPTION: "send-data-key",
}


def git(directory: str, *args: str) -> None:
    # Auto maintenance would keep writing in .git after the command returns.
    no_maintenance = ["-c", "maintenance.auto=false", "-c", "gc.auto=0"]
    command = ["git", *no_maintenance, "-C", directory, *args]
    subprocess.run(command, check=True, capture_output=True, timeout=30)


def git_repo(parent: str, name: str, origin: str, branch: str = "feature/AIC-1-widget") -> str:
    path = os.path.join(parent, name)
    os.makedirs(path)
    git(path, "init", "-q", "-b", branch)
    git(path, "remote", "add", "origin", origin)
    identity = ["-c", "user.name=t", "-c", "user.email=t@t"]
    git(path, *identity, "commit", "-q", "--allow-empty", "-m", ".")
    return path


def run_main(event: dict, environment: dict, argv: list) -> mock.MagicMock:
    """Runs the hook entry point with UTF-8 bytes on stdin, as Claude Code sends them."""
    stdin = io.TextIOWrapper(io.BytesIO(json.dumps(event, ensure_ascii=False).encode()))
    with ExitStack() as stack:
        stack.enter_context(mock.patch.dict(os.environ, environment))
        stack.enter_context(mock.patch.object(sys, "stdin", stdin))
        stack.enter_context(mock.patch.object(sys, "argv", argv))
        start_sender = stack.enter_context(mock.patch.object(session_spans, "start_sender"))
        send = stack.enter_context(mock.patch.object(session_spans, "send"))
        session_spans.main()
    return start_sender, send


def span_attributes(event: dict) -> dict:
    return session_spans.span_attributes(session_spans.hook_fields(event))


class SessionSpansTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = directory.name
        # The host's git config (hooks, signing, insteadOf) must not change the results.
        isolated = mock.patch.dict(
            os.environ,
            {"HOME": self.root, "XDG_CONFIG_HOME": self.root, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        isolated.start()
        self.addCleanup(isolated.stop)
        self.https_repo = git_repo(
            self.root,
            "widget",
            "https://ci-bot:token123@github.com/Acme/Widget.git?private_token=token456#token789",
        )
        self.scp_repo = git_repo(self.root, "other", "git@github.com:acme/other.git")
        git(self.scp_repo, "checkout", "-q", "--detach")

    def test_hook_starts_sender_only_when_configured(self):
        event = {
            "session_id": "s1",
            "hook_event_name": "UserPromptSubmit",
            "cwd": self.https_repo,
            "prompt": "תקן את ❌",
        }
        unconfigured = {session_spans.DOMAIN_OPTION: "", session_spans.SEND_DATA_KEY_OPTION: ""}
        start_sender, _ = run_main(event, unconfigured, ["session_spans.py"])
        start_sender.assert_not_called()
        start_sender, send = run_main(event, CONFIGURED, ["session_spans.py"])
        [fields] = start_sender.call_args.args
        self.assertEqual(fields["hook_event"], "UserPromptSubmit")
        self.assertEqual(fields["directory"], self.https_repo)
        self.assertNotIn("❌", json.dumps(fields, ensure_ascii=False))
        send.assert_not_called()

    def test_sender_stamps_the_span_with_the_hook_time_not_its_own(self):
        fields = {
            "session_id": "s1",
            "hook_event": "SessionEnd",
            "time_unix_nano": "1700000000000000000",
            "directory": self.https_repo,
        }
        _, send = run_main(fields, CONFIGURED, ["session_spans.py", session_spans.SENDER_ARGUMENT])
        [(domain, key, payload)] = [call.args for call in send.call_args_list]
        self.assertEqual((domain, key), ("eu2.coralogix.com", "send-data-key"))
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        self.assertEqual(span["name"], "agent_hook.SessionEnd")
        self.assertEqual(span["startTimeUnixNano"], "1700000000000000000")

    def test_payload_matches_the_roi_service_contract(self):
        fields = {"session_id": "s1", "hook_event": "SessionStart", "time_unix_nano": "1"}
        payload = session_spans.traces_payload(fields, {"session_id": "s1"})
        [resource_spans] = payload["resourceSpans"]
        self.assertIn(
            {"key": "cx.source.integration.type", "value": {"stringValue": "claude_code_agent"}},
            resource_spans["resource"]["attributes"],
        )
        [span] = resource_spans["scopeSpans"][0]["spans"]
        self.assertEqual(span["name"], "agent_hook.SessionStart")
        self.assertEqual(len(span["traceId"]), 32)
        self.assertEqual(len(span["spanId"]), 16)
        int(span["traceId"] + span["spanId"], 16)
        self.assertEqual(span["startTimeUnixNano"], "1")
        self.assertNotIn("parentSpanId", span)

    def test_span_in_a_turn_is_a_child_of_the_turn_span(self):
        turn = "00-1ee0e8fa073e87da683359eeb0d0373a-b1d3ad205fbc0389-01"
        event = {"session_id": "s1", "hook_event_name": "UserPromptSubmit", "cwd": self.root}
        tracing_on = {"TRACEPARENT": turn, "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1"}
        with mock.patch.dict(os.environ, tracing_on):
            fields = session_spans.hook_fields(event)
        payload = session_spans.traces_payload(fields, {})
        span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
        self.assertEqual(span["traceId"], "1ee0e8fa073e87da683359eeb0d0373a")
        self.assertEqual(span["parentSpanId"], "b1d3ad205fbc0389")

    def test_traceparent_from_the_shell_is_not_used(self):
        shell = "00-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-bbbbbbbbbbbbbbbb-01"
        tracing = "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA"
        cases = (
            ("SessionStart", {"TRACEPARENT": shell, tracing: "1"}),
            ("SessionEnd", {"TRACEPARENT": shell, tracing: "1"}),
            ("UserPromptSubmit", {"TRACEPARENT": shell, tracing: "0"}),
        )
        for hook_event, environment in cases:
            with self.subTest(hook_event=hook_event, environment=environment):
                event = {"session_id": "s1", "hook_event_name": hook_event, "cwd": self.root}
                with mock.patch.dict(os.environ, environment):
                    self.assertIsNone(session_spans.hook_fields(event)["traceparent"])

    def test_invalid_traceparent_falls_back_to_the_session_trace(self):
        session_trace = session_spans.traces_payload(
            {"session_id": "s1", "hook_event": "Stop", "time_unix_nano": "1"}, {}
        )["resourceSpans"][0]["scopeSpans"][0]["spans"][0]["traceId"]
        for traceparent in (
            "00-00000000000000000000000000000000-b1d3ad205fbc0389-01",
            "00-1ee0e8fa073e87da683359eeb0d0373a-0000000000000000-01",
            "00-1EE0E8FA073E87DA683359EEB0D0373A-b1d3ad205fbc0389-01",
            "not a traceparent",
        ):
            with self.subTest(traceparent=traceparent):
                fields = {"session_id": "s1", "hook_event": "Stop", "time_unix_nano": "1"}
                fields["traceparent"] = traceparent
                payload = session_spans.traces_payload(fields, {})
                span = payload["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
                self.assertEqual(span["traceId"], session_trace)
                self.assertNotIn("parentSpanId", span)

    def test_prompt_span_has_cwd_branch_and_no_url_credentials(self):
        event = {"session_id": "s1", "hook_event_name": "UserPromptSubmit", "cwd": self.https_repo}
        span = span_attributes(event)
        self.assertEqual(span["vcs_repository_url_full"], "https://github.com/Acme/Widget.git")
        self.assertEqual(span["vcs_repository_name"], "Acme/Widget")
        self.assertEqual(span["vcs_ref_head_name"], "feature/AIC-1-widget")
        self.assertNotIn("token", json.dumps(span))

    def test_edit_span_has_edited_file_repo_and_no_branch_on_detached_head(self):
        event = {
            "session_id": "s1",
            "hook_event_name": "PostToolUse",
            "cwd": self.https_repo,
            "tool_name": "NotebookEdit",
            "tool_input": {"notebook_path": os.path.join(self.scp_repo, "n.ipynb")},
        }
        span = span_attributes(event)
        self.assertEqual(span["tool_name"], "NotebookEdit")
        self.assertEqual(span["vcs_repository_url_full"], "ssh://github.com/acme/other.git")
        self.assertEqual(span["vcs_repository_name"], "acme/other")
        self.assertNotIn("vcs_ref_head_name", span)

    def test_cwd_changed_span_has_the_new_directory_repo(self):
        event = {
            "session_id": "s1",
            "hook_event_name": "CwdChanged",
            "cwd": self.https_repo,
            "old_cwd": self.https_repo,
            "new_cwd": self.scp_repo,
        }
        self.assertEqual(span_attributes(event)["vcs_repository_name"], "acme/other")

    def test_branch_with_the_name_of_a_tag_keeps_its_name(self):
        repo = git_repo(self.root, "tagged", "https://github.com/acme/tagged.git", branch="release")
        git(repo, "tag", "release")
        event = {"session_id": "s1", "hook_event_name": "SessionStart", "cwd": repo}
        self.assertEqual(span_attributes(event)["vcs_ref_head_name"], "release")

    def test_span_outside_a_repository_has_no_vcs_attributes(self):
        event = {"session_id": "s1", "hook_event_name": "SessionEnd", "cwd": self.root}
        self.assertEqual(
            span_attributes(event),
            {"agent_name": "claude-code", "hook_event": "SessionEnd", "session_id": "s1"},
        )

    def test_remote_on_this_machine_is_never_sent(self):
        for origin in (
            "/Users/alice/private/project.git",
            "file:///Users/alice/private/project.git",
            "C:\\Users\\alice\\project.git",
            "C:/Users/alice/project.git",
            "hg::/home/alice/project",
            "ext::ssh -i /home/alice/.ssh/key host %S project",
            "../project",
            "ssh://alice@/project",
            "",
        ):
            with self.subTest(origin=origin):
                self.assertIsNone(session_spans.remote(origin))

    def test_remote_keeps_host_and_repository_only(self):
        for origin, expected in (
            ("alice@git.corp.example:team/x.git", ("ssh://git.corp.example/team/x.git", "team/x")),
            ("ssh://alice@github.com/acme/x", ("ssh://github.com/acme/x", "acme/x")),
            (
                "https://u:p@gitlab.com/g/sub/x.git?private_token=t#f",
                ("https://gitlab.com/g/sub/x.git", "sub/x"),
            ),
        ):
            with self.subTest(origin=origin):
                self.assertEqual(session_spans.remote(origin), expected)

    def test_coralogix_domain_accepts_pasted_forms_only(self):
        for value, expected in (
            ("eu2.coralogix.com", "eu2.coralogix.com"),
            (" https://EU2.coralogix.com/ ", "eu2.coralogix.com"),
            ("ingress.eu2.coralogix.com", "eu2.coralogix.com"),
            ("evil.com/x?", ""),
            ("eu2.coralogix.com:443", ""),
            ("localhost", ""),
        ):
            with self.subTest(value=value):
                self.assertEqual(session_spans.coralogix_domain(value), expected)


if __name__ == "__main__":
    unittest.main()

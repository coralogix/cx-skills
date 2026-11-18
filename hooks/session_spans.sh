#!/bin/sh
# session_spans.py always exits 0: a non-zero status means the interpreter failed (missing, or the
# Windows Store stub), so the next one gets the same input.

# Off until both options are set: no Python start on each event.
if [ -z "$CLAUDE_PLUGIN_OPTION_CORALOGIX_DOMAIN" ] || [ -z "$CLAUDE_PLUGIN_OPTION_CORALOGIX_SEND_DATA_KEY" ]; then
  exit 0
fi

# On a Mac without the developer tools, python3 and git are stubs that open an install dialog.
if [ -x /usr/bin/xcode-select ] && ! /usr/bin/xcode-select -p >/dev/null 2>&1; then
  exit 0
fi

input=$(cat)
script="$(dirname -- "$0")/session_spans.py"
for python in python3 python "py -3"; do
  command -v "${python%% *}" >/dev/null 2>&1 || continue
  # shellcheck disable=SC2086 # "py -3" is a command and its argument.
  printf '%s' "$input" | $python -I "$script" && exit 0
done
exit 0

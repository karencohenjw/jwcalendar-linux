#!/usr/bin/env bash
set -euo pipefail

output_dir="${1:-screenshots}"
mkdir -p "$output_dir"
export DISPLAY=:99
Xvfb "$DISPLAY" -screen 0 1280x900x24 >/tmp/jwcalendar-xvfb.log 2>&1 &
xvfb_pid=$!
app_pid=''
terminal_pid=''
cleanup() {
  [[ -z "$terminal_pid" ]] || kill "$terminal_pid" 2>/dev/null || true
  [[ -z "$app_pid" ]] || kill "$app_pid" 2>/dev/null || true
  kill "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT
sleep 2

.venv/bin/jwcalendar-desktop > /tmp/jwcalendar-desktop.log 2>&1 &
app_pid=$!
window=''
for _ in $(seq 1 30); do
  window=$(xdotool search --onlyvisible --name '^JW Calendar$' 2>/dev/null | head -n1 || true)
  [[ -n "$window" ]] && break
  sleep 1
done
if [[ -z "$window" ]]; then
  cat /tmp/jwcalendar-desktop.log
  exit 1
fi
sleep 2
import -window "$window" "$output_dir/01-month-view.png"
xdotool mousemove --window "$window" 100 125 click 1
sleep 1
import -window "$window" "$output_dir/02-year-overview.png"
xdotool mousemove --window "$window" 45 125 click 1
sleep 1
import -window "$window" "$output_dir/03-date-and-julian-details.png"

kill "$app_pid" 2>/dev/null || true
wait "$app_pid" 2>/dev/null || true
app_pid=''

xterm -fa Monospace -fs 14 -geometry 100x30+80+70 -bg '#102342' -fg '#f4f7fb' -e bash -c 'cd "$GITHUB_WORKSPACE"; .venv/bin/jwcalendar month 2027 1 --monday; sleep 30' &
terminal_pid=$!
sleep 3
term_window=$(xdotool search --onlyvisible --class XTerm 2>/dev/null | head -n1 || true)
[[ -n "$term_window" ]] || { echo 'xterm did not open' >&2; exit 1; }
import -window "$term_window" "$output_dir/04-cli-month-calendar.png"

kill "$terminal_pid" 2>/dev/null || true
wait "$terminal_pid" 2>/dev/null || true
terminal_pid=''
xterm -fa Monospace -fs 14 -geometry 100x30+80+70 -bg '#102342' -fg '#f4f7fb' -e bash -c 'cd "$GITHUB_WORKSPACE"; .venv/bin/jwcalendar date 2027-01-01; sleep 30' &
terminal_pid=$!
sleep 3
term_window=$(xdotool search --onlyvisible --class XTerm 2>/dev/null | head -n1 || true)
[[ -n "$term_window" ]] || { echo 'date-info xterm did not open' >&2; exit 1; }
import -window "$term_window" "$output_dir/05-cli-date-information.png"

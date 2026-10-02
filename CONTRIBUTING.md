# Contributing

Thanks for helping improve JW Calendar. Please open an issue before proposing a large feature so its scope and date rules can be discussed.

## Development setup

Use Python 3.10 or newer, then install the development tools:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

For the desktop app, install GTK 3 and PyGObject from the Linux distribution. Do not add a network service or telemetry to date calculations.

## Changes and tests

- Preserve strict date validation; do not normalize invalid user input.
- Keep Gregorian dates, Julian calendar dates, Julian Day Numbers, and ordinal dates clearly distinct.
- Add regression cases at leap-day, month-end, year-end, and ISO week-year boundaries.
- Run `python -m pytest`, `python -m ruff check .`, and `python -m ruff format --check .` before opening a pull request.
- Snap metadata or permission changes should be explained in the pull request.

## Pull requests

Keep changes focused, describe user-visible behavior, and include the exact validation performed. Do not include generated build directories, credentials, or screenshots that were not captured from a running Linux app.

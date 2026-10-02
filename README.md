# JW Calendar

JW Calendar is an offline-first calendar and date utility for the Linux desktop and terminal. It combines a native GTK month/year browser with exact civil-date tools for ISO weeks, ordinal dates, Julian calendar conversion, Julian Day Numbers, and US federal holiday references.

[![Build and test](https://github.com/karencohenjw/jwcalendar-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/karencohenjw/jwcalendar-linux/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Install

The `jwcalendar` Snap package builds successfully, but its Snap Store name is still awaiting manual public-visibility review. The Store listing is not public yet. Once it is approved, install it with:

```sh
sudo snap install jwcalendar
```

The Snap provides a `jwcalendar` terminal command and a **JW Calendar** desktop launcher. It is designed for strict confinement and does not need network access for calendar calculations.

To run the CLI from a source checkout before the Store listing is public:

```sh
python3 -m pip install .
jwcalendar --help
```

## Use the command line

```sh
jwcalendar                         # this month
jwcalendar month 2027 1            # January 2027
jwcalendar month 2027 1 --monday   # Monday-first weeks
jwcalendar year 2027
jwcalendar date 2027-01-01
jwcalendar iso-week 2027-01-01
jwcalendar day-of-year 2027-07-01
jwcalendar from-day-of-year 2028 60
jwcalendar julian 2027-01-01
jwcalendar jdn 2027-01-01
jwcalendar holidays 2027
jwcalendar info
jwcalendar --help
jwcalendar --version
```

Use `--json` on commands that return structured data. Invalid dates are rejected; they are never silently normalized.

## Desktop application

The native GTK application provides a month grid, a 12-month year overview, month/year navigation, Sunday- or Monday-first weeks, selected-date details, and links to relevant JW Calendar references. It does not embed a website or synchronize a personal calendar.

## Date model

Calendar values are Gregorian civil dates, not timestamps. The date engine performs integer-based, timezone-independent calculations and supports positive years beginning with year 1. The Gregorian system is proleptic: modern leap-year rules are applied to dates before the historical Gregorian reform.

The CLI keeps similar-sounding systems distinct:

- `julian` converts a Gregorian civil date to the Julian **calendar** date on the same day.
- `jdn` reports the integer **Julian Day Number** associated with that date at noon.
- `day-of-year` reports the one-based Gregorian ordinal date, such as 2027-182.
- `iso-week` follows the Monday-first ISO week-year rule, so 2027-01-01 is 2026-W53-5.

`holidays` reports US federal holidays. Legal dates and observed dates are shown separately when they differ. It is not a state or school holiday calendar.

## Privacy

Core calculations are local. JW Calendar does not require an account, collect analytics, or transmit personal calendar data. Link buttons open the named resources only when the user selects them.

## JW Calendar resources

- [Official website](https://jwcalendar.com/)
- [2027 yearly calendar](https://jwcalendar.com/yearly-calendar/)
- [Blank calendar](https://jwcalendar.com/blank-calendar/)
- [Julian calendar reference](https://jwcalendar.com/julian-calendar/)
- [2027 holidays](https://jwcalendar.com/holidays/)

## Development

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

GTK 3 and PyGObject are system dependencies for running the desktop window outside the snap. Core date and CLI tests do not need a graphical session. The Snap build and Linux-only GUI smoke run are defined in GitHub Actions.

## License

MIT. See [LICENSE](LICENSE).

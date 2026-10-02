"""Offline calendar and date command-line tools."""

from __future__ import annotations

import argparse
import calendar
import re
import shutil
import sys
from datetime import date as local_date

from jwcalendar_calendrical import CivilDate, build_month
from jwcalendar_calendrical.core.civil import is_leap_year
from jwcalendar_calendrical.export.json import to_json
from jwcalendar_calendrical.holidays.calendar import USFederalHolidayCalendar
from jwcalendar_calendrical.systems.gregorian import from_ordinal_date, to_ordinal_date
from jwcalendar_calendrical.systems.iso_week import to_iso_week_date
from jwcalendar_calendrical.systems.julian import gregorian_to_julian_calendar, to_julian_day_number
from jwcalendar_calendrical.week.models import MONDAY_FIRST, SUNDAY_FIRST, WeekModel

from . import __version__

MONTHS = tuple(calendar.month_name[month] for month in range(1, 13))


def parse_date(value: str) -> CivilDate:
    """Parse a strict Gregorian date without timezone or normalization."""
    if not re.fullmatch(r"\d{4,}-\d{2}-\d{2}", value):
        raise argparse.ArgumentTypeError("date must use YYYY-MM-DD")
    try:
        year, month, day = (int(part) for part in value.split("-"))
        return CivilDate(year, month, day)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}: {exc}") from exc


def _positive_int(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer") from exc
    if result < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return result


def _month_number(value: str) -> int:
    month = _positive_int(value)
    if month > 12:
        raise argparse.ArgumentTypeError("month must be in 1..12")
    return month


def _render_month(year: int, month: int, model: WeekModel) -> str:
    grid = build_month(year, month, week_model=model, adjacent_days=False)
    names = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    weekdays = " ".join(names[(model.first_weekday + index) % 7] for index in range(7))
    lines = [f"{MONTHS[month - 1]} {year}", weekdays]
    for row in grid.rows:
        lines.append(" ".join(f"{cell.date.day:2d}" if cell.date else "  " for cell in row))
    return "\n".join(lines)


def _month_block(year: int, month: int, model: WeekModel) -> list[str]:
    grid = build_month(year, month, week_model=model, adjacent_days=False)
    names = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
    offset = model.first_weekday
    lines = [
        f"{MONTHS[month - 1]} {year}".center(20),
        " ".join(names[(offset + i) % 7] for i in range(7)),
    ]
    for row in grid.rows:
        lines.append(" ".join(f"{cell.date.day:2d}" if cell.date else "  " for cell in row))
    return lines


def _render_year(year: int, model: WeekModel) -> str:
    columns = (
        3
        if shutil.get_terminal_size((80, 24)).columns >= 68
        else 2
        if shutil.get_terminal_size((80, 24)).columns >= 45
        else 1
    )
    blocks = [_month_block(year, month, model) for month in range(1, 13)]
    lines = [str(year), ""]
    for offset in range(0, 12, columns):
        row_blocks = blocks[offset : offset + columns]
        height = max(map(len, row_blocks))
        for line in range(height):
            lines.append(
                "   ".join(
                    (block[line] if line < len(block) else "").ljust(20) for block in row_blocks
                ).rstrip()
            )
        if offset + columns < 12:
            lines.append("")
    return "\n".join(lines)


def _week_model(args: argparse.Namespace) -> WeekModel:
    return MONDAY_FIRST if getattr(args, "monday", False) else SUNDAY_FIRST


def _week_start(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--monday", action="store_true", help="start weeks on Monday")
    group.add_argument("--sunday", action="store_true", help="start weeks on Sunday (default)")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jwcalendar",
        description="An offline calendar and date utility for Linux.",
    )
    parser.add_argument("--version", action="version", version=f"jwcalendar {__version__}")
    commands = parser.add_subparsers(dest="command")

    month = commands.add_parser("month", help="show a month calendar")
    month.add_argument("year", nargs="?", type=_positive_int)
    month.add_argument("month", nargs="?", type=_month_number)
    _week_start(month)
    month.add_argument("--plain", action="store_true", help="use plain terminal text")
    month.add_argument("--json", action="store_true", help="print structured JSON")

    year = commands.add_parser("year", help="show all twelve months")
    year.add_argument("year", nargs="?", type=_positive_int)
    _week_start(year)
    year.add_argument("--json", action="store_true")

    date = commands.add_parser("date", help="show date and calendar details")
    date.add_argument("date", type=parse_date)
    date.add_argument("--json", action="store_true")

    week = commands.add_parser("iso-week", help="show the ISO week date")
    week.add_argument("date", type=parse_date)
    week.add_argument("--json", action="store_true")

    ordinal = commands.add_parser(
        "day-of-year", aliases=["ordinal"], help="show the day number in its year"
    )
    ordinal.add_argument("date", type=parse_date)
    ordinal.add_argument("--json", action="store_true")

    reverse = commands.add_parser(
        "from-day-of-year", help="convert a year and ordinal day to a date"
    )
    reverse.add_argument("year", type=_positive_int)
    reverse.add_argument("day", type=_positive_int)
    reverse.add_argument("--json", action="store_true")

    julian = commands.add_parser(
        "julian", aliases=["julian-calendar"], help="convert to the Julian civil calendar"
    )
    julian.add_argument("date", type=parse_date)
    julian.add_argument("--json", action="store_true")

    jdn = commands.add_parser("jdn", help="show the Julian Day Number at noon")
    jdn.add_argument("date", type=parse_date)
    jdn.add_argument("--json", action="store_true")

    holidays = commands.add_parser("holidays", help="list US federal holiday dates")
    holidays.add_argument("year", nargs="?", type=_positive_int)
    holidays.add_argument("--json", action="store_true")

    info = commands.add_parser("info", help="describe the app and date conventions")
    info.add_argument("--json", action="store_true")
    return parser


def _json(value: object) -> None:
    print(to_json(value))


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    today = local_date.today()

    if args.command is None:
        print(_render_month(today.year, today.month, SUNDAY_FIRST))
    elif args.command == "month":
        year = today.year if args.year is None else args.year
        month = today.month if args.month is None else args.month
        if args.year is not None and args.month is None:
            parser.error("month YEAR requires MONTH")
        value = build_month(year, month, week_model=_week_model(args))
        if args.json:
            _json(value)
        else:
            print(_render_month(year, month, _week_model(args)))
    elif args.command == "year":
        year = today.year if args.year is None else args.year
        if args.json:
            _json(
                {
                    "year": year,
                    "months": [_month_block(year, m, _week_model(args)) for m in range(1, 13)],
                }
            )
        else:
            print(_render_year(year, _week_model(args)))
    elif args.command == "date":
        iso_year, iso_week, iso_day = to_iso_week_date(args.date)
        ordinal_year, ordinal = to_ordinal_date(args.date)
        total = 366 if is_leap_year(args.date.year) else 365
        value = {
            "date": str(args.date),
            "weekday": calendar.day_name[args.date.weekday()],
            "day_of_year": ordinal,
            "days_in_year": total,
            "iso_week_year": iso_year,
            "iso_week": iso_week,
            "iso_weekday": iso_day,
            "leap_year": is_leap_year(args.date.year),
            "days_remaining_in_year": total - ordinal,
        }
        if args.json:
            _json(value)
        else:
            print(f"Date:           {value['date']}")
            print(f"Weekday:        {value['weekday']}")
            print(f"Day of year:    {ordinal_year}-{ordinal:03d} ({ordinal} / {total})")
            print(f"ISO week:       {iso_year}-W{iso_week:02d}")
            print(f"ISO weekday:    {iso_day}")
            print(f"Leap year:      {'Yes' if value['leap_year'] else 'No'}")
            print(f"Days remaining: {total - ordinal}")
    elif args.command == "iso-week":
        year, week, weekday = to_iso_week_date(args.date)
        value = {
            "date": str(args.date),
            "iso_week_year": year,
            "week": week,
            "iso_weekday": weekday,
        }
        print(f"{year}-W{week:02d}-{weekday}" if not args.json else to_json(value))
    elif args.command in {"day-of-year", "ordinal"}:
        year, day = to_ordinal_date(args.date)
        value = {"date": str(args.date), "year": year, "day_of_year": day}
        print(f"{year}-{day:03d} (day {day} of year)" if not args.json else to_json(value))
    elif args.command == "from-day-of-year":
        try:
            result = from_ordinal_date(args.year, args.day)
        except ValueError as exc:
            parser.error(str(exc))
        print(
            to_json({"year": args.year, "day_of_year": args.day, "date": str(result)})
            if args.json
            else result
        )
    elif args.command in {"julian", "julian-calendar"}:
        converted = gregorian_to_julian_calendar(args.date)
        value = {"gregorian": str(args.date), "julian_calendar": str(converted)}
        if args.json:
            _json(value)
        else:
            print(f"Gregorian:       {args.date}\nJulian calendar: {converted}")
    elif args.command == "jdn":
        value = to_julian_day_number(args.date)
        print(
            to_json({"date": str(args.date), "julian_day_number_at_noon": value})
            if args.json
            else f"Julian Day Number (noon): {value}"
        )
    elif args.command == "holidays":
        year = today.year if args.year is None else args.year
        occurrences = USFederalHolidayCalendar().occurrences(year)
        if args.json:
            _json(occurrences)
        else:
            print(f"US federal holidays — {year}")
            for holiday in occurrences:
                observed = (
                    f" (observed {holiday.observed_date})"
                    if holiday.legal_date != holiday.observed_date
                    else ""
                )
                print(f"{holiday.legal_date}  {holiday.name}{observed}")
    elif args.command == "info":
        value = {
            "name": "JW Calendar",
            "version": __version__,
            "operation": "offline, date-only calculations",
            "gregorian_calendar": "proleptic Gregorian; years start at 1",
            "julian_calendar": "civil calendar date on the same day",
            "julian_day_number": "astronomical integer day number at noon",
            "ordinal_date": "one-based day-of-year number",
            "holidays": "US federal holiday reference calendar",
        }
        if args.json:
            _json(value)
        else:
            for key, item in value.items():
                print(f"{key.replace('_', ' ').title()}: {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

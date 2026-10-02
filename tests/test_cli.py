from __future__ import annotations

import argparse
import json
import os
import time

import pytest

from jwcalendar_linux.cli import main, parse_date


@pytest.mark.parametrize(
    ("date", "weekday", "ordinal", "iso_week"),
    [
        ("1900-01-01", "Monday", 1, "1900-W01"),
        ("2000-01-01", "Saturday", 1, "1999-W52"),
        ("2024-02-29", "Thursday", 60, "2024-W09"),
        ("2026-12-31", "Thursday", 365, "2026-W53"),
        ("2027-01-01", "Friday", 1, "2026-W53"),
        ("2027-02-28", "Sunday", 59, "2027-W08"),
        ("2027-03-01", "Monday", 60, "2027-W09"),
        ("2027-12-31", "Friday", 365, "2027-W52"),
        ("2028-01-01", "Saturday", 1, "2027-W52"),
        ("2028-02-29", "Tuesday", 60, "2028-W09"),
    ],
)
def test_date_command_regression(capsys, date, weekday, ordinal, iso_week):
    assert main(["date", date]) == 0
    output = capsys.readouterr().out
    assert f"Date:           {date}" in output
    assert f"Weekday:        {weekday}" in output
    assert f"Day of year:    {date[:4]}-{ordinal:03d}" in output
    assert f"ISO week:       {iso_week}" in output


@pytest.mark.parametrize(
    ("year", "expected"),
    [(1900, False), (2000, True), (2024, True), (2027, False), (2028, True), (2100, False)],
)
def test_gregorian_leap_years(year, expected):
    from jwcalendar_calendrical.core.civil import is_leap_year

    assert is_leap_year(year) is expected


@pytest.mark.parametrize(
    "value",
    [
        "2027-00-01",
        "2027-13-01",
        "2027-02-29",
        "2027-04-31",
        "not-a-date",
        "2027-1-01",
        "2027-01-1",
    ],
)
def test_rejects_invalid_or_noncanonical_dates(value):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_date(value)


def test_january_2027_grid_and_week_start(capsys):
    assert main(["month", "2027", "1", "--monday"]) == 0
    monday = capsys.readouterr().out
    assert "Mon Tue Wed Thu Fri Sat Sun" in monday
    assert "January 2027" in monday
    assert " 1  2  3" in monday

    assert main(["month", "2027", "1", "--json"]) == 0
    grid = json.loads(capsys.readouterr().out)
    assert grid["year"] == 2027
    assert grid["month"] == 1


def test_year_overview_and_narrow_terminal(monkeypatch, capsys):
    monkeypatch.setattr(
        "jwcalendar_linux.cli.shutil.get_terminal_size", lambda *_: os.terminal_size((40, 24))
    )
    assert main(["year", "2027"]) == 0
    output = capsys.readouterr().out
    assert output.count("2027") >= 13
    assert "December 2027" in output


def test_iso_ordinal_julian_and_jdn_commands(capsys):
    assert main(["iso-week", "2027-01-01"]) == 0
    assert capsys.readouterr().out.strip() == "2026-W53-5"
    assert main(["day-of-year", "2027-07-01"]) == 0
    assert "2027-182" in capsys.readouterr().out
    assert main(["from-day-of-year", "2028", "60"]) == 0
    assert capsys.readouterr().out.strip() == "2028-02-29"
    assert main(["julian", "2027-01-01"]) == 0
    assert "Julian calendar:" in capsys.readouterr().out
    assert main(["jdn", "2027-01-01"]) == 0
    assert "Julian Day Number (noon):" in capsys.readouterr().out


def test_holidays_info_and_version(capsys):
    assert main(["holidays", "2027"]) == 0
    assert "Independence Day" in capsys.readouterr().out
    assert main(["info"]) == 0
    info = capsys.readouterr().out
    assert "timezone" not in info.lower() or "date-only" in info

    with pytest.raises(SystemExit) as error:
        main(["--version"])
    assert error.value.code == 0
    assert "jwcalendar 0.1.0" in capsys.readouterr().out


def test_plain_date_output_does_not_change_with_timezone(capsys, monkeypatch):
    before = os.environ.get("TZ")
    outputs = []
    try:
        for zone in ("Pacific/Kiritimati", "America/Los_Angeles", "UTC"):
            monkeypatch.setenv("TZ", zone)
            time.tzset()
            assert main(["date", "2027-01-01"]) == 0
            outputs.append(capsys.readouterr().out)
    finally:
        if before is None:
            monkeypatch.delenv("TZ", raising=False)
        else:
            monkeypatch.setenv("TZ", before)
        time.tzset()
    assert outputs[0] == outputs[1] == outputs[2]

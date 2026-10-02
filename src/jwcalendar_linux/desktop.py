"""GTK 3 desktop calendar; its dependencies are supplied by the Linux package."""

from __future__ import annotations

import calendar
from datetime import date as host_date

from jwcalendar_calendrical import CivilDate, build_month
from jwcalendar_calendrical.core.civil import days_in_month, is_leap_year
from jwcalendar_calendrical.systems.gregorian import to_ordinal_date
from jwcalendar_calendrical.systems.iso_week import to_iso_week_date
from jwcalendar_calendrical.systems.julian import gregorian_to_julian_calendar, to_julian_day_number
from jwcalendar_calendrical.week.models import MONDAY_FIRST, SUNDAY_FIRST

from . import __version__

MONTH_NAMES = tuple(calendar.month_name[month] for month in range(1, 13))
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
RESOURCES = (
    ("JW Calendar", "https://jwcalendar.com/"),
    ("Yearly calendar", "https://jwcalendar.com/yearly-calendar/"),
    ("Blank calendar", "https://jwcalendar.com/blank-calendar/"),
    ("Julian calendar", "https://jwcalendar.com/julian-calendar/"),
    ("Holidays", "https://jwcalendar.com/holidays/"),
)


def main() -> int:
    """Run the native desktop app (GTK is imported only by the Linux launcher)."""
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gdk, Gio, Gtk
    except (ImportError, ValueError) as exc:
        raise SystemExit("JW Calendar desktop needs GTK 3 and PyGObject.") from exc

    class Window(Gtk.ApplicationWindow):
        def __init__(self, application: Gtk.Application) -> None:
            super().__init__(application=application, title="JW Calendar")
            self.set_default_size(1000, 720)
            self.set_border_width(0)
            now = host_date.today()
            self.selected = CivilDate(now.year, now.month, now.day)
            self.view_year = now.year
            self.week_model = SUNDAY_FIRST
            self._style(Gdk, Gtk)
            self._layout(Gtk)
            self._draw_month(Gtk)
            self._draw_year(Gtk)
            self._draw_details(Gtk)

        def _style(self, Gdk, Gtk) -> None:
            css = b"""
              window { background: #f4f7fb; color: #142748; }
              headerbar { background: #12264b; color: #fff; border: 0; }
              headerbar label { color: #fff; font-weight: 700; }
              .surface { background: #fff; border-radius: 14px; padding: 18px; }
              .muted { color: #66758c; }
              .heading { font-size: 24px; font-weight: 700; }
              .accent { color: #008e86; font-weight: 700; }
              button.day { min-height: 52px; min-width: 52px; border-radius: 10px; }
              button.current-date { border: 2px solid #12a99e; }
              .resource-heading { font-weight: 700; color: #16315d; }
            """
            provider = Gtk.CssProvider()
            provider.load_from_data(css)
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        def _layout(self, Gtk) -> None:
            header = Gtk.HeaderBar()
            header.set_show_close_button(True)
            header.props.title = "JW Calendar"
            self.set_titlebar(header)
            about = Gtk.Button.new_from_icon_name("help-about-symbolic", Gtk.IconSize.BUTTON)
            about.set_tooltip_text("About JW Calendar")
            about.connect("clicked", self._about, Gtk)
            header.pack_end(about)

            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            root.set_border_width(22)
            self.add(root)
            controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            root.pack_start(controls, False, False, 0)
            previous = Gtk.Button.new_with_label("‹")
            previous.set_tooltip_text("Previous month")
            previous.connect("clicked", self._shift_month, -1, Gtk)
            controls.pack_start(previous, False, False, 0)
            self.heading = Gtk.Label()
            self.heading.get_style_context().add_class("heading")
            controls.pack_start(self.heading, False, False, 4)
            following = Gtk.Button.new_with_label("›")
            following.set_tooltip_text("Next month")
            following.connect("clicked", self._shift_month, 1, Gtk)
            controls.pack_start(following, False, False, 0)

            controls_end = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=9)
            controls.pack_end(controls_end, False, False, 0)
            controls_end.pack_start(Gtk.Label(label="Year"), False, False, 0)
            self.year_spin = Gtk.SpinButton.new_with_range(1, 999999, 1)
            self.year_spin.set_value(self.view_year)
            self.year_spin.connect("value-changed", self._year_changed, Gtk)
            controls_end.pack_start(self.year_spin, False, False, 0)
            self.week_choice = Gtk.ComboBoxText()
            self.week_choice.append("sunday", "Sunday start")
            self.week_choice.append("monday", "Monday start")
            self.week_choice.set_active_id("sunday")
            self.week_choice.connect("changed", self._week_changed, Gtk)
            controls_end.pack_start(self.week_choice, False, False, 0)

            self.notebook = Gtk.Notebook()
            self.notebook.set_show_border(False)
            self.notebook.connect("switch-page", self._tab_changed)
            root.pack_start(self.notebook, True, True, 0)
            month_page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
            self.notebook.append_page(month_page, Gtk.Label(label="Month"))
            self.calendar_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            self.calendar_panel.get_style_context().add_class("surface")
            month_page.pack_start(self.calendar_panel, True, True, 0)
            self.detail_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.detail_panel.set_size_request(300, -1)
            self.detail_panel.get_style_context().add_class("surface")
            month_page.pack_start(self.detail_panel, False, False, 0)

            year_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            year_page.get_style_context().add_class("surface")
            self.notebook.append_page(year_page, Gtk.Label(label="Year"))
            self.year_grid = Gtk.Grid()
            self.year_grid.set_row_spacing(12)
            self.year_grid.set_column_spacing(12)
            year_page.pack_start(self.year_grid, True, True, 0)

            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            footer.get_style_context().add_class("muted")
            root.pack_end(footer, False, False, 0)
            footer.pack_start(
                Gtk.Label(label="Date calculations stay on this device"), False, False, 0
            )
            footer.pack_end(
                Gtk.LinkButton.new_with_label("https://jwcalendar.com/", "JW Calendar resources ↗"),
                False,
                False,
                0,
            )

        def _set_date(self, date: CivilDate, Gtk) -> None:
            self.selected = date
            self.view_year = date.year
            self.year_spin.set_value(date.year)
            self._draw_month(Gtk)
            self._draw_year(Gtk)
            self._draw_details(Gtk)

        def _shift_month(self, _button, direction: int, Gtk) -> None:
            self._set_date(self.selected.add_months(direction), Gtk)

        def _year_changed(self, spin, Gtk) -> None:
            year = int(spin.get_value())
            self.view_year = year
            day = min(self.selected.day, days_in_month(year, self.selected.month))
            self.selected = CivilDate(year, self.selected.month, day)
            self._draw_month(Gtk)
            self._draw_year(Gtk)
            self._draw_details(Gtk)

        def _week_changed(self, combo, Gtk) -> None:
            self.week_model = MONDAY_FIRST if combo.get_active_id() == "monday" else SUNDAY_FIRST
            self._draw_month(Gtk)
            self._draw_year(Gtk)

        def _tab_changed(self, _notebook, _page, page_number: int) -> None:
            if page_number == 1:
                self.heading.set_text(str(self.view_year))
            else:
                self.heading.set_text(
                    f"{MONTH_NAMES[self.selected.month - 1]} {self.selected.year}"
                )

        def _draw_month(self, Gtk) -> None:
            for child in self.calendar_panel.get_children():
                self.calendar_panel.remove(child)
            self.heading.set_text(f"{MONTH_NAMES[self.selected.month - 1]} {self.selected.year}")
            grid = build_month(
                self.selected.year, self.selected.month, week_model=self.week_model, fixed_rows=6
            )
            labels = Gtk.Grid()
            labels.set_column_homogeneous(True)
            for col in range(7):
                label = Gtk.Label(label=WEEKDAYS[(self.week_model.first_weekday + col) % 7])
                label.get_style_context().add_class("muted")
                labels.attach(label, col, 0, 1, 1)
            self.calendar_panel.pack_start(labels, False, False, 0)
            days = Gtk.Grid()
            days.set_row_spacing(5)
            days.set_column_spacing(5)
            days.set_column_homogeneous(True)
            now = host_date.today()
            today = CivilDate(now.year, now.month, now.day)
            for row_number, row in enumerate(grid.rows):
                for col, cell in enumerate(row):
                    button = Gtk.Button(
                        label=str(cell.date.day) if cell.in_month and cell.date else ""
                    )
                    button.get_style_context().add_class("day")
                    button.set_sensitive(cell.in_month and cell.date is not None)
                    if cell.date == self.selected:
                        button.get_style_context().add_class("suggested-action")
                    if cell.date == today:
                        button.get_style_context().add_class("current-date")
                    if cell.date is not None:
                        button.connect(
                            "clicked", lambda _button, value=cell.date: self._set_date(value, Gtk)
                        )
                    days.attach(button, col, row_number, 1, 1)
            self.calendar_panel.pack_start(days, True, True, 0)
            self.calendar_panel.show_all()

        def _draw_year(self, Gtk) -> None:
            for child in self.year_grid.get_children():
                self.year_grid.remove(child)
            for month in range(1, 13):
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                card.get_style_context().add_class("surface")
                title = Gtk.Button(label=MONTH_NAMES[month - 1])
                title.connect("clicked", self._choose_month, month, Gtk)
                card.pack_start(title, False, False, 0)
                mini = Gtk.Grid()
                mini.set_column_homogeneous(True)
                grid = build_month(self.view_year, month, week_model=self.week_model)
                for row_number, row in enumerate(grid.rows):
                    for col, cell in enumerate(row):
                        label = str(cell.date.day) if cell.in_month and cell.date else ""
                        button = Gtk.Button(label=label)
                        button.set_relief(Gtk.ReliefStyle.NONE)
                        button.set_sensitive(cell.in_month and cell.date is not None)
                        if cell.date == self.selected:
                            button.get_style_context().add_class("suggested-action")
                        if cell.date:
                            button.connect(
                                "clicked", lambda _b, value=cell.date: self._set_date(value, Gtk)
                            )
                        mini.attach(button, col, row_number, 1, 1)
                card.pack_start(mini, False, False, 0)
                self.year_grid.attach(card, (month - 1) % 3, (month - 1) // 3, 1, 1)
            self.year_grid.show_all()
            self.year_spin.set_value(self.view_year)

        def _choose_month(self, _button, month: int, Gtk) -> None:
            day = min(self.selected.day, days_in_month(self.view_year, month))
            self._set_date(CivilDate(self.view_year, month, day), Gtk)
            self.notebook.set_current_page(0)

        def _draw_details(self, Gtk) -> None:
            for child in self.detail_panel.get_children():
                self.detail_panel.remove(child)
            date = self.selected
            year, ordinal = to_ordinal_date(date)
            iso_year, iso_week, iso_day = to_iso_week_date(date)
            julian = gregorian_to_julian_calendar(date)
            days_in_year = 366 if is_leap_year(year) else 365
            lines = (
                (str(date), "heading"),
                (calendar.day_name[date.weekday()], "accent"),
                (f"ISO week  {iso_year}-W{iso_week:02d} · weekday {iso_day}", ""),
                (
                    f"Day of year  {year}-{ordinal:03d} ({ordinal} / {days_in_year})",
                    "",
                ),
                (f"Julian calendar  {julian.year:04d}-{julian.month:02d}-{julian.day:02d}", ""),
                (f"Julian Day Number  {to_julian_day_number(date)}", ""),
                (f"Leap year  {'Yes' if is_leap_year(year) else 'No'}", ""),
            )
            for text, style in lines:
                label = Gtk.Label(label=text, xalign=0)
                label.set_line_wrap(True)
                if style:
                    label.get_style_context().add_class(style)
                self.detail_panel.pack_start(label, False, False, 3)
            heading = Gtk.Label(label="Calendar resources", xalign=0)
            heading.get_style_context().add_class("resource-heading")
            self.detail_panel.pack_start(heading, False, False, 6)
            for label, uri in RESOURCES:
                self.detail_panel.pack_start(
                    Gtk.LinkButton.new_with_label(uri, label), False, False, 0
                )
            self.detail_panel.show_all()

        def _about(self, _button, Gtk) -> None:
            dialog = Gtk.AboutDialog(transient_for=self, modal=True)
            dialog.set_program_name("JW Calendar")
            dialog.set_version(__version__)
            dialog.set_comments("An offline-first calendar and date utility for Linux.")
            dialog.set_website("https://jwcalendar.com/")
            dialog.set_website_label("JW Calendar")
            dialog.set_license_type(Gtk.License.MIT_X11)
            dialog.run()
            dialog.destroy()

    class Application(Gtk.Application):
        def __init__(self) -> None:
            super().__init__(
                application_id="com.jwcalendar.Calendar", flags=Gio.ApplicationFlags.DEFAULT_FLAGS
            )

        def do_activate(self) -> None:
            window = self.props.active_window
            if window is None:
                window = Window(self)
            window.present()

    return Application().run(None)


if __name__ == "__main__":
    raise SystemExit(main())

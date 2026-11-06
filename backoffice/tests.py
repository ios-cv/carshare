from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .views import calendar_offset_seconds, calendar_period


class CalendarDaylightSavingTests(SimpleTestCase):
    def setUp(self):
        self.london = ZoneInfo("Europe/London")

    def test_day_headings_and_booking_offsets_share_the_same_scale(self):
        for month, day, first_day_hours in [
            (3, 29, 23),
            (10, 25, 25),
            (7, 1, 24),
            (1, 1, 24),
        ]:
            with self.subTest(month=month, day=day):
                start = datetime(2026, month, day, tzinfo=self.london)
                end, seconds, hours, headings = calendar_period(start, 2)
                self.assertEqual(len(hours), first_day_hours + 24)
                self.assertEqual(seconds, (first_day_hours + 24) * 3600)
                next_midnight = headings[1]["date"].astimezone(timezone.utc)
                self.assertAlmostEqual(
                    calendar_offset_seconds(next_midnight, start) / seconds * 100,
                    headings[0]["width_percent"],
                )
                self.assertAlmostEqual(sum(d["width_percent"] for d in headings), 100)
                self.assertEqual(calendar_offset_seconds(end, start), seconds)

    def test_spring_header_skips_missing_hour(self):
        start = datetime(2026, 3, 29, tzinfo=self.london)
        _, _, hours, _ = calendar_period(start, 2)
        self.assertEqual([h.strftime("%H") for h in hours[:3]], ["00", "02", "03"])
        self.assertEqual(
            calendar_offset_seconds(
                datetime(2026, 3, 29, 1, 30, tzinfo=timezone.utc), start
            ),
            1.5 * 3600,
        )

    def test_autumn_repeated_hour_has_distinct_columns_and_positive_duration(self):
        start = datetime(2026, 10, 25, tzinfo=self.london)
        _, _, hours, _ = calendar_period(start, 2)
        self.assertEqual(
            [h.strftime("%H %Z") for h in hours[:4]],
            ["00 BST", "01 BST", "01 GMT", "02 GMT"],
        )
        # 01:45 BST to 01:15 GMT is a 30-minute booking, not negative width.
        lower = datetime(2026, 10, 25, 0, 45, tzinfo=timezone.utc)
        upper = datetime(2026, 10, 25, 1, 15, tzinfo=timezone.utc)
        self.assertEqual(
            calendar_offset_seconds(upper, start)
            - calendar_offset_seconds(lower, start),
            1800,
        )

    def test_template_renders_repeated_hour_with_timezone_labels(self):
        start = datetime(2026, 10, 25, tzinfo=self.london)
        _, _, hours, headings = calendar_period(start, 2)
        html = render_to_string(
            "backoffice/components/calendar.html",
            {
                "hours_in_period": hours,
                "num_hours_in_period": len(hours),
                "name_days_in_period": headings,
                "calendar": [],
            },
        )
        self.assertIn("repeat(49,minmax(0,1fr))", html)
        self.assertIn("Sun 25 Oct 01:00 BST", html)
        self.assertIn("Sun 25 Oct 01:00 GMT", html)

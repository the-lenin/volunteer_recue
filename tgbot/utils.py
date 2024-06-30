import unittest
import datetime as dt
import re
from freezegun import freeze_time


def str_to_dt(string: str, tz: dt.timezone = dt.UTC) -> dt.datetime:
    """Parse date string to a datetime.datetime instance."""
    try:
        today = dt.datetime.now(tz=tz)

        pattern = r'([0-9]{2}[.,-/][0-9]{2}[.,-/][0-9]{4}|[0-9]{2}[.,-/][0-9]{2}|[0-9]{2})'  # noqa: E501
        match = re.search(pattern, string)
        if match:
            date_str = re.sub(r'\D', '', match.group(0))

            match len(date_str):
                case 2:
                    date = dt.datetime.strptime(date_str, '%d')
                    date = date.replace(year=today.year, month=today.month)
                    if date.date() < today.date():
                        if today.month == 12:
                            date = date.replace(month=1, year=today.year + 1)
                        else:
                            date = date.replace(month=today.month + 1)

                case 4:
                    date = dt.datetime.strptime(date_str, '%d%m')
                    date = date.replace(year=today.year)
                    if date.date() < today.date():
                        date = date.replace(year=today.year + 1)

                case 8:
                    date = dt.datetime.strptime(date_str, '%d%m%Y')
                    if date.date() < today.date():
                        raise ValueError("The date cannot be in the past.")
                case _:
                    raise ValueError("Invalid date format.")

            return date.replace(tzinfo=tz)

        pattern = r'(today|tomorrow|сегодня|завтра)'
        match = re.search(pattern, string.lower())
        if match:
            date_str = match.group()
            match date_str:
                case 'today' | 'сегодня':
                    date = today
                case 'tomorrow' | 'завтра':
                    date = today + dt.timedelta(days=1)
            return date

        raise ValueError("Invalid date format.")

    except Exception as e:
        raise e


class TestCase(unittest.TestCase):
    today = '2024-02-23'

    @freeze_time(today)
    def test_old_date(self):
        with self.assertRaises(
            ValueError,
            msg="The date cannot be in the past."
        ):
            str_to_dt('22-02-2024')

    @freeze_time(today)
    def test_future_date(self):
        self.assertEqual(
            str_to_dt('25-02-2024'), dt.datetime(2024, 2, 25, tzinfo=dt.UTC)
        )

    @freeze_time(today)
    def test_future_day_month(self):
        self.assertEqual(
            str_to_dt('25-02'), dt.datetime(2024, 2, 25, tzinfo=dt.UTC)
        )

    @freeze_time(today)
    def test_future_day_same_month(self):
        self.assertEqual(
            str_to_dt('25'), dt.datetime(2024, 2, 25, tzinfo=dt.UTC)
        )

    @freeze_time(today)
    def test_future_day_next_month(self):
        self.assertEqual(
            str_to_dt('04'), dt.datetime(2024, 3, 4, tzinfo=dt.UTC)
        )

    @freeze_time(today)
    def test_future_today_tomorrow(self):
        today_dt = dt.datetime(2024, 2, 23, tzinfo=dt.UTC)
        self.assertEqual(str_to_dt('Today'), today_dt)
        self.assertEqual(str_to_dt('today'), today_dt)
        self.assertEqual(str_to_dt('Сегодня'), today_dt)

        self.assertEqual(
            str_to_dt('Tomorrow'), dt.datetime(2024, 2, 24, tzinfo=dt.UTC)
        )

    @freeze_time('22-12-2024')
    def test_next_year(self):
        self.assertEqual(
            str_to_dt('02'), dt.datetime(2025, 1, 2, tzinfo=dt.UTC)
        )
        self.assertEqual(
            str_to_dt('02-01'), dt.datetime(2025, 1, 2, tzinfo=dt.UTC)
        )


def main():
    print('Start')
    unittest.main()


if __name__ == '__main__':
    main()

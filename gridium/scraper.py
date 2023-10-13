from typing import Any, List, Tuple

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.tide-forecast.com"


class TideForecastScraper:
    """Scrape Tide Forecast data from tide-forecast.com"""

    def get_location_url(self, location_name: str) -> str:
        return f"{BASE_URL}/locations/{location_name}/tides/latest"

    def parse_time(self, time: str) -> int:
        """Convert time to a number so tide values can be compared"""
        # Check if we are in the afternoon, but not in the noon hour
        hour_shift = 12 if "PM" in time.upper() and "12:" not in time else 0
        hour, minute = (
            time.upper()
            .replace(" ", "")
            .replace(".", "")
            .replace("AM", "")
            .replace("PM", "")
            .split(":")
        )
        return (int(hour) + int(hour_shift)) * 60 + int(minute)

    def parse_todays_times(self, header: str) -> Tuple[int, int]:
        """Today's forecast has a different format for the sunrise and sunset times in a sentence instead of the table"""
        sunrise_time, sunset_time = header.split("Sunrise is at  ")[1].split(
            " and sunset is at  "
        )
        return self.parse_time(sunrise_time), self.parse_time(sunset_time)

    def get_daylight_low_tides(self, day: Any, date: str, sunrise: int, sunset: int):
        """Get all the daylight low tides for a particular day, track if there aren't any for that day"""

        # track if a daylight low tide exist for that day and notify if there isn't one
        has_tide = False
        tide_table = day.find("table", class_="tide-day-tides")

        # iterate through the rows, skip the first (assuming) header row
        for row in tide_table.find_all("tr")[1:]:
            tide_type, time, height = row.find_all("td")
            if tide_type.text == "Low Tide":
                tide_time_value = time.find("b").text
                tide_time = self.parse_time(tide_time_value)
                if tide_time > sunrise and tide_time < sunset:
                    has_tide = True
                    print(f"{date} {tide_time_value} {height.text}")
        return has_tide

    def run(self, locations: List[str]):
        """Script to iterate through the locations and return results"""
        for location in locations:
            print(location)
            location_url = self.get_location_url(location)

            response = requests.get(location_url)
            if response.status_code != 200:
                raise RuntimeError(f"ERROR: Unable to get page for {location_url}")

            tide_html = BeautifulSoup(response.content, "html.parser")

            # Parse table for today's tides, which is a little different than the future dates
            todays_tide = tide_html.find_all(
                "div", class_="tide-header-today tide-header__card"
            )[0]
            if not todays_tide:
                raise RuntimeError("Unable to find today's tide table")

            todays_date = todays_tide.find_all("h3")[0].text.split(": ")[1]
            todays_tide_header = tide_html.find_all("p", class_="tide-header-summary")
            if not todays_tide_header:
                RuntimeError("Unable to find today's header!")
            todays_sunrise, todays_sunset = self.parse_todays_times(
                todays_tide_header[0].text
            )
            self.get_daylight_low_tides(
                todays_tide, todays_date, todays_sunrise, todays_sunset
            )

            # Parse tables for future days
            for day in tide_html.find_all("div", class_="tide-day"):
                date = day.find("h4").text.split(": ")[1]
                sunrise_el, sunset_el = day.find_all(
                    "td", class_="tide-day__sun-moon-cell"
                )[0:2]
                sunrise = self.parse_time(
                    sunrise_el.select("span.tide-day__value")[0].text
                )
                sunset = self.parse_time(
                    sunset_el.select("span.tide-day__value")[0].text
                )

                has_tide = self.get_daylight_low_tides(day, date, sunrise, sunset)
                if not has_tide:
                    print(f"No daylight low tide for {date}")


if __name__ == "__main__":
    locations = [
        "Half-Moon-Bay-California",
        "Huntington-Beach",
        "Providence-Rhode-Island",
        "Wrightsville-Beach-North-Carolina",
    ]

    scraper = TideForecastScraper()
    scraper.run(locations)

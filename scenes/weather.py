import urllib.request
import urllib.parse
import datetime
import time
import json
from math import ceil
from functools import lru_cache
from rgbmatrix import graphics
from utilities.animator import Animator
from setup import colours, fonts, frames
from config import WEATHER_LOCATION
import sys
import os

# Attempt to load config data
try:
    from config import OPENWEATHER_API_KEY

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no config data
    OPENWEATHER_API_KEY = None

try:
    from config import TEMPERATURE_UNITS

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no config data
    TEMPERATURE_UNITS = "metric"

try:
    from config import RAINFALL_ENABLED

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no config data
    RAINFALL_ENABLED = False

if RAINFALL_ENABLED and OPENWEATHER_API_KEY:
    print("Rainfall display does not yet work with Open Weather", file=sys.stderr)
    RAINFALL_ENABLED = False

if TEMPERATURE_UNITS != "metric" and TEMPERATURE_UNITS != "imperial":
    TEMPERATURE_UNITS = "metric"

# Weather API
WEATHER_API_URL = "https://taps-aff.co.uk/api/"
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/"
WEATHER_RETRIES = 3
# Newer API for future weather
OPENWEATHER_GEO_URL = "http://api.openweathermap.org/geo/1.0/direct?"
OPENWEATHER_ONECALL_URL = "https://api.openweathermap.org/data/3.0/onecall?"
ONECALL_3_URL = "https://api.openweathermap.org/data/3.0/onecall?"

# Scene Setup
RAINFALL_REFRESH_SECONDS = 300
RAINFALL_HOURS = 24
RAINFAILL_12HR_MARKERS = True
RAINFALL_GRAPH_ORIGIN = (39, 15)
RAINFALL_COLUMN_WIDTH = 1
RAINFALL_GRAPH_HEIGHT = 8
RAINFALL_MAX_VALUE = 3  # mm
RAINFALL_OVERSPILL_FLASH_ENABLED = True

TEMPERATURE_REFRESH_SECONDS = 120 #put up from 60 to avoid too many calls in a day
TEMPERATURE_FONT = fonts.regular
TEMPERATURE_FONT_HEIGHT = 6
TEMPERATURE_POSITION = (40, TEMPERATURE_FONT_HEIGHT + 4)

FUTURE_TEMPERATURE_FONT = fonts.extrasmall
FUTURE_TEMPERATURE_FONT_HEIGHT = 6
FUTURE_TEMPERATURE_POSITION = (10, TEMPERATURE_POSITION[1] + 6)

TEMPERATURE_COLOURS = (
    (0, colours.WHITE),
    (1, colours.BLUE_LIGHT),
    (8, colours.PINK_DARK),
    (18, colours.YELLOW),
    (30, colours.ORANGE),
)

# For drawing Icons (Emma)
FORECAST_ICON_POSITION = (52, 20)  # top-left corner of an 10x10 sprite - move 2 pixels larger if doing 8x8
FORECAST_ICON_SIZE = 11

SPRITES_11x11 = {
    "clear": [
        ".    .    .",
        " .   .   . ",
        "  .     .  ",
        "    ...    ",
        "   .....   ",
        ".. ..... ..",
        "   .....   ",
        "    ...    ",
        "  .     .  ",
        " .   .   . ",
        ".    .    .",
    ],
    "few-clouds": [
        "    .    . ",
        ".   .   .  ",
        " .     .   ",
        "   ...     ",
        "  .....    ",
        ". ....     ",
        "  ...   ...",
        "   .  .....",
        " .   ......",
        ".    ......",
        "      .....",
    ],
    "scattered-clouds": [
        "  .  .  .  ",
        "   .   .   ",
        "    ...    ",
        " . ..... . ",
        "           ",
        "   .....   ",
        "  .......  ",
        " ......... ",
        " ......... ",
        "  .......  ",
        "           ",
    ],
    "clouds": [
        "           ",
        "      ..   ",
        "     ....  ",
        "   ....... ",
        "  ........ ",
        " ..........",
        "...........",
        "...........",
        " ..........",
        "  ........ ",
        "   ......  ",
       # "           ", # hollow cloud - like less
       # "      ..   ",
       # "     .  .  ",
       # "   ..    . ",
       # "  .      . ",
       # " .        .",
       # ".         .",
       # ".         .",
       # " .        .",
       # "  .      . ",
       # "   ......  ",
        #"           ", # old cloud
        #"   .....   ",
        #"  .......  ",
        #" ......... ",
        #"...........",
        #"...........",
        #" ......... ",
        #"  .......  ",
        #"           ",
        #"           ",
        #"           ",
    ],
    "showers": [
        "   .....   ",
        "  .......  ",
        " ......... ",
        "...........",
        "...........",
        " ......... ",
        "  .  .  .  ",
        "           ",
        ".  .  .  . ",
        "           ",
        "  .  .  .  ",
    ],
    "rain": [
        "   .....   ",
        "  .......  ",
        " ......... ",
        "...........",
        "...........",
        " ......... ",
        "  . . . .  ",
        " . . . . . ",
        "  . . . .  ",
        " . . . . . ",
        "  . . . .  ",
    ],
    "snow": [
        "     .     ",
        "           ",
        "   . . .   ",
        "  .. . ..  ",
        "    . .    ",
        ". .. . .. .",
        "    . .    ",
        "  .. . ..  ",
        "   . . .   ",
        "           ",
        "     .     ",
    ],
    "thunder": [
        "   .....   ",
        "  .......  ",
        " ......... ",
        ".......... ",
        "   ....    ",
        "   ..      ",
        "  ....     ",
        "    ..     ",
        "   ..      ",
        "   .       ",
        "           ",
    ],
    "mist": [
        "   .  .  . ",
        " .. .. .. .",
        "           ",
        "   .  .  . ",
        " .. .. .. .",
        "           ",
        "   .  .  . ",
        " .. .. .. .",
        "           ",
        "   .  .  . ",
        " .. .. .. .",
    ],
    "unknown": [
        "  .......  ",
        " ......... ",
        "..      .. ",
        "      ...  ",
        "    ...    ",
        "   ..      ",
        "           ",
        "   ..      ",
        "   ..      ",
        "   ..      ",
        "           ",
    ],
}


SPRITES_8x8 = {
    "clear": [
        ".  .  . ",
        " .   .  ",
        "  ...   ",
        ". ... . ",
        "  ...   ",
        " .   .  ",
        ".  .  . ",
        "   .    ",
    ],
    "clouds": [
        "        ",
        "  ....  ",
        " ...... ",
        "........",
        "........",
        " ...... ",
        "        ",
        "        ",
    ],
    "rain": [
        "  ....  ",
        " ...... ",
        "........",
        "........",
        " ...... ",
        "  .  . .",
        " .  .  .",
        "  .  .  ",
    ],
    "snow": [
        "   .    ",
        " . . .  ",
        "  ...  .",
        "... ... ",
        "  ...  .",
        " . . .  ",
        "   .    ",
        "        ",
    ],
    "thunder": [
        "  ....  ",
        " ...... ",
        "........",
        "  ..    ",
        " ....   ",
        "   ..   ",
        "  ..    ",
        "        ",
    ],
    "mist": [
        "        ",
        " ...... ",
        "        ",
        " ...... ",
        "        ",
        " ...... ",
        "        ",
        "        ",
    ],
    "unknown": [
        " ...... ",
        "..    ..",
        "    ... ",
        "   ..   ",
        "  ..    ",
        "        ",
        "  ..    ",
        "        ",
    ],
}

# This helps to test all sprites manually:
def get_icon_override_category():
    """
    Returns a sprite category override from env var, or None.
    Use like: FORECAST_ICON_OVERRIDE=rain
    """
    override = os.environ.get("FORECAST_ICON_OVERRIDE")
    if not override:
        return None
    override = override.strip().lower()
    if override in SPRITES_11x11 or override in SPRITES_8x8:
        return override
    return None


def draw_sprite(canvas, x, y, sprite, colour):
    """Draw an 8x8 sprite where non-space characters are 'on' pixels."""
    for row, line in enumerate(sprite):
        for col, ch in enumerate(line):
            if ch != " ":
                canvas.SetPixel(x + col, y + row, colour.red, colour.green, colour.blue)

def clear_sprite(canvas, x, y, sprite):
    for row, line in enumerate(sprite):
        for col, ch in enumerate(line):
            if ch != " ":
                canvas.SetPixel(x + col, y + row, 0, 0, 0)




# Cache grabbing weather data
class WeatherError(Exception):
    """Raised when weather data cannot be retrieved after all retries."""
    pass


@lru_cache()
def grab_weather(location, ttl_hash=None):
    del ttl_hash  # not used directly, just part of the cache key

    content = None
    retries = WEATHER_RETRIES

    while retries:
        try:
            request = urllib.request.Request(WEATHER_API_URL + location)
            raw_data = urllib.request.urlopen(request, timeout=3).read()
            content = json.loads(raw_data.decode("utf-8"))
            break
        except Exception as e:
            retries -= 1
    else:
        # We've ran out of retries without getting new weather data
        raise WeatherError(
            f"Failed to fetch weather data for '{location}' after {WEATHER_RETRIES} retries"
        )

    return content


def get_ttl_hash(seconds=60):
    """Return the same value withing `seconds` time period"""
    return round(time.time() / seconds)


def grab_current_temperature(location, units="metric"):
    current_temp = None

    try:
        weather = grab_weather(location, ttl_hash=get_ttl_hash())
        current_temp = weather["temp_c"]

    except WeatherError:
        grab_weather.cache_clear()

    if units == "imperial":
        current_temp = (current_temp * (9.0 / 5.0)) + 32

    return current_temp


def grab_upcoming_rainfall_and_temperature(location, hours):
    up_coming_rainfall_and_temperature = None

    try:
        weather = grab_weather(location, ttl_hash=get_ttl_hash())

        # We want to parse the data to find the
        # rainfall from now for <hours>
        forecast_today = weather["forecast"][0]["hourly"]
        forecast_tomorrow = weather["forecast"][1]["hourly"]
        hourly_forecast = forecast_today + forecast_tomorrow

        hourly_data = [
            {
                "precip_mm": hour["precip_mm"],
                "temp_c": hour["temp_c"],
                "hour": hour["hour"],
            }
            for hour in hourly_forecast
        ]

        now = datetime.datetime.now()
        current_hour = now.hour
        up_coming_rainfall_and_temperature = hourly_data[
            current_hour : current_hour + hours
        ]

    except WeatherError:
        grab_weather.cache_clear()

    return up_coming_rainfall_and_temperature


def grab_current_temperature_openweather(location, apikey, units):
    current_temp = None
    retries = WEATHER_RETRIES

    while retries:
        try:
            request = urllib.request.Request(
                OPENWEATHER_API_URL
                + "weather?q="
                + location
                + "&appid="
                + apikey
                + "&units="
                + units
            )
            raw_data = urllib.request.urlopen(request, timeout=3).read()
            content = json.loads(raw_data.decode("utf-8"))
            current_temp = content["main"]["temp"]
            break
        except Exception as e:
            retries -= 1
    else:
        raise WeatherError(
            f"Failed to fetch current temperature for '{location}' "
            f"after {WEATHER_RETRIES} retries"
        )

    return current_temp

#by Emma, with ChatGPT, map icon code to weather conditions to draw icon later
def icon_category(icon_code: str) -> str:
    if not icon_code or len(icon_code) < 2:
        return "unknown"
    base = icon_code[:2]
    return {
        "01": "clear",
        "02": "few-clouds",
        "03": "scattered-clouds",
        "04": "clouds",
        "09": "showers",
        "10": "rain",
        "11": "thunder",
        "13": "snow",
        "50": "mist",
    }.get(base, "unknown")

#by Emma, with ChatGPT (new API call needs lat/long not location)
def geocode_location(location, apikey):
    params = {
        "q": location,
        "limit": 1,
        "appid": apikey,
    }
    url = OPENWEATHER_GEO_URL + urllib.parse.urlencode(params)
    raw = urllib.request.urlopen(url, timeout=3).read()
    results = json.loads(raw.decode("utf-8"))
    if not results:
        raise WeatherError(f"Could not geocode location '{location}'")
    return results[0]["lat"], results[0]["lon"]

#by Emma, with ChatGPT
def grab_next_two_hours_temperature_openweather(location, apikey, units):
    lat, lon = geocode_location(location, apikey)

    params = {
        "lat": lat,
        "lon": lon,
        "exclude": "minutely,daily,alerts",
        "appid": apikey,
        "units": units,
    }
    url = ONECALL_3_URL + urllib.parse.urlencode(params)

    raw = urllib.request.urlopen(url, timeout=3).read()
    content = json.loads(raw.decode("utf-8"))

    # current temperature:
    current_temp = content["current"]["temp"]

    # hourly forecast (next hours):
    hourly = content.get("hourly", [])
    if len(hourly) < 3:
        raise WeatherError("Hourly forecast missing or too short")

    hour2 = hourly[2]
    temp2 = hour2["temp"]
    
    # get offset for time
    tz_offset = content.get("timezone_offset", 0)  # seconds
    dt_local = hour2["dt"] + tz_offset
    time_str = time.strftime("%H:%M", time.gmtime(dt_local))

    # grab icon code
    icon = hour2["weather"][0].get("icon")

    return (time_str, temp2, icon)
    #temp_plus_1h = hourly[1]["temp"]
    #temp_plus_2h = hourly[2]["temp"]

    # Optional: convert dt to readable UTC time for display/debug
    #dt_plus_1h = datetime.datetime.fromtimestamp(hourly[1]["dt"], tz=datetime.timezone.utc)
    #dt_plus_2h = datetime.datetime.fromtimestamp(hourly[2]["dt"], tz=datetime.timezone.utc)

    # return [hourly[1]["temp"], hourly[2]["temp"]]
    # older more complex version that returns all 3 - not compatible with rest of code
    #return {
    #    "current": current_temp,
    #    "plus_1h": {"dt": dt_plus_1h, "temp": temp_plus_1h},
    #    "plus_2h": {"dt": dt_plus_2h, "temp": temp_plus_2h},
    #}


class WeatherScene(object):
    def __init__(self):
        super().__init__()
        self._last_upcoming_rain_and_temp = None
        self._last_temperature = None
        self._last_temperature_str = None
        #Emma, related to sprite/icon drawing
        self._last_forecast_icon_cat = None

        # Attempt to grab the current temperature using OPENWEATHER if a key
        # is provided otherwise fallback on the taps-aff service
        self._temperature_providers = [
            *( [lambda: grab_current_temperature_openweather(
                    WEATHER_LOCATION, OPENWEATHER_API_KEY, TEMPERATURE_UNITS
                )] if OPENWEATHER_API_KEY else [] ),
            lambda: grab_current_temperature(WEATHER_LOCATION, TEMPERATURE_UNITS)
        ]

        # Attempt by Emma with GPT to get next 2 hours of weather forecast
        self._forecast_providers = [
            *(
               [lambda: grab_next_two_hours_temperature_openweather(
                    WEATHER_LOCATION, OPENWEATHER_API_KEY, TEMPERATURE_UNITS
               )] if OPENWEATHER_API_KEY  else [] ),
        ]


    def colour_gradient(self, colour_A, colour_B, ratio):
        return graphics.Color(
            colour_A.red + ((colour_B.red - colour_A.red) * ratio),
            colour_A.green + ((colour_B.green - colour_A.green) * ratio),
            colour_A.blue + ((colour_B.blue - colour_A.blue) * ratio),
        )

    def temperature_to_colour(self, current_temperature):
        # Set some defaults
        min_temp = TEMPERATURE_COLOURS[0][0]
        max_temp = TEMPERATURE_COLOURS[1][0]
        min_temp_colour = TEMPERATURE_COLOURS[0][1]
        max_temp_colour = TEMPERATURE_COLOURS[1][1]

        # Search to find where in the current
        # temperature lies within the
        # defined colours
        for i in range(1, len(TEMPERATURE_COLOURS) - 1):
            if current_temperature > TEMPERATURE_COLOURS[i][0]:
                min_temp = TEMPERATURE_COLOURS[i][0]
                max_temp = TEMPERATURE_COLOURS[i + 1][0]
                min_temp_colour = TEMPERATURE_COLOURS[i][1]
                max_temp_colour = TEMPERATURE_COLOURS[i + 1][1]

        if current_temperature > max_temp:
            ratio = 1
        elif current_temperature > min_temp:
            ratio = (current_temperature - min_temp) / max_temp
        else:
            ratio = 0

        temp_colour = self.colour_gradient(min_temp_colour, max_temp_colour, ratio)

        return temp_colour

    def draw_rainfall_and_temperature(
        self, rainfall_and_temperature, graph_colour=None, flash_enabled=False
    ):
        columns = range(
            0, RAINFALL_HOURS * RAINFALL_COLUMN_WIDTH, RAINFALL_COLUMN_WIDTH
        )

        i = 0

        # Draw hours
        for data, column_x in zip(rainfall_and_temperature, columns):
            rain_height = int(
                ceil(data["precip_mm"] * (RAINFALL_GRAPH_HEIGHT / RAINFALL_MAX_VALUE))
            )

            if rain_height > RAINFALL_GRAPH_HEIGHT:
                # Any over-spill, flash some pixels
                flash_height = rain_height - RAINFALL_GRAPH_HEIGHT

                if flash_height > RAINFALL_GRAPH_HEIGHT:
                    flash_height = (
                        RAINFALL_GRAPH_HEIGHT + 1
                    )  # +1 to also draw over x-axis

                # Clip over-spill
                rain_height = RAINFALL_GRAPH_HEIGHT
            else:
                flash_height = 0

            if RAINFAILL_12HR_MARKERS:
                hourly_marker = data["hour"] in (0, 12)
            else:
                hourly_marker = False

            x1 = RAINFALL_GRAPH_ORIGIN[0] + column_x
            x2 = x1 + RAINFALL_COLUMN_WIDTH
            y1 = RAINFALL_GRAPH_ORIGIN[1] + (1 if hourly_marker else 0)
            y2 = RAINFALL_GRAPH_ORIGIN[1] - rain_height

            if graph_colour is None:
                square_colour = self.temperature_to_colour(data["temp_c"])
            else:
                flash_height = 0
                square_colour = graph_colour

            self.draw_square(x1, y1, x2, y2, square_colour)

            # Make any over-spill flash
            if flash_height and flash_enabled:
                x1 = RAINFALL_GRAPH_ORIGIN[0] + column_x
                x2 = x1 + RAINFALL_COLUMN_WIDTH
                y1 = RAINFALL_GRAPH_ORIGIN[1] - RAINFALL_GRAPH_HEIGHT
                y2 = y1 + flash_height - 1

                self.draw_square(x1, y1, x2, y2, colours.BLACK)

    @Animator.KeyFrame.add(frames.PER_SECOND * 1)
    def rainfall(self, count):

        if not RAINFALL_ENABLED:
            return

        if len(self._data):
            # Don't draw if there's plane data
            # and force a redraw when this is visible
            # again by clearing the previous drawn data
            # forcing a complete redraw
            self._last_upcoming_rain_and_temp = None

            # Don't draw anything
            return

        if not (count % RAINFALL_REFRESH_SECONDS):
            self.upcoming_rain_and_temp = grab_upcoming_rainfall_and_temperature(
                WEATHER_LOCATION, RAINFALL_HOURS
            )

        # Test for drawing rainfall if data is available
        if not self._last_upcoming_rain_and_temp == self.upcoming_rain_and_temp:
            if self._last_upcoming_rain_and_temp is not None:
                # Undraw previous graph
                self.draw_rainfall_and_temperature(
                    self._last_upcoming_rain_and_temp, colours.BLACK
                )

        if self.upcoming_rain_and_temp:
            # Draw new graph
            flash_enabled = (
                True if RAINFALL_OVERSPILL_FLASH_ENABLED and (count % 2) else False
            )

            self.draw_rainfall_and_temperature(
                self.upcoming_rain_and_temp, flash_enabled=flash_enabled
            )
            self._last_upcoming_rain_and_temp = self.upcoming_rain_and_temp.copy()

    @Animator.KeyFrame.add(frames.PER_SECOND * 1)
    def temperature(self, count):

        if len(self._data):
            # Don't draw if there's plane data
            return

        if not (count % TEMPERATURE_REFRESH_SECONDS):
            self.current_temperature = None
            for temperature in self._temperature_providers:
                try:
                    self.current_temperature = temperature()
                    break
                except WeatherError:
                    continue

            # by Emma & ChatGPT - get future forecast refresh (separate chain)
            self.future_temperatures = None
            for forecast in self._forecast_providers:
                 try:
                     self.future_temperatures = forecast()
                     break
                 except WeatherError:
                     continue

        if self._last_temperature_str is not None:
            # Undraw old temperature
            _ = graphics.DrawText(
                self.canvas,
                TEMPERATURE_FONT,
                TEMPERATURE_POSITION[0],
                TEMPERATURE_POSITION[1],
                colours.BLACK,
                self._last_temperature_str,
            )

        # by Emma
        if getattr(self, "_last_future_temp_str", None) is not None:
            # Undraw old future temperature
            _ = graphics.DrawText(
                self.canvas,
                FUTURE_TEMPERATURE_FONT,
                FUTURE_TEMPERATURE_POSITION[0],
                FUTURE_TEMPERATURE_POSITION[1],
                colours.BLACK,
                self._last_future_temp_str,
            )

        # by Emma - undraw old icon
        # Undraw old forecast icon (prevents ghosting)
        if self._last_forecast_icon_cat is not None:
            old_sprite = SPRITES_8x8.get(self._last_forecast_icon_cat, SPRITES_8x8["unknown"])
            clear_sprite(self.canvas, FORECAST_ICON_POSITION[0], FORECAST_ICON_POSITION[1], old_sprite)
            self._last_forecast_icon_cat = None


        if self.future_temperatures:
            forecast_time, forecast_temp, forecast_icon = self.future_temperatures
            future_str = f"+2h {forecast_time}: {round(forecast_temp)}°"
            _ = graphics.DrawText(
                self.canvas,
                FUTURE_TEMPERATURE_FONT,
                FUTURE_TEMPERATURE_POSITION[0],
                FUTURE_TEMPERATURE_POSITION[1],
                colours.WHITE,
                future_str,
            )
            self._last_future_temp_str = future_str

            # by Emma - draw icon in bottom-right
            override_cat = get_icon_override_category() # allow override manually to test sprites/icons
            cat = override_cat if override_cat else icon_category(forecast_icon)
            sprite = SPRITES_11x11.get(cat, SPRITES_11x11["unknown"])
            draw_sprite(self.canvas, FORECAST_ICON_POSITION[0], FORECAST_ICON_POSITION[1], sprite, colours.WHITE)
            self._last_forecast_icon_cat = cat



        if self.current_temperature:
            temp_str = f"{round(self.current_temperature)}°".rjust(4, " ")

            temp_colour = self.temperature_to_colour(self.current_temperature)

            # Draw temperature
            _ = graphics.DrawText(
                self.canvas,
                TEMPERATURE_FONT,
                TEMPERATURE_POSITION[0],
                TEMPERATURE_POSITION[1],
                temp_colour,
                temp_str,
            )

            self._last_temperature = self.current_temperature
            self._last_temperature_str = temp_str

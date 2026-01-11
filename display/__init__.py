import sys
import datetime

from setup import frames
from utilities.animator import Animator
from utilities.overhead import Overhead

from scenes.weather import WeatherScene
from scenes.flightdetails import FlightDetailsScene
from scenes.journey import JourneyScene
from scenes.loadingpulse import LoadingPulseScene
from scenes.loadingled import LoadingLEDScene
from scenes.clock import ClockScene
from scenes.planedetails import PlaneDetailsScene
from scenes.day import DayScene
from scenes.date import DateScene

from rgbmatrix import graphics
from rgbmatrix import RGBMatrix, RGBMatrixOptions


def callsigns_match(flights_a, flights_b):
    get_callsigns = lambda flights: [f["callsign"] for f in flights]
    callsigns_a = set(get_callsigns(flights_a))
    callsigns_b = set(get_callsigns(flights_b))

    return callsigns_a == callsigns_b

# Emma modified to add brightness/dim/off settings for changes over time
try:
    # Attempt to load config data
    from config import (
        BRIGHTNESS,
        GPIO_SLOWDOWN,
        HAT_PWM_ENABLED,
        BRIGHTNESS_DAY,
        BRIGHTNESS_DIM,
        DIM_START_HOUR,
        DIM_END_HOUR,
        OFF_START_HOUR,
        OFF_END_HOUR,
    )

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no config data
    BRIGHTNESS = 100
    GPIO_SLOWDOWN = 1
    HAT_PWM_ENABLED = True

    BRIGHTNESS_DAY = BRIGHTNESS
    BRIGHTNESS_DIM = 50
    DIM_START_HOUR = 19
    DIM_END_HOUR = 8
    OFF_START_HOUR = 21
    OFF_END_HOUR = 7

try:
    # Attempt to load experimental config data
    from config import LOADING_LED_ENABLED

except (ModuleNotFoundError, NameError, ImportError):
    # If there's no experimental config data
    LOADING_LED_ENABLED = False


#Emma & ChatGPT - add helpers to track time and adjust brightness/display
def _minutes_since_midnight(dt: datetime.datetime) -> int:
    return dt.hour * 60 + dt.minute

def _in_window(now_min: int, start_hour: int, end_hour: int) -> bool:
    """True if now is in [start, end) where window may cross midnight."""
    start = start_hour * 60
    end = end_hour * 60
    if start < end:
        return start <= now_min < end
    else:
        # crosses midnight
        return now_min >= start or now_min < end

class Display(
    WeatherScene,
    FlightDetailsScene,
    JourneyScene,
    LoadingLEDScene if LOADING_LED_ENABLED else LoadingPulseScene ,
    PlaneDetailsScene,
    ClockScene,
    DayScene,
    DateScene,
    Animator,
):
    def __init__(self):
        # Setup Display
        options = RGBMatrixOptions()
        options.hardware_mapping = "adafruit-hat-pwm" if HAT_PWM_ENABLED else "adafruit-hat"
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.row_address_type = 0
        options.multiplexing = 0
        options.pwm_bits = 11
        options.brightness = BRIGHTNESS
        options.pwm_lsb_nanoseconds = 130
        options.led_rgb_sequence = "RGB"
        options.pixel_mapper_config = ""
        options.show_refresh_rate = 0
        options.gpio_slowdown = GPIO_SLOWDOWN
        options.disable_hardware_pulsing = True
        options.drop_privileges = True
        self.matrix = RGBMatrix(options=options)

        # Emma - set up brightness/dim/off
        self._screen_off = False
        self._brightness_current = BRIGHTNESS_DAY
        self.matrix.brightness = self._brightness_current

        # Setup canvas
        self.canvas = self.matrix.CreateFrameCanvas()
        self.canvas.Clear()

        # Emma - create black canvas for 'off'
        self.black_canvas = self.matrix.CreateFrameCanvas()
        self.black_canvas.Clear()

        # Data to render
        self._data_index = 0
        self._data = []

        # Start Looking for planes
        self.overhead = Overhead()
        self.overhead.grab_data()

        # Initalise animator and scenes
        super().__init__()

        # Overwrite any default settings from
        # Animator or Scenes
        self.delay = frames.PERIOD

    def draw_square(self, x0, y0, x1, y1, colour):
        for x in range(x0, x1):
            _ = graphics.DrawLine(self.canvas, x, y0, x, y1, colour)

    @Animator.KeyFrame.add(0)
    def clear_screen(self):
        # First operation after
        # a screen reset
        self.canvas.Clear()

    @Animator.KeyFrame.add(frames.PER_SECOND * 5)
    def check_for_loaded_data(self, count):
        if self.overhead.new_data:
            # Check if there's data
            there_is_data = len(self._data) > 0 or not self.overhead.data_is_empty

            # this marks self.overhead.data as no longer new
            new_data = self.overhead.data

            # See if this matches the data already on the screen
            # This test only checks if it's 2 lists with the same
            # callsigns, regardless or order
            data_is_different = not callsigns_match(self._data, new_data)

            if data_is_different:
                self._data_index = 0
                self._data_all_looped = False
                self._data = new_data

            # Only reset if there's flight data already
            # on the screen, of if there's some new
            # data available to draw which is different
            # from the current data
            reset_required = there_is_data and data_is_different

            if reset_required:
                self.reset_scene()

    @Animator.KeyFrame.add(frames.PER_SECOND * 60)
    def power_management(self, count):
        # Emma - adds a power-management feature to control brightness/dim/off display
        now = datetime.datetime.now()
        now_min = _minutes_since_midnight(now)

        off = _in_window(now_min, OFF_START_HOUR, OFF_END_HOUR)
        dim = _in_window(now_min, DIM_START_HOUR, DIM_END_HOUR)

        if off:
            target_brightness = 0
            screen_off = True
        elif dim:
            target_brightness = BRIGHTNESS_DIM
            screen_off = False
        else:
            target_brightness = BRIGHTNESS_DAY
            screen_off = False

        # Apply only if something changed
        if screen_off != self._screen_off:
            self._screen_off = screen_off

        if target_brightness != self._brightness_current:
            self.matrix.brightness = target_brightness
            self._brightness_current = target_brightness

    @Animator.KeyFrame.add(1)
    def sync(self, count):
        # Emma - modify so that during off window, nothing is displayed
        if getattr(self, "_screen_off", False):
            _ = self.matrix.SwapOnVSync(self.black_canvas)
        else: #    self.canvas.Clear()
            _ = self.matrix.SwapOnVSync(self.canvas)
        #Original: # Redraw screen every frame
        #_ = self.matrix.SwapOnVSync(self.canvas)

    @Animator.KeyFrame.add(frames.PER_SECOND * 30)
    def grab_new_data(self, count):
        # Only grab data if we're not already searching
        # for planes, or if there's new data available
        # which hasn't been displayed.
        #
        # We also need wait until all previously grabbed
        # data has been looped through the display.
        #
        # Last, if our internal store of the data
        # is empty, try and grab data
        if not (self.overhead.processing and self.overhead.new_data) and (
            self._data_all_looped or len(self._data) <= 1
        ):
            self.overhead.grab_data()

    def run(self):
        try:
            # Start loop
            print("Press CTRL-C to stop")
            self.play()

        except KeyboardInterrupt:
            print("Exiting\n")
            sys.exit(0)

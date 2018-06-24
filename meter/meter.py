import threading
import struct
import math
import os

import scipy.signal
import numpy as np
import pyaudio
import pygame

from .config import load_config
from .widgets import Button, Indicator, Graph, VUMeter, MessageBox
from .grid import GridingManager, RootWindow
from .enums import *

CONFIG, NEW_CONFIG = load_config()
if CONFIG.get('rpi'):
    # When using the TFT screen on the Raspberry Pi, SDL still expects a
    # standard screen so we force it to connect to a seperate frame-buffer/
    # input selection.
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ['SDL_FBDEV'] = '/dev/fb1'
    os.environ['SDL_MOUSEDRV'] = 'TSLIB'
    os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
pygame.display.init()
pygame.font.init()


AW_BTN = 0
SPEECH_BTN = 1
SPLIT_BTN = 2
GRAPH_BTN = 3

CONFIG_MESSAGE = """No config file was found.
The default has been loaded.

You should probably close this
and setup the audio inputs."""


def a_weighting(fs):
    """Compute the constants needed for the A-weighting"""
    f1 = 20.598997
    f2 = 107.65265
    f3 = 737.86223
    f4 = 12194.217
    a1000 = 1.9997

    nums = [(2 * np.pi * f4) ** 2 * (10 ** (a1000 / 20)), 0, 0, 0, 0]
    dens = np.polymul([1, 4 * np.pi * f4, (2 * np.pi * f4) ** 2],
                      [1, 4 * np.pi * f1, (2 * np.pi * f1) ** 2])
    dens = np.polymul(np.polymul(dens, [1, 2 * np.pi * f3]),
                      [1, 2 * np.pi * f2])

    return scipy.signal.bilinear(nums, dens, fs)


class Meter:
    def __init__(self):
        self.screen = self.root = self.box = self.graph = self.vu_p = None
        self.buttons, self.indicators = [], []

        self.setup_display()

        self.loud = CONFIG.get('loud_music', 3)
        self.quiet = CONFIG.get('quiet_music', 15)

        self.audio = pyaudio.PyAudio()

        # Connect to input devices and start stream listeners
        self.stream1 = self.audio.open(
            format=CONFIG.get('format', 8),
            channels=CONFIG.get('channels', 1),
            rate=CONFIG.get('rate', 44100),
            input=True,
            frames_per_buffer=CONFIG.get('chunk', '1024'),
            input_device_index=CONFIG.get('device_1_id', 1))
        thread = threading.Thread(target=self.read_stream1)
        thread.daemon = True
        thread.start()
        if CONFIG.get('line_in'):
            self.stream2 = self.audio.open(
                format=CONFIG.get('format', 8),
                channels=CONFIG.get('channels', 1),
                rate=CONFIG.get('rate', 44100),
                input=True,
                frames_per_buffer=CONFIG.get('chunk', '1024'),
                input_device_index=CONFIG.get('device_2_id', 1))

            thread = threading.Thread(target=self.read_stream2)
            thread.daemon = True
            thread.start()

    def setup_display(self):
        """
        Form our screen, create the gridding manager, create and bind the panes
        to the manager then bind callbacks to the buttons.
        """

        self.screen = pygame.display.set_mode((CONFIG.get('screen_width', 0), CONFIG.get('screen_height', 0)),
                                              (not CONFIG.get('rpi')) * pygame.RESIZABLE, 32)
        if CONFIG.get('rpi'):
            # When running an X session straight from the console, the cursor
            # will stay in the corner. Let's hide it.
            pygame.mouse.set_visible(False)

        # Register the window with the packing system
        self.root = RootWindow(self.screen)
        self.box = GridingManager()

        labels = ['A/W', 'SPEECH', 'SPLIT', 'GRAPH']
        self.buttons = [self.box.grid(Button(text=labels[i]), 0, i) for i in range(4)]
        self.buttons[SPEECH_BTN].callback = self.on_speech_tog_click
        self.buttons[SPLIT_BTN ].callback = self.on_split_tog_click
        self.buttons[GRAPH_BTN ].callback = self.on_graph_tog_click

        self.buttons[SPLIT_BTN].disabled = CONFIG.get('line_in', False)

        ind_1 = self.box.grid(Indicator(label=CONFIG.get('source_1_label', '1'), row_span=2), 1, 0)
        ind_2 = self.box.grid(Indicator(label=CONFIG.get('source_1_label', '2'), row_span=2), 2, 0)
        self.indicators = [ind_1, ind_2]

        self.graph = self.box.grid(Graph(row_span=2, col_span=2), 1, 2)
        self.vu_p = self.box.grid(VUMeter(row_span=4), 3, 0)

        self.root.add_child(self.box)

        if CONFIG['welcome_message']:
            self.root.add_child(MessageBox(CONFIG['welcome_message']))
        if NEW_CONFIG:
            self.root.add_child(MessageBox(CONFIG_MESSAGE))

        self.reflow()

    # Callbacks
    def on_speech_tog_click(self, _, state):
        """Callback handler for the speech toggle"""
        if state:  # Enable speech mode
            self.vu_p.loud = CONFIG.get('loud_speech', 12)
            self.vu_p.quiet = CONFIG.get('quiet_speech', 30)

            self.loud = CONFIG.get('loud_speech', 12)
            self.quiet = CONFIG.get('quiet_speech', 30)
        else:  # Disable speech mode
            self.vu_p.loud = CONFIG.get('loud_music', 3)
            self.vu_p.quiet = CONFIG.get('quiet_music', 15)

            self.loud = CONFIG.get('loud_music', 3)
            self.quiet = CONFIG.get('quiet_music', 15)

    def on_graph_tog_click(self, _, __):
        """Callback handler for the graph toggle"""
        self.reflow()

    def on_split_tog_click(self, _, __):
        """Callback handler for the split toggle"""
        self.reflow()

    def reflow(self):
        """
        Remove all the center panes from the gridding manager and then re-grid
        them depending on what the user wants to be shown.

        TODO: Find a cleaner way to do this.
        """

        self.box.remove(self.indicators[0])
        self.box.remove(self.indicators[1])
        self.box.remove(self.graph)
        if CONFIG.get('line_in') or self.buttons[SPLIT_BTN].state:
            self.indicators[0].row_span = 2
            self.indicators[1].row_span = 2
            if self.buttons[GRAPH_BTN].state:
                self.indicators[0].col_span = 1
                self.indicators[1].col_span = 1
                self.box.grid(self.indicators[0], 1, 0)
                self.box.grid(self.indicators[1], 2, 0)

                self.graph.row_span = 2
                self.graph.col_span = 2
                self.box.grid(self.graph, 1, 2)
            else:
                self.indicators[0].col_span = 2
                self.indicators[1].col_span = 2
                self.box.grid(self.indicators[0], 1, 0)
                self.box.grid(self.indicators[1], 1, 2)
        else:
            self.indicators[0].col_span = 2
            self.box.grid(self.indicators[0], 1, 0)
            if self.buttons[GRAPH_BTN].state:
                self.indicators[0].row_span = 2
                self.graph.row_span = 2
                self.graph.col_span = 2

                self.box.grid(self.graph, 1, 2)
            else:
                self.indicators[0].row_span = 4

    # Audio processing
    @staticmethod
    def butter_pass_filter(data, cutoff, fs, btype, order=5):
        """Perform a butter pass filter on a set of data"""
        normal_cutoff = cutoff / (0.5 * fs)
        b, a, *_ = scipy.signal.butter(order, normal_cutoff, btype=btype, analog=False)
        return scipy.signal.lfilter(b, a, data)

    B, A = a_weighting(CONFIG.get('rate', 44100))

    # Stream handling
    @staticmethod
    def rms(shorts):
        """Calculate the root mean squared of a set of data"""
        count = len(shorts)
        sum_squares = 0
        for sample in shorts:
            n = sample * (1 / 32768)
            sum_squares += n * n
        return math.sqrt(sum_squares / count)

    def get_db(self, data):
        """Vaguely calculate the -dB from a sample"""
        db = self.rms(data)
        db = 20 * math.log10(db) if db else 48
        return max(0, min(48, abs(db)))

    def read(self, stream):
        """Read data from a given PyAudio stream and then handle it as needed"""
        data = stream.read(CONFIG.get('chunk', 1024), exception_on_overflow=False)

        if self.buttons[AW_BTN].state:
            # Apply A-weighting
            data = np.frombuffer(data, dtype=np.int16)
            data = scipy.signal.lfilter(self.B, self.A, data, axis=0)
            db = self.get_db(data)
        else:
            count = len(data) / 2
            shorts = struct.unpack(str(int(count)) + 'h', data)
            db = self.get_db(shorts)
            if self.buttons[SPLIT_BTN].state:
                # The butter filter requests a numpy array
                data = np.fromstring(data, dtype=np.int16)

        return db, data

    def add_value(self, val, index):
        """Take a new packet of data and inform the other panes of it"""
        self.graph.feed(index, val)  # Update graph

        avg = min(self.graph.data_sets[index][-CONFIG.get('average_samples', 20):])

        state = LOW if avg >= self.quiet else HIGH if avg <= self.loud else MID
        if self.indicators[index].state != state:  # Avoid unneeded re-drawing
            self.indicators[index].state = state
            self.indicators[index].dirty = True

        self.vu_p.curr[index] = val
        self.vu_p.avg[index] = avg
        self.vu_p.dirty = True

    def read_stream1(self):
        """Stream handler for the primary stream"""
        while self.root.running:
            v, d = self.read(self.stream1)

            if self.buttons[SPLIT_BTN].state:
                # Split the packet into two chunks (defined in config)
                split_frequency = CONFIG.get('split_frequency', 125)
                rate = CONFIG.get('rate', 44100)
                lp_data = self.butter_pass_filter(d, split_frequency, rate, 'low')
                hp_data = self.butter_pass_filter(d, split_frequency, rate, 'high')

                lp_db = self.get_db(lp_data)
                hp_db = self.get_db(hp_data)

                self.add_value(lp_db, 1)
                self.add_value(hp_db, 0)
            else:
                self.add_value(v, 0)

            if not (CONFIG.get('line_in') or self.buttons[SPLIT_BTN].state):
                # Flat-line the secondary input when not in use
                self.add_value(48, 1)

    def read_stream2(self):
        """Stream handler for the secondary stream"""
        while self.root.running:
            v, _ = self.read(self.stream2)
            self.add_value(v, 1)

    # Mainloop
    def main(self):
        """Hand over to the GUI manager"""
        self.root.mainloop()
        pygame.display.quit()
        pygame.font.quit()


if __name__ == '__main__':
    meter = Meter()
    meter.main()

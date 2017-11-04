import threading
import struct
import math
import os
os.environ['SDL_VIDEODRIVER'] = 'fbcon'
os.environ['SDL_FBDEV'] = '/dev/fb1'
os.environ['SDL_MOUSEDRV'] = 'TSLIB'
os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'

import scipy.signal
import numpy as np
import pyaudio
import pygame
pygame.init()


RPI = True

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

AVERAGE_SAMPLES = 20  # Last 0.5 seconds
GRAPH_SAMPLES = 215  # Last 5 seconds

BG_COLOUR = (60, 80, 110)
BG_DARKER = (50, 60, 90)
BORDER_COLOUR = (15, 15, 15)
BORDER_LIGHT = (90, 95, 100)
TEXT_COLOUR = (80, 100, 120)
FG_COLOUR = (0, 0, 0)

DARK_ORANGE = (40, 40, 20)
DARK_GREEN = (20, 30, 20)
ORANGE = (230, 190, 45)
GREEN = (50, 150, 80)
LIGHT_BLUE = (80, 180, 220)
DARK_BLUE = (10, 35, 60)
RED = (215, 45, 50)

SOURCE_1_LABEL = 'MIC'
SOURCE_2_LABEL = 'OUT'

BUTTON_COLOUR = [
    (64, 87, 54),
    (129, 146, 114),
    (43, 55, 31),
    (51, 64, 38)
]
BUTTON_GREY_COLOUR = [
    (132, 134, 131),
    (162, 163, 165),
    (91, 91, 91),
    (87, 87, 87)
]
BUTTON_BLUE_COLOUR = [
    (117, 206, 240),
    (140, 231, 255),
    (28, 109, 139),
    (72, 168, 208)
]

FONT = pygame.font.Font('font.ttf', 10)
FONT_BIG = pygame.font.Font('font.ttf', 20)

FPS = 30

BUTTON_PADDING = 2
COLOUR_PADDING = 4


def A_weighting(fs):
    f1 = 20.598997
    f2 = 107.65265
    f3 = 737.86223
    f4 = 12194.217
    A1000 = 1.9997

    NUMs = [(2*np.pi * f4)**2 * (10**(A1000/20)), 0, 0, 0, 0]
    DENs = np.polymul([1, 4*np.pi * f4, (2*np.pi * f4)**2],
                   [1, 4*np.pi * f1, (2*np.pi * f1)**2])
    DENs = np.polymul(np.polymul(DENs, [1, 2*np.pi * f3]),
                                 [1, 2*np.pi * f2])

    return scipy.signal.bilinear(NUMs, DENs, fs)


class Meter:
    B, A = A_weighting(RATE)

    QUIET_MUSIC = 24
    LOUD_MUSIC = 6

    QUIET_SPEECH = 36
    LOUD_SPEECH = 12

    '''
    SPEC:

    1/2/5/10S 20*log10(a)
    -----------------------
    [A WEIGHT]  /\
    [DESK OUT]  ||
    [REF MIC ]  ||
    [DISP    ]  \/
    -----------------------
    GREEN/RED FOR ACCEPTABLE LEVEL (AMBER = QUIET)
    -----------------------
    - ON DISP
    - SPECTOGRAPH / VU
    -----------------------
    AM/PM TOGGLE
    '''
    def __init__(self):
        self.screen = pygame.display.set_mode((320, 240))
        if RPI: pygame.mouse.set_visible(False)

        self.running = True

        self.a1_colour = ORANGE
        self.a2_colour = ORANGE

        self.samples_1 = []
        self.samples_2 = []
        self.graph_samples_1 = []
        self.graph_samples_2 = []

        self.vu_1 = 48
        self.vu_2 = 48

        self.a_weighting = True
        self.show_graph = False
        self.speech_enabled = False

        if self.speech_enabled:
            self.loud = self.LOUD_SPEECH
            self.quiet = self.QUIET_SPEECH
        else:
            self.loud = self.LOUD_MUSIC
            self.quiet = self.QUIET_MUSIC

        self.audio = pyaudio.PyAudio()

        info = self.audio.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
                if (self.audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                    print("Input Device id ", i, " - ", self.audio.get_device_info_by_host_api_device_index(0, i).get('name'))

        self.stream1 = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=1 if RPI else 2,
        )
        self.stream2 = None  # self.audio.open(
        #    format=FORMAT,
        #    channels=CHANNELS,
        #    rate=RATE,
        #    input=True,
        #    frames_per_buffer=CHUNK,
        #    input_device_index=1,
        #)

        thread = threading.Thread(target=self.read_stream1)
        thread.daemon = True
        thread.start()

        thread = threading.Thread(target=self.read_stream2)
        thread.daemon = True
        thread.start()

        self.clock = pygame.time.Clock()

    @staticmethod
    def rms(shorts):
        count = len(shorts)
        sum_squares = 0
        for sample in shorts:
            n = sample * (1 / 32768)
            sum_squares += n * n
        return math.sqrt(sum_squares / count)

    def render(self):
        self.screen.fill(BORDER_COLOUR)

        sw, sh = self.screen.get_size()

        # Draw the 4 buttons
        pygame.draw.rect(self.screen, BORDER_COLOUR, (0, 0, sw / 4, sh))
        labels = ['A/W', 'SPEECH', '', 'GRAPH']
        for i in range(4):
            if i == 0:
                col = BUTTON_BLUE_COLOUR if self.a_weighting else BUTTON_GREY_COLOUR
            elif i == 1:
                col = BUTTON_BLUE_COLOUR if self.speech_enabled else BUTTON_GREY_COLOUR
            elif i == 3:
                col = BUTTON_BLUE_COLOUR if self.show_graph else BUTTON_GREY_COLOUR
            else:
                col = BUTTON_COLOUR

            r = pygame.Rect(BUTTON_PADDING,
                         i * sh / 4 + BUTTON_PADDING,
                         sw / 4 - BUTTON_PADDING * 2,
                         sh / 4 - BUTTON_PADDING * 2)
            pygame.draw.rect(self.screen, col[0], r)
            pygame.draw.line(self.screen, col[1],
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING),
                (sw / 4 - (BUTTON_PADDING + 2), i * sh / 4 + BUTTON_PADDING)
            )
            pygame.draw.line(self.screen, col[2],
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING),
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1))
            )
            pygame.draw.line(self.screen, col[2],
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1)),
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1))
            )
            pygame.draw.line(self.screen, col[3],
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + 1),
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + 1 + sh / 4 - (BUTTON_PADDING * 2 + 3))
            )

            t = FONT_BIG.render(labels[i], 1, FG_COLOUR)
            x = (r.width - t.get_width()) / 2 + r.x
            y = (r.height - (FONT_BIG.get_ascent() - FONT_BIG.get_descent())) / 2 + r.y
            self.screen.blit(t, (x, y))

        # Draw our secondary area
        pygame.draw.rect(self.screen, BG_COLOUR, (sw / 4, 1, sw / 4 * 3 - 1, sh - 2))

        # Now... Now we do the "VU" meters...
        pygame.draw.rect(self.screen, BG_DARKER, (
            sw / 4 * 3 + 1, 1, sw / 4 - 2, sh - 2
        ))
        pygame.draw.line(self.screen, BORDER_COLOUR,
            (sw / 4 * 3, 1),
            (sw / 4 * 3, sh - 2)
        )

        vu_width = 31  # 15 + 15 + 1
        vu_height = sh / 5 * 4
        vu_x = ((sw / 8) - vu_width / 2) + (sw / 4 * 3)
        vu_y = (sh - vu_height) / 2

        pygame.draw.rect(self.screen, BORDER_COLOUR, (vu_x, vu_y, vu_width, vu_height))
        pygame.draw.line(self.screen, BORDER_LIGHT, (vu_x, vu_y + vu_height - 1), (vu_x + vu_width - 1, vu_y + vu_height - 1))

        pygame.draw.line(self.screen, TEXT_COLOUR, (vu_x + vu_width, vu_y), (vu_x + vu_width, vu_y + vu_height - 1))

        for i in range(13):
            x1 = vu_x + vu_width + 1
            y1 = vu_y + max(i * (vu_height - 3) / 12, 0) + 1
            x2 = vu_x + vu_width + 4
            y2 = y1

            pygame.draw.line(self.screen, TEXT_COLOUR, (x1, y1), (x2, y2))

            x1 = vu_x - 1
            x2 = vu_x - 4

            pygame.draw.line(self.screen, TEXT_COLOUR, (x1, y1), (x2, y2))

            t = FONT.render(str(i * 3 + (0 if i < 8 else 3 * (i - 8))), 1, TEXT_COLOUR)
            self.screen.blit(t, (vu_x + vu_width + 5, y1 - (FONT.get_ascent() - FONT.get_descent()) / 2))

        # Bars
        pygame.draw.rect(self.screen, DARK_BLUE, (vu_x + 1, vu_y + 1, (vu_width - 1) / 2 - 1, vu_height / 2 - 1))
        pygame.draw.rect(self.screen, DARK_BLUE, (vu_x + 1, vu_y + vu_height / 2, (vu_width - 1) / 2 - 1, vu_height / 2 - 1))

        def draw_bar(vu, vua, xoff):
            if vu < 18:
                pygame.draw.rect(self.screen, LIGHT_BLUE, (vu_x + 1 + xoff, vu_y + vu_height / 2 - 1, (vu_width - 1) / 2 - 1, vu_height / 2 - 1))
                rem = vu - 18
                h = rem * ((vu_height / 2 - 3) / 18)
                pygame.draw.rect(self.screen, LIGHT_BLUE, (vu_x + 1 + xoff, vu_y + vu_height / 2 - 1, (vu_width - 1) / 2 - 1, h))
            elif vu <= 24:
                rem = 6 - (vu - 18)
                h = rem * ((vu_height / 2 - 2) / 18) + ((vu_height / 2 - 2) / 18) * 12
                pygame.draw.rect(self.screen, LIGHT_BLUE, (vu_x + 1 + xoff, vu_y + vu_height - h - 2, (vu_width - 1) / 2 - 1, h + 1))
            elif vu < 48:
                rem = 24 - (vu - 24)
                h = (rem / 24) * ((vu_height / 2 - 2) / 6) * 4 - 1
                pygame.draw.rect(self.screen, LIGHT_BLUE, (vu_x + 1 + xoff, vu_y + vu_height - 3, (vu_width - 1) / 2 - 1, -h))

            if vua <= 24:
                vua /= 24
                h = vua * (vu_height - 2) / 3 * 2
            else:
                vua -= 24
                vua /= 24
                h = vua * (vu_height - 2) / 3 - 1
                h += (vu_height - 2) / 3 * 2
            h += vu_y + 1
            pygame.draw.rect(self.screen, RED, (vu_x + 1 + xoff, h, (vu_width - 1) / 2 - 1, 2))

        def cross_bar(vu):
            if vu <= 24:
                vu /= 24
                h = vu * (vu_height - 2) / 3 * 2
            else:
                vu -= 24
                vu /= 24
                h = vu * (vu_height - 2) / 3 - 1
                h += (vu_height - 2) / 3 * 2
            h += vu_y + 1
            pygame.draw.rect(self.screen, TEXT_COLOUR, (vu_x + 1, h, vu_width - 2, 1))

        vu = 48 if not self.samples_1 else self.samples_1[-1]

        draw_bar(vu, self.vu_1, 0)

        vu = 48 if not self.samples_2 else self.samples_2[-1]

        pygame.draw.rect(self.screen, DARK_BLUE, (vu_x + (vu_width - 1) / 2 + 1, vu_y + 1, (vu_width - 1) / 2 - 1, vu_height / 2 - 1))
        pygame.draw.rect(self.screen, DARK_BLUE, (vu_x + (vu_width - 1) / 2 + 1, vu_y + vu_height / 2, (vu_width - 1) / 2 - 1, vu_height / 2 - 1))
        draw_bar(vu, self.vu_2, (vu_width - 1) / 2)

        cross_bar(self.quiet)
        cross_bar(self.loud)

        pygame.draw.line(self.screen, BORDER_COLOUR, (sw / 4, sh / 2 - 1), (sw / 4 * 3, sh / 2 - 1))
        if not self.show_graph:
            # Coloured area 1:
            pygame.draw.rect(self.screen, self.a1_colour, (sw / 4 + COLOUR_PADDING, 1 + COLOUR_PADDING, sw / 2 - COLOUR_PADDING * 2, sh / 2 - 2 - COLOUR_PADDING * 2))
            t = FONT_BIG.render(SOURCE_1_LABEL, 1, FG_COLOUR)
            self.screen.blit(t, (sw / 4 + COLOUR_PADDING + 3, 1 + COLOUR_PADDING + 3))
            # Coloured area 2:
            pygame.draw.rect(self.screen, self.a2_colour, (sw / 4 + COLOUR_PADDING, sh / 2 + COLOUR_PADDING, sw / 2 - COLOUR_PADDING * 2, sh / 2 - 1 - COLOUR_PADDING * 2))
            t = FONT_BIG.render(SOURCE_2_LABEL, 1, FG_COLOUR)
            self.screen.blit(t, (sw / 4 + COLOUR_PADDING + 3, sh / 2 + COLOUR_PADDING + 3))
        else:
            # Coloured area 1:
            pygame.draw.rect(self.screen, self.a1_colour, (sw / 4 + COLOUR_PADDING, 1 + COLOUR_PADDING, sw / 4 - COLOUR_PADDING * 2, sh / 2 - 2 - COLOUR_PADDING * 2))
            t = FONT_BIG.render(SOURCE_1_LABEL, 1, FG_COLOUR)
            self.screen.blit(t, (sw / 4 + COLOUR_PADDING + 3, 1 + COLOUR_PADDING + 3))
            # Coloured area 2:
            pygame.draw.rect(self.screen, self.a2_colour, (sw / 2 + COLOUR_PADDING, 1 + COLOUR_PADDING, sw / 4 - COLOUR_PADDING * 2, sh / 2 - 2 - COLOUR_PADDING * 2))
            t = FONT_BIG.render(SOURCE_2_LABEL, 1, FG_COLOUR)
            self.screen.blit(t, (sw / 2 + COLOUR_PADDING + 3, 1 + COLOUR_PADDING + 3))

            # Verticle divider
            pygame.draw.line(self.screen, BORDER_COLOUR, (sw / 2 - 1, 1), (sw / 2 - 1, sh / 2 - 1))

            # Draw 'dat graph
            rect = pygame.Rect(sw / 4 + COLOUR_PADDING, sh / 2 + COLOUR_PADDING, sw / 2 - COLOUR_PADDING * 2, sh / 2 - 1 - COLOUR_PADDING * 2)
            pygame.draw.rect(self.screen, BORDER_COLOUR, rect)
            dx = (rect.width - 1) / (GRAPH_SAMPLES - 1)
            dy = (rect.height - 1) / 48

            lp = None
            for x, y in enumerate(self.graph_samples_1):
                xp = x * dx + rect.x
                yp = y * dy + rect.y
                xp, yp = int(xp), int(yp)

                if lp is not None:
                    pygame.draw.aaline(self.screen, TEXT_COLOUR, lp, (xp, yp), True)

                self.screen.set_at((xp, yp), TEXT_COLOUR)
                lp = (xp, yp)

            lp = None
            for x, y in enumerate(self.graph_samples_2):
                xp = x * dx + rect.x
                yp = y * dy + rect.y
                xp, yp = int(xp), int(yp)

                if lp is not None:
                    pygame.draw.aaline(self.screen, TEXT_COLOUR, lp, (xp, yp), True)

                self.screen.set_at((xp, yp), TEXT_COLOUR)
                lp = (xp, yp)

        # "Round" everything off :P
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING, 1 + COLOUR_PADDING), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING + int(sw / 2) - COLOUR_PADDING * 2 - 1, 1 + COLOUR_PADDING), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING, 1 + COLOUR_PADDING + int(sh / 2) - COLOUR_PADDING * 2 - 3), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING + int(sw / 2) - COLOUR_PADDING * 2 - 1, 1 + COLOUR_PADDING + int(sh / 2) - COLOUR_PADDING * 2 - 3), BG_COLOUR)

        if self.show_graph:
            self.screen.set_at((int(sw / 2) - COLOUR_PADDING - 1, 1 + COLOUR_PADDING), BG_COLOUR)
            self.screen.set_at((int(sw / 2) - COLOUR_PADDING - 1, int(sh / 2) - 2 - COLOUR_PADDING), BG_COLOUR)
            self.screen.set_at((int(sw / 2) + COLOUR_PADDING, 1 + COLOUR_PADDING), BG_COLOUR)
            self.screen.set_at((int(sw / 2) + COLOUR_PADDING, int(sh / 2) - 2 - COLOUR_PADDING), BG_COLOUR)

            self.screen.set_at((int(sw / 2) - 2, 1), BORDER_COLOUR)
            self.screen.set_at((int(sw / 2), 1), BORDER_COLOUR)
            self.screen.set_at((int(sw / 2) - 2, int(sh / 2) - 2), BORDER_COLOUR)
            self.screen.set_at((int(sw / 2), int(sh / 2) - 2), BORDER_COLOUR)

        self.screen.set_at((int(sw / 4) + COLOUR_PADDING, int(sh / 2)  + COLOUR_PADDING), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING + int(sw / 2) - COLOUR_PADDING * 2 - 1, int(sh / 2) + COLOUR_PADDING), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING, int(sh / 2) + COLOUR_PADDING + int(sh / 2) - COLOUR_PADDING * 2 - 2), BG_COLOUR)
        self.screen.set_at((int(sw / 4) + COLOUR_PADDING + int(sw / 2) - COLOUR_PADDING * 2 - 1, int(sh / 2) + COLOUR_PADDING + int(sh / 2) - COLOUR_PADDING * 2 - 2), BG_COLOUR)

        self.screen.set_at((int(sw / 4) * 3 - 1, 1), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4) * 3 + 1, 1), BORDER_COLOUR)
        self.screen.set_at((sw - 2, 1), BORDER_COLOUR)
        self.screen.set_at((sw - 2, sh - 2), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4), 1), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4), sh - 2), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4) * 3 - 1, sh - 2), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4) * 3 + 1, sh - 2), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4), int(sh / 2)), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4), int(sh / 2) - 2), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4) * 3 - 1, int(sh / 2)), BORDER_COLOUR)
        self.screen.set_at((int(sw / 4) * 3 - 1, int(sh / 2) - 2), BORDER_COLOUR)

        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                sw, sh = self.screen.get_size()
                for i in range(4):
                    r = pygame.Rect(BUTTON_PADDING,
                         i * sh / 4 + BUTTON_PADDING,
                         sw / 4 - BUTTON_PADDING * 2,
                         sh / 4 - BUTTON_PADDING * 2)
                    if r.collidepoint(event.pos):
                        if i == 0:
                            self.a_weighting = not self.a_weighting
                        elif i == 1:
                            self.speech_enabled = not self.speech_enabled
                            if self.speech_enabled:
                                self.loud = self.LOUD_SPEECH
                                self.quiet = self.QUIET_SPEECH
                            else:
                                self.loud = self.LOUD_MUSIC
                                self.quiet = self.QUIET_MUSIC
                        elif i == 3:
                            self.show_graph = not self.show_graph

    def read(self, stream):
        data = stream.read(CHUNK, exception_on_overflow=False)

        if not self.a_weighting:
            count = len(data) / 2
            shorts = struct.unpack(str(int(count)) + 'h', data)
            db = self.rms(shorts)
        else:
            data = np.fromstring(data, dtype=np.int16)
            db = self.rms(scipy.signal.lfilter(self.B, self.A, data, axis=0))

        if db:
            db = 20 * math.log10(db)
        else:
            db = 48
        return max(0, min(48, abs(db)))

    def read_stream1(self):
        while self.running:
            v = self.read(self.stream1)
            self.samples_1.append(v)
            self.graph_samples_1.append(v)
            if len(self.samples_1) > AVERAGE_SAMPLES:
                self.samples_1.pop(0)
            if len(self.graph_samples_1) > GRAPH_SAMPLES:
                self.graph_samples_1.pop(0)
            self.vu_1 = sum(self.samples_1) / len(self.samples_1)

            if self.vu_1 >= self.quiet:
                self.a1_colour = ORANGE
            elif self.vu_1 <= self.loud:
                self.a1_colour = RED
            else:
                self.a1_colour = GREEN

    def read_stream2(self):
        return
        while self.running:
            v = self.read(self.stream2)
            self.samples_2.append(v)
            self.graph_samples_2.append(v)
            if len(self.samples_2) > AVERAGE_SAMPLES:
                self.samples_2.pop(0)
            if len(self.graph_samples_2) > GRAPH_SAMPLES:
                self.graph_samples_2.pop(0)
            self.vu_2 = sum(self.samples_2) / len(self.samples_2)

            if self.vu_2 >= self.quiet:
                self.a2_colour = ORANGE
            elif self.vu_2 <= self.loud:
                self.a2_colour = RED
            else:
                self.a2_colour = GREEN

    def main(self):
        while self.running:
            self.render()
            self.events()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == '__main__':
    meter = Meter()
    meter.main()

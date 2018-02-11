#!/usr/bin/env python3

import threading
import struct
import math
import os

import scipy.signal
import numpy as np
import pyaudio
import pygame

from config import *
if RPI:
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ['SDL_FBDEV'] = '/dev/fb1'
    os.environ['SDL_MOUSEDRV'] = 'TSLIB'
    os.environ['SDL_MOUSEDEV'] = '/dev/input/touchscreen'
pygame.init()


FONT = pygame.font.Font('font.ttf', FONT_SIZE)
FONT_BIG = pygame.font.Font('font.ttf', BIG_FONT_SIZE)


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


def butter_pass_filter(data, cutoff, fs, btype, order=5):
    normal_cutoff = cutoff / (0.5 * fs)
    b, a = scipy.signal.butter(order, normal_cutoff, btype=btype, analog=False)
    return scipy.signal.lfilter(b, a, data)


class Meter:
    B, A = A_weighting(RATE)

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT),
                                              (not RPI) * pygame.RESIZABLE, 32)
        if RPI: pygame.mouse.set_visible(False)

        self.running = True

        self.colours = [ORANGE, ORANGE]
        self.graph_samples = [[], []]
        self.samples = [[], []]
        self.vus = [48, 48]

        self.speech_enabled = False
        self.a_weighting = True
        self.show_graph = False
        self.sub_split = False

        if self.speech_enabled:
            self.loud = LOUD_SPEECH
            self.quiet = QUIET_SPEECH
        else:
            self.loud = LOUD_MUSIC
            self.quiet = QUIET_MUSIC

        self.audio = pyaudio.PyAudio()

        self.stream1 = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=DEVICE_1_ID,
        )
        if LINE_IN:
            self.stream2 = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=DEVICE_2_ID,
            )

        thread = threading.Thread(target=self.read_stream1)
        thread.daemon = True
        thread.start()

        if LINE_IN:
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

    def rounded_rect(self, colour, rect):
        if ROUND_CORNERS:
            pygame.draw.rect(self.screen, colour, (rect[0] + 1, rect[1], math.ceil(rect[2] - 2), rect[3]))
            pygame.draw.line(self.screen, colour, (rect[0], rect[1] + 1), (rect[0], rect[1] + rect[3] - 2))
            pygame.draw.line(self.screen, colour, (rect[0] + rect[2] - 1, rect[1] + 1), (rect[0] + rect[2] - 1, rect[1] + rect[3] - 2))
        else:
            pygame.draw.rect(self.screen, colour, (rect[0], rect[1], math.ceil(rect[2]), rect[3]))

    def render(self):
        self.screen.fill(BORDER_COLOUR)

        sw, sh = self.screen.get_size()

        # Draw the 4 buttons
        pygame.draw.rect(self.screen, BORDER_COLOUR, (0, 0, sw / 4, sh))
        labels = ['A/W', 'SPEECH', 'SPLIT', 'GRAPH']
        for i in range(4):
            if i == 0:
                col = BUTTON_BLUE_COLOUR if self.a_weighting else BUTTON_GREY_COLOUR
            elif i == 1:
                col = BUTTON_BLUE_COLOUR if self.speech_enabled else BUTTON_GREY_COLOUR
            elif i == 2 and not LINE_IN:
                col = BUTTON_BLUE_COLOUR if self.sub_split else BUTTON_GREY_COLOUR
            elif i == 2:
                col = BUTTON_DGREY_COLOUR
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
                (sw / 4 - (BUTTON_PADDING + 2), i * sh / 4 + BUTTON_PADDING))
            pygame.draw.line(self.screen, col[2],
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING),
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1)))
            pygame.draw.line(self.screen, col[2],
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1)),
                (sw / 4 - (BUTTON_PADDING + 1), i * sh / 4 + BUTTON_PADDING + sh / 4 - (BUTTON_PADDING * 2 + 1)))
            pygame.draw.line(self.screen, col[3],
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + 1),
                (BUTTON_PADDING, i * sh / 4 + BUTTON_PADDING + 1 + sh / 4 - (BUTTON_PADDING * 2 + 3)))

            t = FONT_BIG.render(labels[i], 1, FG_COLOUR)
            x = (r.width - t.get_width()) / 2 + r.x
            y = (r.height - (FONT_BIG.get_ascent() - FONT_BIG.get_descent())) / 2 + r.y
            self.screen.blit(t, (x, y))

        # Meters
        self.rounded_rect(BG_DARKER, (sw / 4 * 3 + 1, 1, sw / 4 - 2, sh - 2))

        vu_width = sw / 7
        vu_height = sh / 5 * 4
        vu_x = ((sw / 8) - vu_width / 2) + (sw / 4 * 3)
        vu_y = (sh - vu_height) / 2

        pygame.draw.line(self.screen, BORDER_LIGHT, (vu_x, vu_y + vu_height - 1), (vu_x + vu_width - 1, vu_y + vu_height - 1))
        pygame.draw.line(self.screen, TEXT_COLOUR, (vu_x + vu_width, vu_y), (vu_x + vu_width, vu_y + vu_height - 1))

        for i in range(13):
            x1 = vu_x - 4
            x2 = vu_x + vu_width + 4
            y = vu_y + max(i * (vu_height - 3) / 12, 0) + 1

            pygame.draw.line(self.screen, TEXT_COLOUR, (x1, y), (x2, y))

            label = str(i * 3 + (0 if i < 8 else 3 * (i - 8)))
            t = FONT.render(label, 1, TEXT_COLOUR)
            self.screen.blit(t, (vu_x + vu_width + 5, y - (FONT.get_ascent() - FONT.get_descent()) / 2))

        pygame.draw.rect(self.screen, BORDER_COLOUR, (vu_x, vu_y, vu_width, vu_height - 1))

        # Bars
        pygame.draw.rect(self.screen, DARK_BLUE, (vu_x + 1, vu_y + 1, vu_width - 2, vu_height - 3))
        pygame.draw.rect(self.screen, BORDER_COLOUR, (vu_x + vu_width / 2 - 1, vu_y + 1, 1, vu_height - 3))

        def draw_bar(vu, vua, xoff):
            width = math.ceil((vu_width - 1) / 2 - 1)
            xp = vu_x + xoff + 1

            if vu < 18:
                pygame.draw.rect(self.screen, LIGHT_BLUE, (xp, vu_y + vu_height / 2 - 1, width, vu_height / 2 - 1))
                rem = vu - 18
                h = rem * ((vu_height / 2 - 3) / 18)
                pygame.draw.rect(self.screen, LIGHT_BLUE, (xp, vu_y + vu_height / 2 - 1, width, h))
            elif vu <= 24:
                rem = 6 - (vu - 18)
                h = rem * ((vu_height / 2 - 2) / 18) + ((vu_height / 2 - 2) / 18) * 12
                pygame.draw.rect(self.screen, LIGHT_BLUE, (xp, vu_y + vu_height - h - 2, width, h + 1))
            elif vu < 48:
                rem = 24 - (vu - 24)
                h = (rem / 24) * ((vu_height / 2 - 2) / 6) * 4 - 1
                pygame.draw.rect(self.screen, LIGHT_BLUE, (xp, vu_y + vu_height - 3, width, -h))

            if vua < 48:
                if vua <= 24:
                    vua /= 24
                    h = vua * (vu_height - 2) / 3 * 2
                else:
                    vua -= 24
                    vua /= 24
                    h = vua * (vu_height - 2) / 3 - 1
                    h += (vu_height - 2) / 3 * 2
                h += vu_y + 1
                pygame.draw.rect(self.screen, RED, (xp, h, width, 2))

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

        vu = 48 if not self.samples[0] else self.samples[0][-1]
        draw_bar(vu, self.vus[0], 0)

        vu = 48 if not self.samples[1] else self.samples[1][-1]
        draw_bar(vu, self.vus[1], (vu_width - 1) / 2)

        cross_bar(self.quiet)
        cross_bar(self.loud)

        # Labels for the pannels
        s1_t = FONT_BIG.render(S1_SPLIT_LABEL if self.sub_split else SOURCE_1_LABEL, 1, FG_COLOUR)
        s2_t = FONT_BIG.render(S2_SPLIT_LABEL if self.sub_split else SOURCE_2_LABEL, 1, FG_COLOUR)

        vertical_split = self.sub_split or self.show_graph or LINE_IN
        horizontal_split = self.show_graph and (self.sub_split or LINE_IN)

        # Draw the pannels
        if vertical_split and horizontal_split:
            self.rounded_rect(BG_COLOUR, (sw / 4, sh / 2, sw / 2, sh / 2 - 1))
            self.rounded_rect(BG_COLOUR, (sw / 4, 1, sw / 4, sh / 2 - 2))
            self.rounded_rect(BG_COLOUR, (sw / 2 + 1, 1, sw / 4 - 1, sh / 2 - 2))
        elif vertical_split:
            self.rounded_rect(BG_COLOUR, (sw / 4, sh / 2, sw / 2, sh / 2 - 1))
            self.rounded_rect(BG_COLOUR, (sw / 4, 1, sw / 2, sh / 2 - 2))
        else:
            self.rounded_rect(BG_COLOUR, (sw / 4, 1, sw / 2, sh - 2))

        xp = sw / 4 + COLOUR_PADDING
        yp = 1 + COLOUR_PADDING
        width = sw / 2 - COLOUR_PADDING * 2
        height = sh - 2 - COLOUR_PADDING * 2
        half_height = height / 2 - COLOUR_PADDING - 1
        half_width = width / 2 - COLOUR_PADDING
        mid_xp = xp + half_width + COLOUR_PADDING * 2 + 1
        mid_yp = yp + half_height + COLOUR_PADDING * 2 + 1
        # Draw the indicator boxes/graph background
        if vertical_split and horizontal_split:
            self.rounded_rect(self.colours[0], (xp, yp, half_width + 1, half_height))
            self.rounded_rect(self.colours[1], (mid_xp, yp, half_width - 1, half_height))
            self.rounded_rect(BORDER_COLOUR, (xp, mid_yp, width, half_height + 1))
        elif vertical_split:
            self.rounded_rect(self.colours[0], (xp, yp, width, half_height))
            if self.show_graph:
                self.rounded_rect(BORDER_COLOUR, (xp, mid_yp, width, half_height + 1))
            else:
                self.rounded_rect(self.colours[1], (xp, mid_yp, width, half_height + 1))
        else:
            self.rounded_rect(self.colours[0], (xp, yp, width, height))

        # Add labels to the pannels
        self.screen.blit(s1_t, (xp + 2, yp))
        if vertical_split and horizontal_split:
            self.screen.blit(s2_t, (mid_xp + 2, yp))
        elif vertical_split and not self.show_graph:
            self.screen.blit(s2_t, (xp + 2, mid_yp))

        # Draw the graph(s)
        if self.show_graph:
            rect = pygame.Rect(xp, mid_yp, width, half_height)
            dx = (rect.width - 1) / (GRAPH_SAMPLES - 1)
            dy = (rect.height - 1) / 48

            def plot_line(samples, colour):
                lp = None
                for x, y in enumerate(samples):
                    xp = x * dx + rect.x
                    yp = y * dy + rect.y
                    xp, yp = int(xp), int(yp)

                    if lp is not None:
                        pygame.draw.aaline(self.screen, colour, lp, (xp, yp), True)

                    self.screen.set_at((xp, yp), colour)
                    lp = (xp, yp)

            plot_line(self.graph_samples[0], GRAPH_COLOUR)
            if LINE_IN or self.sub_split:
                plot_line(self.graph_samples[1], GRAPH_COLOUR_2)

        if WATERMARK:
            t = FONT.render('bsnk.me/spl', 1, TEXT_COLOUR)
            self.screen.blit(t, (sw - t.get_width() - 2, sh - t.get_height()))

        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode(event.size, (not RPI) * pygame.RESIZABLE, 32)
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
                        elif i == 2 and not LINE_IN:
                            self.sub_split = not self.sub_split
                            if not self.sub_split:
                                self.samples[1] = []
                                self.graph_samples[1] = []
                                self.vus[1] = 48
                        elif i == 1:
                            self.speech_enabled = not self.speech_enabled
                            if self.speech_enabled:
                                self.loud = LOUD_SPEECH
                                self.quiet = QUIET_SPEECH
                            else:
                                self.loud = LOUD_MUSIC
                                self.quiet = QUIET_MUSIC
                        elif i == 3:
                            self.show_graph = not self.show_graph

    def get_db(self, data):
        db = self.rms(data)
        db = 20 * math.log10(db) if db else 48
        return max(0, min(48, abs(db)))

    def read(self, stream):
        data = stream.read(CHUNK, exception_on_overflow=False)

        if self.a_weighting:
            data = np.fromstring(data, dtype=np.int16)
            data = scipy.signal.lfilter(self.B, self.A, data, axis=0)
            db = self.get_db(data)
        else:
            count = len(data) / 2
            shorts = struct.unpack(str(int(count)) + 'h', data)
            db = self.get_db(shorts)
            if self.sub_split:
                data = np.fromstring(data, dtype=np.int16)

        return db, data

    def add_value(self, val, index):
        samples = self.samples[index]
        graph_samples = self.graph_samples[index]

        samples.append(val)
        graph_samples.append(val)
        if len(samples) > AVERAGE_SAMPLES:
            samples.pop(0)
        if len(graph_samples) > GRAPH_SAMPLES:
            graph_samples.pop(0)
        self.vus[index] = sum(samples) / len(samples)

        if self.vus[index] >= self.quiet:
            self.colours[index] = ORANGE
        elif self.vus[index] <= self.loud:
            self.colours[index] = RED
        else:
            self.colours[index] = GREEN

    def read_stream1(self):
        while self.running:
            v, d = self.read(self.stream1)

            if self.sub_split:
                lp_data = butter_pass_filter(d, SPLIT_FREQUENCY, RATE, 'low')
                hp_data = butter_pass_filter(d, SPLIT_FREQUENCY, RATE, 'high')

                lp_db = self.get_db(lp_data)
                hp_db = self.get_db(hp_data)

                self.add_value(lp_db, 1)
                self.add_value(hp_db, 0)
            else:
                self.add_value(v, 0)

    def read_stream2(self):
        while self.running:
            v, _ = self.read(self.stream2)
            self.add_value(v, 1)

    def main(self):
        while self.running:
            self.render()
            self.events()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == '__main__':
    meter = Meter()
    meter.main()

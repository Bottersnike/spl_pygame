import pygame

from .config import load_config
from .utils import Font
from .grid import Pane
from .enums import *
CONFIG, _ = load_config()


pygame.font.init()
FONT = pygame.font.Font('meter/assets/font.ttf', CONFIG.get('font_size', 10))
FONT_BIG = pygame.font.Font('meter/assets/font.ttf', CONFIG.get('big_font_size', 20))


class Button(Pane):
    """A simple widget providing a button that can be inactive, active or disabled."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.text = kwargs.get('text', '')
        self.disabled = kwargs.get('disabled', False)
        self.state = kwargs.get('state', False)
        self.callback = kwargs.get('callback', None)

    def render(self):
        palette = CONFIG['button_dgrey_colour'] if self.disabled else \
            (CONFIG['button_blue_colour'] if self.state else CONFIG['button_grey_colour']) \
            if self.text else CONFIG['button_colour']

        self.surface.fill(CONFIG.get('border_colour', (0, 0, 0)))
        size = self.surface.get_size()
        size = (size[0] - 2, size[1] - 2)
        pygame.draw.rect(self.surface, palette[0], (1, 1, size[0], size[1]))

        pygame.draw.line(self.surface, palette[1], (1, 1), (size[0], 1))
        pygame.draw.line(self.surface, palette[2], (size[0], 1), (size[0], size[1]))
        pygame.draw.line(self.surface, palette[2], (1, size[1]), (size[0], size[1]))
        pygame.draw.line(self.surface, palette[3], (1, 1), (1, size[1]))

        if self.text:
            t = FONT_BIG.render(self.text, 1, CONFIG.get('fg_colour', (0, 0, 0)))
            self.surface.blit(t, ((size[0] - t.get_width()) / 2,
                                  (size[1] - t.get_height()) / 2))

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.disabled: return

            self.state = not self.state
            if self.callback is not None:
                self.callback(event, self.state)


class Indicator(Pane):
    """A widget that provides a block of colour with a label to represent something."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = kwargs.get('label', '')
        self.state = MID

    def render(self):
        col = CONFIG.get('green', (0, 255, 0)) if self.state == MID \
            else CONFIG.get('orange', (255, 127, 0)) if self.state == LOW \
            else CONFIG.get('fg_colour', (255, 0, 0))
        self.outline_and_fill(CONFIG.get('bg_colour', (50, 50, 50)), col)

        if self.label:
            t = FONT_BIG.render(self.label, 1, CONFIG.get('fg_colour', (0, 0, 0)))
            self.surface.blit(t, (CONFIG.get('colour_padding', 4) + 2,
                                  CONFIG.get('colour_padding', 4)))


class Graph(Pane):
    """A widget that renders a graph with two lines plotted.

    `meth`:feed is also provided to feed in data and the buffer will be
    control by this class."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_sets = [[], []]

    def feed(self, set_num, data):
        self.data_sets[set_num].append(data)
        while len(self.data_sets[set_num]) > CONFIG.get('graph_samples', 200):
            self.data_sets[set_num] = self.data_sets[set_num][1:]

    def render(self):
        size = self.surface.get_size()

        self.outline_and_fill(CONFIG.get('bg_colour', (0, 0, 0)),
                              CONFIG.get('border_colour', (0, 0, 0)))

        dx = (size[0] - CONFIG.get('colour_padding', 4) * 2) / CONFIG.get('graph_samples', 200)
        dy = (size[1] - CONFIG.get('colour_padding', 4) * 2) / 48

        def plot_line(samples, colour):
            if len(samples) > 1:
                pygame.draw.lines(self.surface, colour, False, [
                    (size[0] - x * dx - CONFIG.get('colour_padding', 4),
                     y * dy + CONFIG.get('colour_padding', 4))
                    for x, y in enumerate(samples[::-1])
                ])

        plot_line(self.data_sets[0], CONFIG.get('graph_colour', (0, 255, 0)))
        plot_line(self.data_sets[1], CONFIG.get('graph_colour_2', (255, 0, 0)))


class VUMeter(Pane):
    """A widget that provides two "VU" meters side-by-side."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.avg = [48, 48]
        self.curr = [48, 48]

        self.loud = CONFIG.get('loud_music', 3)
        self.quiet = CONFIG.get('quiet_music', 15)

    @staticmethod
    def get_y(vu_height, vu):
        """Calculate the size and position of a bar on the meter"""
        step_size = (vu_height - 4) / 12

        yp = step_size * min(vu, 24) / 3
        if vu > 24:
            yp += step_size * (vu - 24) / 6

        yp = round(yp)
        h = vu_height - yp - 4

        return yp + 1, h

    def meter_bar(self, vu, xoff, width, vu_height, vu_y, colour, height=None):
        """Draw a bar/line on the meter"""
        yp, h = self.get_y(vu_height, vu)

        if h > 1:
            if height is not None:
                h = height

            pygame.draw.rect(self.surface, colour, (xoff, yp + vu_y + 1, width, h))

    def render(self):
        size = self.surface.get_size()
        self.outline_and_fill(CONFIG.get('bg_darker', (0, 0, 0)), None)

        half = size[0] // 4
        vu_width = half * 2 + 1
        vu_height = size[1] / 5 * 4
        vu_x = (size[0] - vu_width) / 2
        vu_y = (size[1] - vu_height) / 2

        pygame.draw.line(self.surface, CONFIG.get('border_light', (100, 100, 100)), (vu_x, vu_y + vu_height - 2), (vu_x + vu_width - 1, vu_y + vu_height - 2))
        pygame.draw.line(self.surface, CONFIG.get('text_colour', (100, 100, 100)), (vu_x + vu_width, vu_y), (vu_x + vu_width, vu_y + vu_height - 3))

        # Draw the scale down the side
        for i in range(13):
            vu = i * 3 + (0 if i < 8 else 3 * (i - 8))
            y, _ = self.get_y(vu_height, vu)
            y += vu_y + 1

            pygame.draw.line(self.surface, CONFIG.get('text_colour', (100, 100, 100)),
                             (vu_x - 4, y), (vu_x + vu_width + 4, y))

            t = FONT.render(str(vu), 1, CONFIG.get('text_colour', (100, 100, 100)))
            # Centre text using descent and ascent
            yp = y - (FONT.get_ascent() - FONT.get_descent()) / 2
            self.surface.blit(t, (vu_x + vu_width + 5, yp))

        pygame.draw.rect(self.surface, CONFIG.get('border_colour', (0, 0, 0)), (vu_x, vu_y, vu_width, vu_height - 1))

        # Draw the background for the bars
        pygame.draw.rect(self.surface, CONFIG.get('dark_blue', (0, 0, 127)), (vu_x + 1, vu_y + 1, vu_width - 2, vu_height - 3))

        def draw_bar(vu, xoff, col, height=None, width=None):
            """Provides a helper class to scope some variables"""
            w = half - 1 if width is None else width
            xoff += vu_x + 1
            self.meter_bar(vu, xoff, w, vu_height, vu_y, col, height)

        # Draw the bars and indicator lines
        draw_bar(self.curr[1], half, CONFIG.get('light_blue', (0, 0, 255)))
        draw_bar(self.curr[0], 0, CONFIG.get('light_blue', (0, 0, 255)))
        draw_bar(self.avg[1], half, CONFIG.get('red', (255, 0, 0)), 2)
        draw_bar(self.avg[0], 0, CONFIG.get('red', (255, 0, 0)), 2)

        draw_bar(self.quiet, 0, CONFIG.get('text_colour', (100, 100, 100)), 1, vu_width - 2)
        draw_bar(self.loud, 0, CONFIG.get('text_colour', (100, 100, 100)), 1, vu_width - 2)

        # Central divider
        pygame.draw.rect(self.surface, CONFIG.get('border_colour', (0, 0, 0)), (vu_x + half, vu_y + 1, 1, vu_height - 3))

        if CONFIG.get('watermark'):
            text = FONT.render('bsnk.me/spl', 1, CONFIG.get('text_colour', (100, 100, 100)))
            self.surface.blit(text, (size[0] - text.get_width() - 2, size[1] - text.get_height()))


class MessageBox(Pane):
    """A widget that renders a block of text until dismissed. Intended to be
    added on its own to a manager instead of within a grid.
    """

    CLOSE_MSG = 'Tap anywhere to close.'

    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message
        self.font = Font('meter/assets/font.ttf')

    def rounded_rect(self, x, y, w, h, col, r):
        pygame.draw.circle(self.surface, col, (x + r, y + r), r)
        pygame.draw.circle(self.surface, col, (w + x - r, y + r), r)
        pygame.draw.circle(self.surface, col, (x + r, h + y - r), r)
        pygame.draw.circle(self.surface, col, (w + x - r, h + y - r), r)
        pygame.draw.rect(self.surface, col, (x, y + r, w, h - r * 2))
        pygame.draw.rect(self.surface, col, (x + r, y, w - r * 2, r))
        pygame.draw.rect(self.surface, col, (x + r, y + h - r, w - r * 2, r))

    def event(self, event):
        if event.type in [pygame.MOUSEBUTTONUP, pygame.KEYUP]:
            del self.parent

    def render(self):
        size = self.surface.get_size()
        self.surface.fill((0, 0, 0, 0))

        self.rounded_rect(20, 20, size[0] - 40, size[1] - 40, CONFIG.get('border_colour', (0, 0, 0)), 10)
        self.rounded_rect(22, 22, size[0] - 44, size[1] - 44, CONFIG.get('bg_colour', (0, 0, 0)), 10)

        lines = [
            self.font.render(size[1] // 20, line, CONFIG.get('message_fg', (255, 255, 255))) for line in [*self.message.split('\n'), '']
        ]
        lines += [
            self.font.render(size[1] // 20, self.CLOSE_MSG, CONFIG.get('message_fg', (255, 255, 255)), True)
        ]
        lines_height = sum(i.get_height() for i in lines)

        y = (size[1] - lines_height) / 2
        for line in lines:
            self.surface.blit(line, ((size[0] - line.get_width()) / 2, y))
            y += line.get_height()

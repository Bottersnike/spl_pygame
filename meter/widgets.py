import pygame

from .config import load_config
from .utils import Font
from .grid import Pane
from .enums import *

CONFIG, _ = load_config()
FONT = Font('assets/font.ttf')


class Button(Pane):
    """
    A button that triggers a callback when pressed. A button can be in one of
    three states:

    1- Enabled
    2- Active
    3- Disabled

    When in state (1) or (2) the callback will be called when pressed. Pressing
    the button while in state (1) or (2) will also toggle it between the two.

    Setting `.disabled` to `True` will **not** set `.state` to `False`. The
    code disabling the button should be responsible for this.
    """

    def __init__(self, *args, **kwargs):
        super().__init__()

        self.text = kwargs.get('text', '')
        self.disabled = kwargs.get('disabled', False)
        self.state = kwargs.get('state', False)
        self.callback = kwargs.get('callback', None)

    def render(self):
        palette = CONFIG['button_dgrey_colour'] if self.disabled else \
            (CONFIG['button_blue_colour'] if self.state else CONFIG['button_grey_colour']) \
                if self.text else CONFIG['button_colour']

        self.surface.fill(palette[0])
        size = self.surface.get_size()

        pygame.draw.line(self.surface, palette[1], (0, 0), (size[0], 0))
        pygame.draw.line(self.surface, palette[2], (size[0] - 1, 0), (size[0] - 1, size[1]))
        pygame.draw.line(self.surface, palette[2], (0, size[1] - 1), (size[0], size[1] - 1))
        pygame.draw.line(self.surface, palette[3], (0, 0), (0, size[1]))

        if self.text:
            t = FONT.render(self.text, CONFIG['fg_colour'], CONFIG['big_font_size'])
            self.surface.blit(t, ((size[0] - t.get_width()) / 2,
                                  (size[1] - t.get_height()) / 2))

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.disabled:
                return

            self.state = not self.state
            if self.callback is not None:
                self.callback(event, self.state)


class Indicator(Pane):
    """
    A pane of solid colour with a label. The state is one of `HIGH`, `MID` or
    `LOW` from `meter.enums`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = kwargs.get('label', '')
        self.state = MID

    def render(self):
        col = CONFIG['green'] if self.state == MID else CONFIG['orange'] if self.state == LOW else CONFIG['red']
        self.outline_and_fill(CONFIG['bg_colour'], col)

        if self.label:
            t = FONT.render(self.label, CONFIG['fg_colour'], CONFIG['big_font_size'])
            self.surface.blit(t, (CONFIG['colour_padding'] + 2, CONFIG['colour_padding']))


class Graph(Pane):
    """
    A basic graph without labels or axises. Data is fed in through `.feed` and
    up to two sets of data can be plotted at once. No fitting is performed, so
    data points are joined up using a direct straight line.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_sets = [[], []]

    def feed(self, set_num, data):
        self.data_sets[set_num].append(data)
        while len(self.data_sets[set_num]) > CONFIG['graph_samples']:
            self.data_sets[set_num] = self.data_sets[set_num][1:]

    def render(self):
        size = self.surface.get_size()

        self.outline_and_fill(CONFIG['bg_colour'], CONFIG['border_colour'])

        dx = (size[0] - CONFIG['colour_padding'] * 2) / CONFIG['graph_samples']
        dy = (size[1] - CONFIG['colour_padding'] * 2) / 48

        def plot_line(samples, colour):
            if len(samples) > 1:
                pygame.draw.lines(self.surface, colour, False, [
                    (size[0] - x * dx - CONFIG['colour_padding'], y * dy + CONFIG['colour_padding'])
                    for x, y in enumerate(samples[::-1])
                ])

        plot_line(self.data_sets[0], CONFIG['graph_colour'])
        plot_line(self.data_sets[1], CONFIG['graph_colour_2'])


class VUMeter(Pane):
    """
    A dual "VU" meter display. Data is fed in by setting `.avg` and `.curr`.
    When only one bar is being used, the other just sits at -48. The average
    is displayed using a horizontal cross bar.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.avg = [48, 48]
        self.curr = [48, 48]

        self.loud = CONFIG['loud_music']
        self.quiet = CONFIG['quiet_music']

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
        self.outline_and_fill(CONFIG['bg_darker'], None)

        half = size[0] // 4
        vu_width = half * 2 + 1
        vu_height = size[1] / 5 * 4
        vu_x = (size[0] - vu_width) / 2
        vu_y = (size[1] - vu_height) / 2

        pygame.draw.line(self.surface, CONFIG['border_light'], (vu_x, vu_y + vu_height - 2),
                         (vu_x + vu_width - 1, vu_y + vu_height - 2))
        pygame.draw.line(self.surface, CONFIG['text_colour'], (vu_x + vu_width, vu_y),
                         (vu_x + vu_width, vu_y + vu_height - 3))

        # Draw the scale down the side
        for i in range(13):
            vu = i * 3 + (0 if i < 8 else 3 * (i - 8))
            y, _ = self.get_y(vu_height, vu)
            y += vu_y + 1

            pygame.draw.line(self.surface, CONFIG['text_colour'],
                             (vu_x - 4, y), (vu_x + vu_width + 4, y))

            t = FONT.render(str(vu), CONFIG['text_colour'], CONFIG['font_size'])
            # Centre text using descent and ascent
            yp = y - (FONT.get_ascent(CONFIG['font_size']) - FONT.get_descent(CONFIG['font_size'])) / 2
            self.surface.blit(t, (vu_x + vu_width + 5, yp))

        pygame.draw.rect(self.surface, CONFIG['border_colour'], (vu_x, vu_y, vu_width, vu_height - 1))

        # Draw the background for the bars
        pygame.draw.rect(self.surface, CONFIG['dark_blue'], (vu_x + 1, vu_y + 1, vu_width - 2, vu_height - 3))

        def draw_bar(vu, xoff, col, height=None, width=None):
            """Provides a helper class to scope some variables"""
            w = half - 1 if width is None else width
            xoff += vu_x + 1
            self.meter_bar(vu, xoff, w, vu_height, vu_y, col, height)

        # Draw the bars and indicator lines
        draw_bar(self.curr[1], half, CONFIG['light_blue'])
        draw_bar(self.curr[0], 0, CONFIG['light_blue'])
        draw_bar(self.avg[1], half, CONFIG['red'], 2)
        draw_bar(self.avg[0], 0, CONFIG['red'], 2)

        draw_bar(self.quiet, 0, CONFIG['text_colour'], 1, vu_width - 2)
        draw_bar(self.loud, 0, CONFIG['text_colour'], 1, vu_width - 2)

        # Central divider
        pygame.draw.rect(self.surface, CONFIG['border_colour'], (vu_x + half, vu_y + 1, 1, vu_height - 3))

        # Render the watermark
        if CONFIG['watermark']:
            watermark = FONT.render("https://bsnk.me/spl", CONFIG['text_colour'], CONFIG['font_size'])
            self.surface.blit(watermark, (size[0] - watermark.get_width() - 2,
                                          size[1] - watermark.get_height()))


class MessageBox(Pane):
    """
    A simple message box that can be dismissed by tapping on the screen.
    Best used as a direct child of root (auto-wrapped in a `SingleManager`),
    but theoretically could be gridded like any other pane.
    """

    def __init__(self, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message

        lines = self.message.split('\n')
        self.lines = list(zip([CONFIG['mid_font_size']] * len(lines), lines))
        self.lines.append((CONFIG['font_size'], 'Tap anywhere to continue'))

    def rounded_rect(self, x, y, w, h, col, r):
        pygame.draw.circle(self.surface, col, (x + r, y + r), r)
        pygame.draw.circle(self.surface, col, (w + x - r, y + r), r)
        pygame.draw.circle(self.surface, col, (x + r, h + y - r), r)
        pygame.draw.circle(self.surface, col, (w + x - r, h + y - r), r)
        pygame.draw.rect(self.surface, col, (x, y + r, w, h - r * 2))
        pygame.draw.rect(self.surface, col, (x + r, y, w - r * 2, r))
        pygame.draw.rect(self.surface, col, (x + r, y + h - r, w - r * 2, r))

    def render(self):
        size = self.surface.get_size()
        self.surface.fill((0, 0, 0, 0))

        self.rounded_rect(20, 20, size[0] - 40, size[1] - 40, CONFIG['bg_colour'], 10)
        self.rounded_rect(22, 22, size[0] - 44, size[1] - 44, CONFIG['bg_darker'], 8)
        self.rounded_rect(24, 24, size[0] - 48, size[1] - 48, CONFIG['bg_colour'], 6)

        y = (size[1] - FONT.get_height(CONFIG['mid_font_size']) * len(self.lines)) / 2
        for font_size, line in self.lines:
            text = FONT.render(line, CONFIG['fg_colour'], font_size)
            self.surface.blit(text, ((size[0] - text.get_width()) / 2, y))
            y += FONT.get_height(font_size)

    def event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.destroy()

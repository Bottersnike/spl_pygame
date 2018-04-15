import pygame


class Font:
    def __init__(self, filename):
        self._filename = filename
        self._font_cache = {}
        self._render_cache = {}

    def render(self, size, text, colour, italic=False):
        colour = tuple(colour)
        if (size, text, colour) not in self._render_cache:
            if size not in self._font_cache:
                self._font_cache[(size, italic)] = pygame.font.Font(self._filename, size)
                if italic:
                    self._font_cache[(size, italic)].set_italic(True)
            self._render_cache[(size, text, colour)] = self._font_cache[(size, italic)].render(text, 1, colour)
        return self._render_cache[(size, text, colour)]

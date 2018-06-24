import pygame

import os


class Font:
    """
    Provides a caching wrapper around pygame.font.Font.
    Usually speeds up rendering significantly by rendering once then just
    retrieving from RAM on future render calls.
    """
    def __init__(self, filename):
        self._cache = {}
        self._fonts = {}

        self.filename = os.path.join(os.path.dirname(__file__), filename)

    def _get_font(self, size):
        if size in self._fonts:
            return self._fonts[size]

        font = pygame.font.Font(self.filename, size)
        self._fonts[size] = font

        return font

    def render(self, text, colour, size):
        colour = tuple(colour)

        if (text, colour, size) in self._cache:
            return self._cache[text, colour, size]

        text = self._get_font(size).render(text, 1, colour)
        self._cache[text, colour, size] = text

        return text

    def get_ascent(self, size):
        return self._get_font(size).get_ascent()

    def get_descent(self, size):
        return self._get_font(size).get_descent()

    def get_height(self, size):
        return self._get_font(size).get_height()

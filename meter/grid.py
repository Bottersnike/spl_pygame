import pygame

from .config import load_config
CONFIG, _ = load_config()


class Manager:
    """
    A base class that all pane managers will inherit from.
    This provides render and event propagation to children.

    Currently inheriting classes:
    - RootWindow
    - GriddingManager
    - SingleManager
    """

    def __init__(self):
        self._children = {}

    def remove(self, child):
        if child in self._children:
            del self._children[child]

    def request_position(self, child):
        return 0, 0

    def request_size(self, child):
        return 0, 0

    def render(self, surface, position):
        """Request re-draws from children then push to the screen."""
        for child in self._children:
            rel_pos = self.request_position(child)
            if not isinstance(child, Manager):
                pos = (rel_pos[0] + position[0] + CONFIG.get('padding', 0.5),
                       rel_pos[1] + position[1] + CONFIG.get('padding', 0.5))

                child.render()
                surface.blit(child.surface, pos)
            else:
                pos = (rel_pos[0] + position[0],
                       rel_pos[1] + position[1])

                child.render(surface, pos)

    def event(self, event, position):
        """Propagate an event through all the children."""
        for child in list(self._children.keys()):
            pos = self.request_position(child)
            pos = (pos[0] + position[0], pos[1] + position[1])
            if not hasattr(event, 'pos'):
                if isinstance(child, Manager):
                    child.event(event, pos)
                    continue
                child.event(event)
                continue

            if not child.visible: continue
            size = self.request_size(child)
            rect = pygame.Rect(*pos, *size)

            if rect.collidepoint(*event.pos):
                if isinstance(child, Manager):
                    child.event(event, pos)
                else:
                    child.event(event)

    def tick(self):
        """Propagate a tick through all the children."""
        for child in list(self._children.keys()):
            child.tick()


class Gridable:
    """This  class represents any object that can be a child of a manager."""
    def __init__(self, *args, **kwargs):
        self._parent = None
        self.visible = True
        self.row_span = kwargs.get('row_span', 1)
        self.col_span = kwargs.get('col_span', 1)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        assert isinstance(parent, Manager)
        self._parent = parent

    @parent.deleter
    def parent(self):
        self._parent.remove_child(self)
        self._parent = None

    def tick(self):
        pass


class Pane(Gridable):
    """This represents a child that provides a surface for drawing onto."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._surface = None

    @property
    def surface(self):
        assert self.parent is not None

        size = self.parent.request_size(self)
        size = (size[0] - CONFIG.get('padding', 0.5) * 2,
                size[1] - CONFIG.get('padding', 0.5) * 2)
        if self._surface is None:
            self._surface = pygame.Surface(size).convert_alpha()
        elif self._surface.get_size() != size:
            surf = pygame.Surface(size).convert_alpha()
            surf.blit(self._surface, (0, 0))
            self._surface = surf

        return self._surface

    def render(self):
        """This method is called when the manager desires a re-draw."""
        pass

    def event(self, event):
        """This method is called with any propagated events."""
        pass

    def outline_and_fill(self, bg, mg):
        size = self.surface.get_size()

        self.surface.fill(bg)
        self.surface.set_at((0, 0), (0, 0, 0))
        self.surface.set_at((size[0] - 1, 0), (0, 0, 0))
        self.surface.set_at((0, size[1] - 1), (0, 0, 0))
        self.surface.set_at((size[0] - 1, size[1] - 1), (0, 0, 0))

        if mg:
            x = CONFIG.get('colour_padding', 4)
            y = CONFIG.get('colour_padding', 4)
            w = size[0] - CONFIG.get('colour_padding', 4) * 2
            h = size[1] - CONFIG.get('colour_padding', 4) * 2

            pygame.draw.rect(self.surface, mg, (x + 1, y, w - 2, h))
            pygame.draw.line(self.surface, mg, (x, y + 1), (x, y + h - 2))
            pygame.draw.line(self.surface, mg, (w + x - 1, y + 1), (w + x - 1, y + h - 2))


class GridingManager(Gridable, Manager):
    """
    This is a basic manager that provides a griding interface for panes.

    Both `Manager` and `Gridable` have been inherited to allow for stacking
    of managers within managers.
    """
    def __init__(self):
        Gridable.__init__(self)
        Manager.__init__(self)
        self.rows = 0
        self.columns = 0

    def grid(self, child, column, row):
        """Add a new child into the gridding system."""
        assert isinstance(child, Gridable)
        self.rows = max(self.rows, row + 1)
        self.columns = max(self.columns, column + 1)
        self._children[child] = (column, row)

        child.parent = self
        return child

    def request_position(self, child):
        """Compute the relative location for any given child."""
        if child not in self._children: return 0, 0
        self_size = self.parent.request_size(self)

        cell_w = self_size[0] / self.columns
        cell_h = self_size[1] / self.rows

        return cell_w * self._children[child][0], cell_h * self._children[child][1]

    def request_size(self, child):
        """Compute the desired size for any given child."""
        self_size = self.parent.request_size(self)
        if child not in self._children: return self_size

        cell_w = self_size[0] // self.columns
        cell_h = self_size[1] // self.rows

        return (cell_w * child.col_span,
                cell_h * child.row_span)


class SingleManager(Manager):
    """
    This is a wrapper manager that only contains one child. This is used by the
    root window when a widget is parented to it.
    """
    def set_c(self, child):
        """Add a new child into the griding system."""
        assert isinstance(child, Gridable)
        self._children[child] = None

        child.parent = self
        return child

    def request_position(self, child):
        """Compute the relative location for any given child."""
        return 0, 0

    def request_size(self, child):
        """Compute the desired size for any given child."""
        return self.parent.request_size(self)

    def remove_child(self, _):
        self.parent.remove_child(self)
        del self


class RootWindow(Manager):
    """
    This class 'owns' the connection to the screen and is the root propagator of
    all events and render requests.

    It allows for a single child to be attached. This is recommended to be a
    manager, although any `Griddable` element is accepted.

    TODO: Allow for multiple stacked children.
    """
    def __init__(self, screen):
        super().__init__()

        self._screen = screen
        self._children = []
        self.clock = pygame.time.Clock()

        self.running = True

    def render(self, *args):
        """Request that the child elements perform a render check."""
        self._screen.fill(CONFIG.get('border_colour', (0, 0, 0)))

        for c in self._children:
            c.render(self._screen, (0, 0))

        pygame.display.update()

    def events(self):
        """Collect all pending events, handle core ones, then propagate."""
        self.clock.tick(CONFIG.get('fps', 30))

        event = pygame.event.poll()
        while event.type != pygame.NOEVENT:
            if event.type == pygame.VIDEORESIZE:
                self._screen = pygame.display.set_mode(event.size, (not CONFIG.get('rpi')) * pygame.RESIZABLE, 32)
            elif event.type == pygame.QUIT:
                self.running = False
                return

            if self._children:
                self._children[-1].event(event, (0, 0))

            event = pygame.event.poll()
        pygame.time.wait(10)

    def tick(self):
        """Give all children a chance to process frame-based logic"""
        for c in self._children:
            c.tick()

    def add_child(self, child):
        """Add a child element."""
        if not isinstance(child, Manager):
            nc = SingleManager()
            nc.set_c(child)
            child = nc
        self._children.append(child)
        child.parent = self

        return child

    def remove_child(self, child):
        """Remove a child from this parent."""
        if child in self._children:
            self._children.remove(child)
            child.parent = None
        return child

    def request_size(self, child):
        """This implements the expected method of any `Manager`."""
        return self._screen.get_size()

    def mainloop(self):
        """
        Take control of the thread and process all events.

        THIS IS A BLOCKING CALL. It will never return while the widow is still open.
        """
        while self.running:
            self.render()
            self.events()
            self.tick()
        pygame.quit()

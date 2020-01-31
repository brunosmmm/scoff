"""Generic regex-based parser."""

from collections import deque
from scoff.parsers.linematch import MatcherError, LineMatcher


class ParserError(Exception):
    """Parser error."""


class DataParser:
    """Simple data parser."""

    def __init__(self, initial_state=None):
        """Initialize."""
        self._state_stack = deque()
        self._state = initial_state

    @property
    def state(self):
        """Get current state."""
        return self._state

    def _handle_match(self, candidate):
        """Handle candidate match."""

    def _handle_options(self, **options):
        """Handle candidate options."""

    def _try_parse(self, candidates, data):
        for candidate in candidates:
            try:
                if not isinstance(candidate, LineMatcher):
                    raise TypeError("candidate must be LineMatcher object")
                size, fields = candidate.parse_first(data)
            except MatcherError:
                continue

            options = candidate.options.copy()
            change_state = options.pop("change_state", None)
            push_state = options.pop("push_state", None)
            pop_state = options.pop("pop_state", None)
            if change_state is not None:
                self._state = change_state
            elif push_state is not None:
                self._state_stack.append(self._state)
                self._state = push_state
            elif pop_state is not None:
                for num in range(pop_state):
                    state = self._state_stack.popleft()
                self._state = state

            # handle other options
            self._handle_options(**options)
            # handle other custom options
            self._handle_match(candidate)
            return (size, candidate, fields)
        raise ParserError("could not parse data")

    def _current_state_function(self, data):
        if not hasattr(self, "_state_{}".format(self._state)):
            raise RuntimeError(f"in unknown state: {self._state}")

        return getattr(self, "_state_{}".format(self._state))(data)

    def parse(self, data):
        """Parse data."""
        while len(data):
            size = self._current_state_function(data)
            # consume data
            data = data[size + 1 :]

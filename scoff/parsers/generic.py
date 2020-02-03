"""Generic regex-based parser."""

from collections import deque
from typing import Union, Any, List, Deque, Tuple, Dict
from scoff.parsers.linematch import MatcherError, LineMatcher


class ParserError(Exception):
    """Parser error."""


class DataParser:
    """Simple data parser."""

    def __init__(
        self,
        initial_state: Union[str, int, None] = None,
        consume_spaces: bool = False,
    ):
        """Initialize.

        Arguments
        ---------
        initial_state
          Initial state of the parser
        consume_spaces
          Consume stray space characters
        """
        self._state_stack: Deque[Union[str, int, None]] = deque()
        self._state = initial_state
        self._consume = consume_spaces
        self._current_position = 0
        self._current_line = 0

    @property
    def state(self):
        """Get current state."""
        return self._state

    def _handle_match(self, candidate):
        """Handle candidate match."""

    def _handle_options(self, **options: Any):
        """Handle candidate options."""

    def _try_parse(
        self, candidates: List[LineMatcher], data: str
    ) -> Tuple[int, LineMatcher, Dict[str, str]]:
        for candidate in candidates:
            try:
                if not isinstance(candidate, LineMatcher):
                    raise TypeError("candidate must be LineMatcher object")
                size, fields = candidate.parse_first(data, strip=self._consume)
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
            # advance position
            self._current_position += size
            # advance line
            matched_str = data[:size]
            self._current_line += matched_str.count("\n")
            return (size, candidate, fields)
        raise ParserError("could not parse data")

    def _current_state_function(self, data: str) -> int:
        if not hasattr(self, "_state_{}".format(self._state)):
            raise RuntimeError(f"in unknown state: {self._state}")

        return getattr(self, "_state_{}".format(self._state))(data)

    @property
    def current_pos(self):
        """Get current position."""
        return self._current_position

    @property
    def current_line(self):
        """Get current line."""
        return self._current_line

    def parse(self, data: str):
        """Parse data.

        Arguments
        ---------
        data
          Textual data to be parsed
        """
        self._current_position = 0
        self._current_line = 0
        while len(data):
            size = self._current_state_function(data)
            # consume data
            data = data[size + 1 :]

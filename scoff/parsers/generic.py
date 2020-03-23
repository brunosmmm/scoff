"""Generic regex-based parser."""

import re
from collections import deque
from typing import Union, Any, List, Deque, Tuple, Dict
from scoff.parsers.linematch import MatcherError, LineMatcher

EMPTY_LINE = re.compile(b"\s*$")


class ParserError(Exception):
    """Parser error."""


class DataParser:
    """Simple data parser."""

    def __init__(
        self,
        initial_state: Union[str, int, None] = None,
        consume_spaces: bool = False,
        **kwargs,
    ):
        """Initialize.

        Arguments
        ---------
        initial_state
          Initial state of the parser
        consume_spaces
          Consume stray space characters
        """
        self._state_hooks = {}
        super().__init__(**kwargs)
        self._state_stack: Deque[Union[str, int, None]] = deque()
        self._state = initial_state
        self._consume = consume_spaces
        self._current_position = 1
        self._current_line = 1
        self._data = None
        self._abort = False

    @property
    def state(self):
        """Get current state."""
        return self._state

    def add_state_hook(self, state, hook):
        """Add state hook."""
        if not callable(hook):
            raise TypeError("hook must be callable")
        if state not in self.states:
            print(self.states)
            raise ParserError(f"unknown state '{state}'")
        if state not in self._state_hooks:
            self._state_hooks[state] = {hook}
        else:
            self._state_hooks[state] |= {hook}

    def _handle_match(self, candidate):
        """Handle candidate match."""

    def _handle_options(self, **options: Any):
        """Handle candidate options."""

    def _try_parse(
        self, candidates: List[LineMatcher], position: int
    ) -> Tuple[int, LineMatcher, Dict[str, str]]:
        if self._consume:
            m = EMPTY_LINE.match(self._data, position)
            if m is not None:
                # an empty line, consume
                return (m.span()[1], None, None)

        for candidate in candidates:
            try:
                if not isinstance(candidate, LineMatcher):
                    raise TypeError("candidate must be LineMatcher object")
                size, fields = candidate.parse_first(self._data, position)
            except MatcherError:
                continue

            options = candidate.options.copy()
            change_state = options.pop("change_state", None)
            push_state = options.pop("push_state", None)
            pop_state = options.pop("pop_state", None)
            if change_state is not None:
                self._change_state(change_state)
            elif push_state is not None:
                self._push_state(push_state)
            elif pop_state is not None:
                self._pop_state(pop_state)

            # handle other options
            self._handle_options(**options)
            # handle other custom options
            self._handle_match(candidate)
            # advance position
            self._current_position += size
            # advance line
            self._current_line += (
                self._data.count(b"\n", position, position + size) + 1
            )
            return (size, candidate, fields)
        raise ParserError("could not parse data")

    def _current_state_function(self, position: int) -> int:
        if not hasattr(self, "_state_{}".format(self._state)):
            raise RuntimeError(f"in unknown state: {self._state}")

        size, stmt, fields = getattr(self, "_state_{}".format(self._state))(
            position
        )
        # call hooks
        if self._state in self._state_hooks:
            for hook in self._state_hooks[self._state]:
                hook(self._state, stmt, fields)
        return size

    def _abort_parser(self):
        """Stop parsing."""
        self._abort = True

    @property
    def current_pos(self):
        """Get current position."""
        return self._current_position

    @property
    def current_line(self):
        """Get current line."""
        return self._current_line

    @property
    def states(self):
        """Get possible states."""
        return [
            attr_name.split("_")[2]
            for attr_name in dir(self)
            if attr_name.startswith("_state")
        ]

    def parse(self, data: str) -> int:
        """Parse data.

        Arguments
        ---------
        data
          Textual data to be parsed
        """
        self._data = data.encode()
        self._current_position = 1
        self._current_line = 1
        current_pos = 0
        while current_pos < len(data):
            if self._abort is True:
                break
            size = self._current_state_function(current_pos)
            # consume data
            current_pos += size + 1

        return current_pos

    def _state_change_handler(self, old_state, new_state):
        """State change handler."""

    def _change_state(self, new_state):
        """Change state."""
        old_state = self._state
        self._state = new_state
        # call state change handler
        self._state_change_handler(old_state, new_state)

    def _push_state(self, new_state):
        """Push into state stack and change state."""
        self._state_stack.append(self._state)
        self._change_state(new_state)

    def _pop_state(self, count):
        """Pop from state stack and change state."""
        for num in range(count):
            state = self._state_stack.popleft()
        self._change_state(state)

"""Generic regex-based parser."""

import re
from collections import deque
from typing import Union, Any, List, Deque, Tuple, Dict, Callable
from scoff.parsers.linematch import MatcherError, LineMatcher
from scoff.parsers.token import SimpleToken, SimpleTokenField, TokenMatcher

EMPTY_LINE = re.compile(b"\s*$")


class ParserError(Exception):
    """Parser error."""


class DataParser:
    """Simple data parser.

    Tokens are regular expression-based
    """

    def __init__(
        self,
        initial_state: Union[str, int, None] = None,
        consume_spaces: bool = False,
        **kwargs,
    ):
        """Initialize.

        :param initial_state: Initial state of the parser
        :param consume_spaces: Consume stray space characters
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

    def add_state_hook(self, state: Union[str, int], hook: Callable):
        """Add state hook (callback).

        A callback will be called when the parser reaches a specified state.

        :param state: The parser state to add a callback to
        :param hook: The callback to be added
        """
        if not callable(hook):
            raise TypeError("hook must be callable")
        if state not in self.states:
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
        self,
        candidates: List[TokenMatcher],
        position: int,
    ) -> Tuple[int, LineMatcher, Dict[str, str]]:
        if self._consume:
            m = EMPTY_LINE.match(self._data, position)
            if m is not None:
                # an empty line, consume
                start, end = m.span()
                return (end - start, None, None, None, m.group(0))

        for candidate in candidates:
            try:
                if not isinstance(candidate, TokenMatcher):
                    raise TypeError("candidate must be TokenMatcher object")
                size, fields, text, consumed = candidate.parse_first(
                    self._data, position, self._consume
                )
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
            if candidate.matches_newline:
                self._current_line += (
                    self._data.count(b"\n", position, position + size) + 1
                )
            return (size, candidate, fields, text, consumed)
        raise ParserError(f"could not parse data at position {position}")

    def _current_state_function(self, position: int) -> int:
        if not hasattr(self, "_state_{}".format(self._state)):
            raise RuntimeError(f"in unknown state: {self._state}")

        try:

            ret = getattr(self, "_state_{}".format(self._state))(position)
            size, _, stmt, fields, _ = ret

        except TypeError:
            raise
            raise ParserError("error in state function")
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

        :param data: Textual data to be parsed
        :return: Current position in data
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
            current_pos += size

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

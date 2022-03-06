"""Generic Parser tokens."""

from typing import Union, Tuple, Dict
import re

WHITESPACE = re.compile(b"\s+")


class MatcherError(Exception):
    """Parser error."""


class TokenMatcher:
    """Token matcher."""

    def __init__(self, pattern, **kwargs):
        """Initialize."""
        self._pattern = pattern
        self._options = kwargs

    @property
    def matches_newline(self):
        """Get whether we match the new line character."""
        return False

    def parse_first(
        self, text: bytes, position: int, consume_whitespace=False
    ) -> Tuple[int, Dict[str, str]]:
        """Try to parse first occurrence.

        :param text: Textual data to be parsed
        :param position: Position in text to start parsing at
        :return: A tuple containing the number of characters consumed and \
        a dictionary containing the tokens parsed by field name
        """
        whitespace_size = 0
        if consume_whitespace:
            m = WHITESPACE.match(text, position)
            if m is not None:
                start, end = m.span()
                whitespace_size += end - start

        old_position = position
        position += whitespace_size
        match = self._pattern.match(text, position)
        if match is None:
            raise MatcherError("failed to parse.")
        start, end = match.span()

        decoded_groups = []
        for group in match.groups():
            if group is None:
                decoded_groups.append(None)
            else:
                decoded_groups.append(group.decode())

        return (
            end - start + whitespace_size,
            {idx: value for idx, value in enumerate(decoded_groups)},
            match.group(0),
            text[old_position:position] if consume_whitespace else None,
        )

    @property
    def options(self):
        """Get options."""
        return self._options


class SimpleToken(TokenMatcher):
    """A simple token."""

    def __init__(self, regex: Union[str, bytes], token_type=None, **kwargs):
        """Initialize.

        :param regex: Regular expression to match token to
        """
        super().__init__(re.compile(regex), **kwargs)
        if not isinstance(regex, (str, bytes)):
            raise TypeError("must be string")
        self._regex = regex
        self._type = token_type

    @property
    def token_type(self):
        """Get token type."""
        return self._type

    @property
    def regex(self):
        """Get regex."""
        return self._regex

    @property
    def compiled_regex(self):
        """Get compiled regex."""
        return self._pattern

    @property
    def matches_newline(self):
        """Get whether we match the new line character."""
        return b"$" in self._regex


class SimpleTokenField(SimpleToken):
    """A field token."""

    def __init__(
        self, field_name: Union[str, bytes], regex: Union[str, bytes], **kwargs
    ):
        """Initialize.

        :param field_name: Field name associated to token
        :param regex: Regular expression to match token to
        """
        super().__init__(regex, **kwargs)
        self._name = field_name

    @property
    def name(self):
        """Get field name."""
        return self._name

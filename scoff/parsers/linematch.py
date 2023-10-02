"""Generic line matcher."""

import re
from typing import Union, Any, Tuple, Dict
from scoff.parsers.token import (
    SimpleToken,
    SimpleTokenField,
    MatcherError,
    TokenMatcher,
)


class LineMatcher(TokenMatcher):
    """Line matcher parser.

    Tries to match an entire line defined by token compositions.
    """

    def __init__(
        self,
        *tokens: Union[str, SimpleToken],
        gobble: bool = True,
        **kwargs: Any
    ):
        """Initialize.

        :param tokens: List of tokens which compose the line
        :param gobble: Whether to consume whitespace or not
        :param kwargs: Other generic keyword arguments
        """
        self._tokens = []
        for token in tokens:
            if not isinstance(token, (str, bytes, SimpleToken)):
                raise TypeError("tokens must be either string or SimpleToken")
            if isinstance(token, (str, bytes)):
                self._tokens.append(SimpleToken(token))
            else:
                self._tokens.append(token)

        self._ordered_fields = [
            token
            for token in self._tokens
            if isinstance(token, SimpleTokenField)
        ]

        self._gobble = gobble
        gobble_str = b"\s*" if gobble is True else b""
        super().__init__(
            re.compile(
                gobble_str + b"".join([token.regex for token in self._tokens]),
                re.S,
            ),
            **kwargs
        )

    def parse_first(
        self, text: bytes, position: int, consume_whitespace=False
    ) -> Tuple[int, Dict[str, str]]:
        """Try to parse first occurrence.

        :param text: Textual data to be parsed
        :param position: Position in text to start parsing at
        :return: A tuple containing the number of characters consumed and \
        a dictionary containing the tokens parsed by field name
        """
        span, matches, text, consumed = super().parse_first(
            text, position, consume_whitespace
        )

        return (
            span,
            {
                field.name: matches[idx]
                for idx, field in enumerate(self._ordered_fields)
            },
            text,
            consumed,
        )

    def parse(self, line: str) -> Dict[str, str]:
        """Parse a line.

        :param line: Line of text to be parsed
        :return: Dictionary containing parsed tokens with field names
        """
        match = self._pattern.match(line)
        if match is None:
            raise MatcherError("failed to parse line.")

        # assemble byproducts
        return {
            field.name: value
            for field, value in zip(self._ordered_fields, match.groups())
        }

    @property
    def matches_newline(self):
        """Get whether this matches the new line character."""
        return True

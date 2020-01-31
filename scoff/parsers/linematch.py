"""Generic line matcher."""

import re
from scoff.parsers.token import SimpleToken, SimpleTokenField


class MatcherError(Exception):
    """Parser error."""


class LineMatcher:
    """Line matcher."""

    def __init__(self, *tokens, **kwargs):
        """Initialize."""
        self._tokens = []
        for token in tokens:
            if not isinstance(token, (str, SimpleToken)):
                raise TypeError("tokens must be either string or SimpleToken")
            if isinstance(token, str):
                self._tokens.append(SimpleToken(token))
            else:
                self._tokens.append(token)

        self._ordered_fields = [
            token
            for token in self._tokens
            if isinstance(token, SimpleTokenField)
        ]

        self._pattern = re.compile(
            r"^" + r"".join([token.regex for token in self._tokens]), re.S
        )

        self._options = kwargs

    @property
    def options(self):
        """Get options."""
        return self._options

    def parse_first(self, text):
        """Try to parse first occurrence."""
        match = self._pattern.match(text)
        if match is None:
            raise MatcherError("failed to parse.")
        _, match_size = match.span()

        return (
            match_size,
            {
                field.name: value
                for field, value in zip(self._ordered_fields, match.groups())
            },
        )

    def parse(self, line):
        """Parse a line."""
        match = self._pattern.match(line)
        if match is None:
            raise MatcherError("failed to parse line.")

        # assemble byproducts
        return {
            field.name: value
            for field, value in zip(self._ordered_fields, match.groups())
        }

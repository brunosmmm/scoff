"""Generic Parser tokens."""

from typing import Union


class SimpleToken:
    """A simple token."""

    def __init__(self, regex: Union[str, bytes]):
        """Initialize.

        :param regex: Regular expression to match token to
        """
        if not isinstance(regex, (str, bytes)):
            raise TypeError("must be string")
        self._regex = regex

    @property
    def regex(self):
        """Get regex."""
        return self._regex


class SimpleTokenField(SimpleToken):
    """A field token."""

    def __init__(
        self, field_name: Union[str, bytes], regex: Union[str, bytes]
    ):
        """Initialize.

        :param field_name: Field name associated to token
        :param regex: Regular expression to match token to
        """
        super().__init__(regex)
        self._name = field_name

    @property
    def name(self):
        """Get field name."""
        return self._name

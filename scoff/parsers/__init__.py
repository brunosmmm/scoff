"""Parse abstract syntax trees."""


class ScoffASTObject:
    """Scoff abstract syntax tree object."""

    SCOFF_META = {}

    def __init__(self, **kwargs):
        """Initialize."""
        if "SCOFF_META" in kwargs:
            self.SCOFF_META = kwargs.pop("SCOFF_META")
        for name, value in kwargs.items():
            setattr(self, name, value)

"""Parse abstract syntax trees."""


class ScoffASTObject:
    """Scoff abstract syntax tree object."""

    SCOFF_META = {}

    def __init__(self, **kwargs):
        """Initialize."""
        self.__visitable_children = {}
        self.__not_visitable_children = {}
        for name, value in kwargs.items():
            # ignore special names
            if not name.startswith("_") and name != "parent":
                self.__visitable_children[name] = value
            else:
                self.__not_visitable_children[name] = value
            setattr(self, name, value)

        self.__visitable_children_names = list(self.__visitable_children.keys())

    @property
    def visitable_children(self):
        """Get visitable children."""
        return self.__visitable_children

    def __dir__(self):
        """Get dir."""
        return self.__visitable_children_names

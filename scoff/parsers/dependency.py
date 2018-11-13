"""Parse dependencies in designs."""

from scoff.parsers.includes import (IncludeManagerMixin,
                                    IncludeAlreadyVisitedError)


class DependencyFinderError(Exception):
    """Dependency finder error."""

    pass


class DependencyFinder(IncludeManagerMixin):
    """Find dependencies."""

    _DEPENDENCY_REGEX = None

    def __init__(self, file_path, include_paths=None):
        """Initialize."""
        super().__init__()
        self._main = file_path
        if include_paths is None:
            include_paths = []
        self._include_paths = include_paths
        self._depends_on = set()

    def find_dependencies(self, depth=-1):
        """Find and build dependency map."""
        try:
            ret = self._find_dependencies(self._main, depth)
            return(ret)
        except Exception as ex:
            raise

    def _find_dependencies(self, filepath, depth=-1):
        with open(filepath, 'r') as f:
            main_txt = f.readlines()

        # simple regex parser
        for line in main_txt:
            m = self._DEPENDENCY_REGEX.match(line)
            if m is not None:
                # a dependency has been found
                try:
                    file_location = self._find_include_file(m.group(1))
                    self._depends_on |= set([file_location])
                    if depth != 0:
                        if depth > 0:
                            depth -= 1
                        self._find_dependencies(file_location, depth)
                except IncludeAlreadyVisitedError:
                    pass
                except Exception as ex:
                    raise DependencyFinderError('failed to inspect')

        return self._depends_on

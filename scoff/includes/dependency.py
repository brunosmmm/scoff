"""Parse dependencies in designs."""

from typing import Optional, List, Set
from scoff.includes import (
    IncludeManagerMixin,
    IncludeAlreadyVisitedError,
)


class DependencyFinderError(Exception):
    """Dependency finder error."""

    pass


class DependencyFinder(IncludeManagerMixin):
    """Find dependencies."""

    _DEPENDENCY_REGEX = None

    def __init__(
        self, file_path: str, include_paths: Optional[List[str]] = None
    ):
        """Initialize.

        :param file_path: Path to file
        :param include_paths: Optional include paths to search
        """
        super().__init__()
        self._main = file_path
        if include_paths is None:
            include_paths = []
        self._include_paths = include_paths
        self._depends_on = set()

    def find_dependencies(self, depth: int = -1) -> Set[str]:
        """Find and build dependency map.

        :param depth: Maximum depth to search dependencies
        :return: List of files which are dependencies
        """
        ret = self._find_dependencies(self._main, depth)
        return ret

    def _find_dependencies(self, filepath: str, depth: int = -1) -> Set[str]:
        """Actually find the dependencies."""
        with open(filepath, "r") as f:
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
                    # ignore file
                    pass
                except OSError as ex:
                    raise DependencyFinderError(f"failed to inspect: {ex}")

        return self._depends_on

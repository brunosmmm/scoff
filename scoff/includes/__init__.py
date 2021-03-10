"""Manage modularity through included files."""

import os.path
import hashlib


class IncludeAlreadyVisitedError(Exception):
    """Include already visited error."""


class IncludeManagerMixin:
    """Include manager mixin."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self._include_paths = [""]
        self._visited_includes = []

    @staticmethod
    def md5_hash(filename: str) -> str:
        """Calculate MD5 hash of file.

        :param filename: A path to a file
        :return: MD5sum of file
        """
        md5 = hashlib.md5()
        with open(filename, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def _find_include_file(self, filename: str) -> str:
        # try to find file and run check on it
        file_location = None
        for location in self._include_paths:
            file_path = os.path.join(".", location, filename)
            if os.path.exists(file_path):
                file_location = file_path
                break

        if file_location is None:
            raise OSError("cannot find file")

        # load and visit this file
        try:
            file_md5 = self.md5_hash(file_location)
        except OSError:
            # could not open file
            raise
        if file_md5 in self._visited_includes:
            # ignore
            raise IncludeAlreadyVisitedError("file already included/imported")

        # prevent double inclusion
        self._visited_includes.append(file_md5)
        return file_location

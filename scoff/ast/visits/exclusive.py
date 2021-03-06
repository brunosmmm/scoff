"""Exclusive visit."""

import re
from typing import Any
from scoff.ast import ScoffASTObject
from scoff.ast.visits import ASTVisitor, VisitError


class ExclusiveASTVisitor(ASTVisitor):
    """Exclusive visits.

    Visits only children which names match certain patterns.
    """

    def __init__(self, *disallowed: str, **options: Any):
        """Initialize.

        :param disallowed: List of disallowed prefix patterns, which will not \
        be visited
        :param options: Visitor options (flags)
        """
        super().__init__(**options)
        # allowed, disallowed prefixes
        self._not_allowed = set()
        self._allowed_visits = set()
        self.add_disallowed_prefixes(*disallowed)
        # exclusive visits
        self.__allowed_matches = []
        self.__not_allowed_matches = []
        if self.get_flag_state("exclusive_visit"):
            self.set_flag("minimal_depth")
            self._allowed_visits = {
                "^{}$".format(name[6:]) for name in self._visit_method_names
            }

    def visit(self, node: ScoffASTObject):
        """Begin visit.

        :param node: Node to start visiting at
        """
        # pre-compile regular expressions
        self.__not_allowed_matches = [
            re.compile(disallowed) for disallowed in self._not_allowed
        ]
        self.__allowed_matches = [
            re.compile(allowed) for allowed in self._allowed_visits
        ]
        return super().visit(node)

    def add_disallowed_prefixes(self, *prefixes: str):
        """Disallow visiting of attributes with a prefix.

        :param prefixes: Disallowed prefix patterns
        """
        if self._visiting is True:
            raise VisitError("cannot alter disallowed prefixes while visiting")
        self._not_allowed |= set(prefixes)

    def add_allowed_prefixes(self, *prefixes: str):
        """Add allowed prefixes.

        :param prefixes: Allowed prefix patterns
        """
        if self._visiting is True:
            raise VisitError("cannot alter allowed prefixes while visiting")
        self._allowed_visits |= set(prefixes)

    def _check_visit_allowed(self, name: str) -> bool:
        if self.get_flag_state("exclusive_visit"):
            for allowed in self.__allowed_matches:
                if allowed.match(name) is not None:
                    return True
            return False
        # else
        for disallowed in self.__not_allowed_matches:
            if disallowed.match(name) is not None:
                return False

        return True

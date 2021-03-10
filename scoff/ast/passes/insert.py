"""Node inserter."""

from scoff.ast import ScoffASTObject
from scoff.ast.visits import ASTVisitor


class NodeInserter(ASTVisitor):
    """Node inserter."""

    def __init__(self, ast: ScoffASTObject):
        """Initialize.

        :param ast: The AST to insert nodes into
        """
        super().__init__()
        self._ast = ast
        self._insert_after = True
        self._matching_node = None
        self._insert_contents = None
        self._inserting = False

    def _visit_and_modify(self, node, attr=None):
        if self._inserting is False:
            return node

        # only mess with scopes for now
        if attr is not None:
            return node

        if node != self._matching_node:
            return node

        if isinstance(self._insert_contents, (tuple, list)):
            if self._insert_after:
                ret = [node].extend(self._insert_contents)
                return ret
            else:
                self._insert_contents.extend([node])
                return self._insert_contents
        else:
            if self._insert_after:
                return [node, self._insert_contents]
            else:
                return [self._insert_contents, node]

    def insert(
        self, what: ScoffASTObject, where: ScoffASTObject, after: bool = True
    ):
        """Insert a node.

        :param what: What to insert
        :param where: Where to insert
        :after: Whether to insert after or before *WHERE*
        """
        self._inserting = True
        self._insert_after = after
        self._insert_contents = what
        self._matching_node = where
        self.visit(self._ast)
        self._inserting = False

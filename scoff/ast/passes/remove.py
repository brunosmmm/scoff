"""Node remover."""

from typing import Callable, Tuple
from scoff.ast.visits import ASTVisitor, VisitOptionType


class NodeRemover(ASTVisitor):
    """Node remover.

    Removes all nodes in AST which match certain class names.
    """

    def __init__(self, *node_types: Tuple[str], **flags: VisitOptionType):
        """Initialize.

        :param node_types: Class names for node types to remove
        :param flags: Any other visitor flags
        """
        for node_type in node_types:
            setattr(self, "visit_{}".format(node_type), self._delete_node)
        super().__init__(**flags)

    def _delete_node(self, node):
        self._debug_visit("removing node {}".format(node))
        return None


class ConditionalNodeRemover(NodeRemover):
    """Remove nodes but only under certain conditions."""

    def __init__(
        self,
        *node_types: Tuple[str],
        decide_fn: Callable,
        **flags: VisitOptionType
    ):
        """Initialize.

        :param node_type: Class name of node type to remove
        :param decide_fn: A callable which is called to decide on removal
        :param flags: Any other visitor flags
        """
        super().__init__(*node_types, **flags)
        self._decide_cb = decide_fn

    def _delete_node(self, node):
        if self._decide_cb(node):
            return super()._delete_node(node)

        return node

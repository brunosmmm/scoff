"""Node remover."""

from scoff.ast.visits import ASTVisitor


class NodeRemover(ASTVisitor):
    """Node remover."""

    def __init__(self, *node_types, **flags):
        """Initialize."""
        for node_type in node_types:
            setattr(self, "visit_{}".format(node_type), self._delete_node)
        super().__init__(**flags)

    def _delete_node(self, node):
        self._debug_visit("removing node {}".format(node))
        return None


class ConditionalNodeRemover(NodeRemover):
    """Remove only on certain conditions."""

    def __init__(self, node_type, decide_fn, **flags):
        """Initialize."""
        super().__init__(node_type, **flags)
        self._decide_cb = decide_fn

    def _delete_node(self, node):
        if self._decide_cb(node):
            return super()._delete_node(node)

        return node

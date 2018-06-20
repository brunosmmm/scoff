"""Node remover."""

from ..parsers.tree import ASTVisitor


class NodeRemover(ASTVisitor):
    """Node remover."""

    def __init__(self, *node_types, **flags):
        """Initialize."""
        super().__init__('_.*', 'parent$', **flags)
        self._node_types = node_types

    def _visit_and_modify(self, node, attr=None):
        if node.__class__.__name__ in self._node_types:
            if attr is not None:
                self._debug_visit('removing node attribute: {}'.format(attr))
                setattr(node, attr, None)
            else:
                self._debug_visit('removing node {}'.format(node))
                return None
        return node


class ConditionalNodeRemover(NodeRemover):
    """Remove only on certain conditions."""

    def __init__(self, node_type, decide_fn, **flags):
        """Initialize."""
        super().__init__(node_type, **flags)
        self._decide_cb = decide_fn

    def _visit_and_modify(self, node, attr=None):
        if self.is_of_type(node, self._node_types[0]):
            if attr is not None:
                if self._decide_cb(node):
                    self._debug_visit('removing node attribute: {}'
                                      .format(attr))
                    setattr(node, attr, None)
            else:
                if self._decide_cb(node):
                    self._debug_visit('removing node: {}'.format(node))
                    return None

        return node

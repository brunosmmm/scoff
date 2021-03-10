"""Visit control through decorators."""


class SetFlag:
    """Set flag on visit.

    Will set a flag on the current visitor before visiting.
    """

    def __init__(self, flag_name: str):
        """Initialize.

        :param flag_name: Flag name
        """
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            tree.set_flag(self._flag)
            return fn(tree, node)

        return wrapper


class SetFlagAfter:
    """Set flag on visit.

    Will set a flag on the current visitor after visiting.
    """

    def __init__(self, flag_name: str):
        """Initialize.

        :param flag_name: Flag name
        """
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            ret = fn(tree, node)
            tree.set_flag(self._flag)
            return ret

        return wrapper


class ClearFlag:
    """Clear flag on visit.

    Flag will be cleared on the visitor before visiting the node.
    """

    def __init__(self, flag_name: str):
        """Initialize.

        :param flag_name: Flag name
        """
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            tree.clear_flag(self._flag)
            return fn(tree, node)

        return wrapper


class ClearFlagAfter:
    """Clear flag on visit.

    Flag will be cleared on the visitor after visiting the node.
    """

    def __init__(self, flag_name: str):
        """Initialize.

        :param flag_name: Flag name
        """
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            ret = fn(tree, node)
            tree.clear_flag(self._flag)
            return ret

        return wrapper


class ConditionalVisit:
    """Conditional visit.

    Only starts visiting the node if some condition is met, otherwise skips.
    """

    def __init__(self, flag_name: str, inverted: bool = False):
        """Initialize.

        :param flag_name: Flag name to check
        :param inverted: Whether to invert the boolean value of the condition
        """
        self._flag = flag_name
        self._inverted = inverted

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            if self._inverted is True:
                if tree.get_flag_state(self._flag) is False:
                    return fn(tree, node)
                else:
                    return node
            elif tree.get_flag_state(self._flag) is True:
                return fn(tree, node)
            else:
                return node

        return wrapper


def trace_visit(fn):
    """Trace visit.

    Prints tracing information when visiting a node.
    """

    def wrapper(tree, *args):
        tree._debug_visit(
            "entering {}, args are: {}".format(fn.__name__, args)
        )
        ret = fn(tree, *args)
        tree._debug_visit("exiting {}, returned: {}".format(fn.__name__, ret))
        return ret

    return wrapper


def stop_visiting(fn):
    """Disable further visits.

    Disable all visits after done visiting the current node.
    """

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("stop_visit")
        return ret

    return wrapper


def no_child_visits(fn):
    """Disable children visits.

    Disable visiting of the current children nodes.
    """

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("no_children_visits")
        return ret

    return wrapper


def reverse_visit_order(fn):
    """Reverse visit order.

    Visits are performed on node's children on an ordered fashion (order is \
    set during AST object creation). Visit this node's children in reverse \
    order
    """

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("reverse_visit")
        return ret

    return wrapper

"""Visit control through decorators."""


class SetFlag:
    """Set flag on visit."""

    def __init__(self, flag_name):
        """Initialize."""
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            tree.set_flag(self._flag)
            return fn(tree, node)

        return wrapper


class SetFlagAfter:
    """Set flag on visit."""

    def __init__(self, flag_name):
        """Initialize."""
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            ret = fn(tree, node)
            tree.set_flag(self._flag)
            return ret

        return wrapper


class ClearFlag:
    """Clear flag on visit."""

    def __init__(self, flag_name):
        """Initialize."""
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            tree.clear_flag(self._flag)
            return fn(tree, node)

        return wrapper


class ClearFlagAfter:
    """Clear flag on visit."""

    def __init__(self, flag_name):
        """Initialize."""
        self._flag = flag_name

    def __call__(self, fn):
        """Call."""

        def wrapper(tree, node):
            ret = fn(tree, node)
            tree.clear_flag(self._flag)
            return ret

        return wrapper


class ConditionalVisit:
    """Conditional visit."""

    def __init__(self, flag_name, inverted=False):
        """Initialize."""
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
    """Trace visit."""

    def wrapper(tree, *args):
        tree._debug_visit(
            "entering {}, args are: {}".format(fn.__name__, args)
        )
        ret = fn(tree, *args)
        tree._debug_visit("exiting {}, returned: {}".format(fn.__name__, ret))
        return ret

    return wrapper


def stop_visiting(fn):
    """No further visits."""

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("stop_visit")
        return ret

    return wrapper


def no_child_visits(fn):
    """No children visits."""

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("no_children_visits")
        return ret

    return wrapper


def reverse_visit_order(fn):
    """Reverse visit order."""

    def wrapper(tree, *args):
        ret = fn(tree, *args)
        tree.set_flag("reverse_visit")
        return ret

    return wrapper

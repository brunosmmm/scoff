"""General Parser utilities."""

import re
from collections import namedtuple, deque
from scoff.parsers import ScoffASTObject
from scoff.parsers.visits import ScoffVisitObject

# Visit history object
VisitHistory = namedtuple("VisitHistory", ["node", "replaces", "depth"])


class VisitError(Exception):
    """Exception while visiting."""

    def __init__(self, original_exception=None):
        """Initialize."""
        super().__init__()
        self.ex = original_exception

    def find_embedded_exception(self):
        """Find an exception that is not VisitError."""
        # there might be several VisitErrors inside each other
        if isinstance(self.ex, VisitError):
            return self.ex.find_embedded_exception()
        if self.ex is None:
            return RuntimeError("unknown error in visit")
        return self.ex


class NoChildrenVisits(Exception):
    """Controlled error to escape event sequence."""


class ASTVisitor:
    """Visits an AST."""

    def __init__(self, **options):
        """Initialize."""
        super().__init__()
        self._visiting = False
        self._dont_visit = False
        self._visit_depth = 0
        self._visit_history = deque()
        self._flags = {"exclusive_visit": False, "minimal_depth": False}
        self._options = {"logger_fn": None, "history_len": 0}
        self._hooks = {}
        self.reset_visits()
        self.clear_flag("debug_visit")
        self._visited_nodes = set()

        # flags
        self.clear_flag("no_children_visits")
        for opt_name, opt_value in options.items():
            if isinstance(opt_value, bool):
                # save as flag
                if opt_value is True:
                    self.set_flag(opt_name)
                else:
                    self.clear_flag(opt_name)
            else:
                # save as option
                self.set_option(opt_name, opt_value)

        # pre-allocate visit function table
        self._method_names = [
            name for name in dir(self) if callable(getattr(self, name))
        ]

        # visit function table
        self.__visit_fn_table = {}
        self.__visit_pre_fn_table = {}

    def _debug_visit(self, message):
        """Print debug messages when visiting."""
        if self.get_flag_state("debug_visit"):
            logger_fn = self.get_option("logger_fn")
            if logger_fn is not None:
                # call logger function
                logger_fn(message)
            else:
                # print to stdout
                print(message)

    def reset_visits(self):
        """Reset visit record."""
        self._visited_nodes = set()

    def add_visit_hook(self, node_cls_name, method):
        """Add external hook to call when a certain class is visited."""
        if node_cls_name not in self._hooks:
            self._hooks[node_cls_name] = set()

        self._hooks[node_cls_name] |= set([method])

    def pause_visiting(self):
        """Stop visiting temporarily."""
        self._dont_visit = True

    def resume_visiting(self):
        """Resume visiting."""
        self._dont_visit = False

    def dont_visit_children(self):
        """Don't visit children of this node."""
        self.set_flag("no_children_visits")

    def has_been_visited(self, node):
        """Check if a node has been visited before."""
        return node in self._visited_nodes

    def get_last_visited(self):
        """Get last visited node."""
        last_visit = self._visit_history.popleft()
        self._visit_history.append(last_visit)
        return last_visit

    def get_visit_history(self):
        """Get visit history."""
        return self._visit_history

    def set_flag(self, flag_name):
        """Set flag."""
        self._flags[flag_name] = True

    def clear_flag(self, flag_name):
        """Clear flag."""
        self._flags[flag_name] = False

    def set_option(self, option_name, option_value):
        """Set option."""
        self._options[option_name] = option_value

    def get_option(self, option_name):
        """Get option."""
        return self._options[option_name]

    def get_flag_state(self, flag_name):
        """Get flag state."""
        if flag_name not in self._flags:
            return False

        return self._flags[flag_name]

    @staticmethod
    def is_of_type(node, type_name):
        """Check class name."""
        return node.__class__.__name__ == type_name

    def get_first_occurrence(self, node, node_type, inclusive=True):
        """Return first occurrence of type."""
        if self.is_of_type(node, node_type):
            if inclusive:
                return node

        if isinstance(node, ScoffASTObject):
            node_dict = node.visitable_children_names
        else:
            node_dict = [
                name
                for name in node.__dict__
                if not name.startswith("_") and name != "parent"
            ]
        for attr_name in node_dict:
            attr = getattr(node, attr_name)
            if self._check_visit_allowed(attr_name):
                if self.is_of_type(attr, node_type):
                    return attr
                if isinstance(attr, list):
                    for obj in attr:
                        ret = self.get_first_occurrence(obj, node_type)
                        if ret is not None:
                            return ret
                elif isinstance(attr, str):
                    return None
                else:
                    self.get_first_occurrence(attr, node_type)
            del attr

        return None

    def get_all_occurrences(self, root, node_type):
        """Find all nodes of a type."""
        if isinstance(root, ScoffASTObject):
            node_dict = root.visitable_children_names
        else:
            node_dict = [
                name
                for name in root.__dict__
                if not name.startswith("_") and name != "parent"
            ]
        occurrences = []
        for attr_name in node_dict:
            attr = getattr(root, attr_name)
            if self.is_of_type(attr, node_type):
                occurrences.append(attr)
            elif isinstance(attr, (list, tuple)):
                for obj in attr:
                    occurrences.extend(self.get_all_occurrences(obj, node_type))
            elif isinstance(attr, str):
                return []
            else:
                occurrences.extend(self.get_all_occurrences(attr, node_type))
            del attr

        return occurrences

    def _cleanup_visit(self):
        """Cleanup temporary storage after visit."""
        for member_name in dir(self):
            if isinstance(getattr(self, member_name), ScoffVisitObject):
                member_class = self.__dict__[member_name].__class__
                self.__dict__[member_name] = member_class()
        # remove visitation list
        self._visited_nodes = set()

    def _store_visit(self, visit_history):
        """Store visit."""
        history_len = self.get_option("history_len")
        if history_len == 0:
            return
        if len(self._visit_history) == history_len:
            self._visit_history.popleft()
        self._visit_history.append(visit_history)

    def _call_visit_hooks(self, cls_name, node):
        """Call registered hooks."""
        if cls_name not in self._hooks:
            return
        for hook in self._hooks[cls_name]:
            hook(node)

    def _visit_fn_post(self, cls_name, node):
        """Call corresponding function if present."""
        if cls_name not in self.__visit_fn_table:
            ret = self._visit_default(node)
            self._call_visit_hooks(cls_name, node)
            return ret

        fn = self.__visit_fn_table[cls_name]

        # check if visited before
        if self.get_flag_state("ignore_visited"):
            if self.has_been_visited(node):
                return node
            else:
                self._visited_nodes |= set([node])

        ret = fn(node)
        self._call_visit_hooks(cls_name, node)
        return ret

    def _visit_fn_pre(self, cls_name, node):
        if cls_name not in self.__visit_pre_fn_table:
            return self._visit_pre_default(node)

        fn = self.__visit_pre_fn_table[cls_name]

        # check if visited before
        if self.get_flag_state("ignore_visited"):
            if self.has_been_visited(node):
                return node

        # do not visit children if we are visiting this node
        # but have the minimal depth flag
        if self.get_flag_state("minimal_depth"):
            if cls_name in self.__visit_fn_table:
                self.set_flag("no_children_visits")

        return fn(node)

    def visit(self, node, cleanup=True):
        """Start visting at a certain node."""

        def strip_name(name, prefix):
            return name[len(prefix) :] if name.startswith(prefix) else name

        # pre-allocate visit function table
        self.__visit_fn_table = {
            strip_name(name, "visit_"): getattr(self, name)
            for name in self._method_names
            if name.startswith("visit_")
        }
        self.__visit_pre_fn_table = {
            strip_name(name, "visitPre_"): getattr(self, name)
            for name in self._method_names
            if name.startswith("visitPre_")
        }

        self._visiting = True
        ret = self._visit(node)
        self._visiting = False
        if cleanup:
            self._cleanup_visit()
        return ret

    def _visit_default(self, node):
        if "Default" not in self.__visit_fn_table:
            return node

        fn = self.__visit_fn_table["Default"]

        return fn(node)

    def _visit_pre_default(self, node):
        if "Default" not in self.__visit_pre_fn_table:
            return None

        fn = self.__visit_pre_fn_table["Default"]

        return fn(node)

    @staticmethod
    def _check_visit_allowed(*args):
        return True

    def _visit_and_modify(self, node, attr=None):
        if attr is None:
            to_visit = node
        else:
            to_visit = getattr(node, attr)
        ret = self._visit(to_visit)
        if ret != to_visit:
            del to_visit
            if ret is not None:
                if attr is not None:
                    setattr(node, attr, ret)
                    return True
                # swapping out entire statements, not attributes
                return ret
            # deleted
            if attr is not None:
                setattr(node, attr, None)

            return None
        # not modified
        return False

    def _visit(self, node):
        """Start visting at a certain node."""
        self._visit_depth += 1
        # call before visiting, cannot modify things
        try:
            if self._dont_visit is False:
                self._visit_fn_pre(node.__class__.__name__, node)
        except Exception as ex:
            self._debug_visit(
                'exception caught while visiting: "{}"'.format(ex)
            )
            raise VisitError(ex)
        try:
            # debug = False
            if self.get_flag_state("no_children_visits"):
                # reset
                self.clear_flag("no_children_visits")
                # get out
                raise NoChildrenVisits()

            visit_list = None
            if not isinstance(node, ScoffASTObject):
                visit_list = [
                    item
                    for item in node.__dict__
                    if not item.startswith("_") and item != "parent"
                ]
            else:
                # NOTE do not use dir as it sorts alphabetically
                visit_list = node.visitable_children_names

            if self.get_flag_state("reverse_visit"):
                visit_list = visit_list[::-1]
                self.clear_flag("reverse_visit")

            for attr_name in visit_list:
                if self._check_visit_allowed(attr_name) is False:
                    continue

                attr_value = getattr(node, attr_name)
                if not isinstance(attr_value, (tuple, list)):
                    self._visit_and_modify(node, attr_name)
                else:

                    modified_statements = {}
                    to_delete = []
                    for idx, statement in enumerate(attr_value):
                        result = self._visit_and_modify(statement)

                        if result is None:
                            to_delete.append(idx)
                        elif not isinstance(result, bool):
                            # returned something else, save
                            modified_statements[idx] = result
                        elif result:
                            attr_value[idx] = result
                            # unflag as ignored due to modification
                            self._visited_nodes.remove(statement)
                        # process returned data
                    insertion_offset = 0
                    attr_list = []
                    for idx, result in modified_statements.items():
                        if not isinstance(result, (tuple, list)):
                            to_insert = [result]
                        else:
                            to_insert = result

                        for _value in to_insert:
                            if isinstance(_value, ScoffASTObject):
                                _value.parent = node
                                _value._parent_key = attr_name

                        before = attr_value[: idx + insertion_offset]
                        after = attr_value[idx + insertion_offset + 1 :]
                        before.extend(to_insert)
                        before.extend(after)
                        insertion_offset += len(to_insert) - 1
                        attr_value = before

                    deletion_offset = 0
                    for idx in to_delete:
                        try:
                            # NOTE do not assign list element to variable as it
                            # creates one more reference
                            if isinstance(
                                attr_value[idx + deletion_offset],
                                ScoffASTObject,
                            ):
                                attr_value[idx + deletion_offset].parent = None
                            del attr_value[idx + deletion_offset]
                            deletion_offset -= 1
                        except Exception:
                            # couldn't delete!
                            print("failed")
                            pass
                    # modify
                    setattr(node, attr_name, attr_value)

        except (AttributeError, NoChildrenVisits):
            # built-in types
            pass
        # if debug:
        #    exit(0)
        try:
            if self._dont_visit is False:
                ret = self._visit_fn_post(node.__class__.__name__, node)
            else:
                self._visit_depth -= 1
                return node
        except Exception as ex:
            raise VisitError(ex)
        # store as last visited node
        if node == ret:
            replaces = None
        else:
            replaces = node
        history_len = self.get_option("history_len")
        if history_len > 0:
            self._store_visit(VisitHistory(ret, replaces, self._visit_depth))
        self._visit_depth -= 1
        return ret

    def find_parent_by_type(self, node, parent_type, level=1):
        """Find nth hierarchical ocurrence of type, upwards."""
        if not hasattr(node, "parent"):
            return None
        if node.parent is not None:
            if node.parent.__class__.__name__ == parent_type:
                if level > 1:
                    return self.find_parent_by_type(
                        node.parent, parent_type, level - 1
                    )
                return node.parent
            return self.find_parent_by_type(node.parent, parent_type, level)
        return None


class ExclusiveASTVisitor(ASTVisitor):
    """Exclusive visits."""

    def __init__(self, *disallowed, **options):
        """Initialize."""
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
                "^{}$".format(name[6:])
                for name in self._method_names
                if name.startswith("visit_")
            }

    def visit(self, node):
        """Begin visit."""
        # pre-compile regular expressions
        self.__not_allowed_matches = [
            re.compile(disallowed) for disallowed in self._not_allowed
        ]
        self.__allowed_matches = [
            re.compile(allowed) for allowed in self._allowed_visits
        ]
        return super().visit(node)

    def add_disallowed_prefixes(self, *prefixes):
        """Disallow visiting of attributes with a prefix."""
        if self._visiting is True:
            raise VisitError("cannot alter disallowed prefixes while visiting")
        self._not_allowed |= set(prefixes)

    def add_allowed_prefixes(self, *prefixes):
        """Add allowed prefixes."""
        if self._visiting is True:
            raise VisitError("cannot alter allowed prefixes while visiting")
        self._allowed_visits |= set(prefixes)

    def _check_visit_allowed(self, name):
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
        tree._debug_visit("entering {}, args are: {}".format(fn.__name__, args))
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

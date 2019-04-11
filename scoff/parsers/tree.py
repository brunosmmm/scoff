"""General Parser utilities."""

import textwrap
import re
import sys
import os
from collections import namedtuple, deque
from . import ScoffASTObject

# Visit history object
VisitHistory = namedtuple("VisitHistory", ["node", "replaces", "depth"])


class VisitError(Exception):
    """Exception while visiting."""

    def __init__(self, original_exception, ex_info=None):
        """Initialize."""
        self.ex = original_exception
        if ex_info is not None:
            ex_fname = os.path.split(ex_info.tb_frame.f_code.co_filename)[1]
            self.ex_fname = ex_fname
            self.ex_lineno = ex_info.tb_lineno
        else:
            self.ex_fname = None
            self.ex_lineno = None

    def find_embedded_exception(self):
        """Find an exception that is not VisitError."""
        # there might be several VisitErrors inside each other
        if isinstance(self.ex, VisitError):
            return self.ex.find_embedded_exception()
        return self.ex


class NoChildrenVisits(Exception):
    """Controlled error to escape event sequence."""


def make_ast_class(class_name, subclass_of, **members):
    """Make class on the fly."""
    _global = {}
    _local = {}
    # comply with textX stuff being used
    members.update({"_tx_position": None})
    if subclass_of is None:
        class_decl = "class {}:\n".format(class_name)
    else:
        class_decl = "class {}({}):\n".format(class_name, subclass_of.__name__)
        _global = {subclass_of.__name__: subclass_of}
    member_decl = "\n".join(
        ["{} = {}".format(name, value) for name, value in members.items()]
    )

    exec(class_decl + textwrap.indent(member_decl, "    "), _global, _local)

    return _local[class_name]


def make_ast_object(cls, subclass_of, *init_args, **members):
    """Make object."""

    def fake_class_obj(cls_name):
        cls = make_ast_class(cls_name, subclass_of, _dummy_ast=True)
        obj = cls(*init_args)
        for name, value in members.items():
            setattr(obj, name, value)

        return obj

    if isinstance(cls, str):
        obj = fake_class_obj(cls)
    elif isinstance(cls, type):
        if not issubclass(cls, ScoffASTObject):
            obj = fake_class_obj(cls.__name__)
        else:
            if "parent" not in members:
                members["parent"] = None
            obj = cls(**members)

    return obj


def make_ast(tree_dict, parent_name=None, depth=0):
    """Make an ast from scratch."""
    if len(tree_dict) != 1 and depth == 0:
        # error
        raise RuntimeError("only one root node allowed")

    if depth == 0:
        root_name, tree_dict = next(iter(tree_dict.items()))

    children = {}
    for node_name, node_child in tree_dict.items():
        if isinstance(node_child, dict):
            # a class
            sub_tree = make_ast(node_child, node_name, depth + 1)
            children[node_name] = sub_tree
        elif isinstance(node_child, list):
            # several children
            child_list = []
            for child in node_child:
                sub_tree = make_ast(child, node_name, depth + 1)
                child_list.append(sub_tree)
            if len(child_list) == 1:
                child_list = child_list[0]
            children[node_name] = child_list
        else:
            # leaf node
            children[node_name] = node_child
    if depth > 0:
        cls_name = parent_name
    else:
        cls_name = root_name

    if depth % 2:
        ret = [child for child in children.values()]
        if len(ret) == 1:
            ret, = ret
    else:
        ret = make_ast_object(cls_name, None, **children)

    return ret


class ASTVisitor:
    """Visits an AST."""

    def __init__(self, *disallowed, **options):
        """Initialize."""
        super().__init__()
        self._not_allowed = set()
        self._allowed_visits = set()
        self.__visiting = False
        self.add_disallowed_prefixes(*disallowed)
        self._dont_visit = False
        self._visit_depth = 0
        self._visit_history = deque()
        self._flags = {"exclusive_visit": False, "minimal_depth": False}
        self._options = {"logger_fn": None, "history_len": 0}
        self._hooks = {}
        self.reset_visits()
        self.clear_flag("debug_visit")

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
        methods = [name for name in dir(self) if callable(getattr(self, name))]

        # visit function table
        self.__visit_fn_table = {}
        self.__visit_fn_pre_table = {}

        # exclusive visits
        self.__allowed_matches = []
        self.__not_allowed_matches = []
        if self.get_flag_state("exclusive_visit"):
            self.set_flag("minimal_depth")
            self._allowed_visits = set(
                [
                    "^{}$".format(name.lstrip("visit_"))
                    for name in methods
                    if name.startswith("visit_")
                ]
            )

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

    def add_disallowed_prefixes(self, *prefixes):
        """Disallow visiting of attributes with a prefix."""
        if self.__visiting is True:
            raise VisitError("cannot alter disallowed prefixes while visiting")
        self._not_allowed |= set(prefixes)

    def add_allowed_prefixes(self, *prefixes):
        """Add allowed prefixes."""
        if self.__visiting is True:
            raise VisitError("cannot alter allowed prefixes while visiting")
        self._allowed_visits |= set(prefixes)

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

        node_dict = node.__dict__
        for attr_name, attr in node_dict.items():
            if self._check_visit_allowed(attr_name):
                if self.is_of_type(attr, node_type):
                    return attr
                elif isinstance(attr, list):
                    for obj in attr:
                        ret = self.get_first_occurrence(obj, node_type)
                        if ret is not None:
                            return ret
                elif isinstance(attr, str):
                    return None
                else:
                    self.get_first_occurrence(attr, node_type)

        return None

    def get_all_occurrences(self, root, node_type):
        """Find all nodes of a type."""
        node_dict = root.__dict__
        occurrences = []
        for attr_name, attr in node_dict.items():
            if self._check_visit_allowed(attr_name):
                if self.is_of_type(attr, node_type):
                    occurrences.append(attr)
                elif isinstance(attr, (list, tuple)):
                    for obj in attr:
                        occurrences.extend(
                            self.get_all_occurrences(obj, node_type)
                        )
                elif isinstance(attr, str):
                    return []
                else:
                    occurrences.extend(
                        self.get_all_occurrences(attr, node_type)
                    )

        return occurrences

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
        if self.has_been_visited(node):
            if self.get_flag_state("ignore_visited"):
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
        if self.has_been_visited(node):
            if self.get_flag_state("ignore_visited"):
                return node

        # do not visit children if we are visiting this node
        # but have the minimal depth flag
        if self.get_flag_state("minimal_depth"):
            if cls_name in self.__visit_fn_table:
                self.set_flag("no_children_visits")

        return fn(node)

    def visit(self, node):
        """Start visting at a certain node."""

        def strip_name(name, prefix):
            return name[len(prefix) :] if name.startswith(prefix) else name

        # pre-allocate visit function table
        methods = [name for name in dir(self) if callable(getattr(self, name))]

        # visit function table
        self.__visit_fn_table = {
            strip_name(name, "visit_"): getattr(self, name)
            for name in methods
            if name.startswith("visit_")
        }
        self.__visit_pre_fn_table = {
            strip_name(name, "visitPre_"): getattr(self, name)
            for name in methods
            if name.startswith("visitPre_")
        }

        # pre-compile regular expressions
        self.__not_allowed_matches = [
            re.compile(disallowed) for disallowed in self._not_allowed
        ]
        self.__allowed_matches = [
            re.compile(allowed) for allowed in self._allowed_visits
        ]
        self.__visiting = True
        ret = self._visit(node)
        self.__visiting = False
        return ret

    def _visit_default(self, node):
        if "Default" not in self.__visit_fn_table:
            return node

        fn = self.__visit_fn_table["Default"]

        return fn(node)

    def _visit_pre_default(self, node):
        if "Default" not in self.__visit_fn_pre_table:
            return None

        fn = self.__visit_fn_pre_table["Default"]

        return fn(node)

    def _check_visit_allowed(self, name):
        if self.get_flag_state("exclusive_visit"):
            for allowed in self.__allowed_matches:
                if allowed.match(name) is not None:
                    return True
            return False
        else:
            for disallowed in self.__not_allowed_matches:
                if disallowed.match(name) is not None:
                    return False

        return True

    def _visit_and_modify(self, node, attr=None):
        if attr is None:
            to_visit = node
        else:
            to_visit = getattr(node, attr)
        ret = self._visit(to_visit)
        if ret != to_visit:
            # print('original = {}; new = {}'
            #       .format(to_visit, ret))
            if ret is not None:
                if attr is not None:
                    setattr(node, attr, ret)
                    return True
                else:
                    # swapping out entire statements, not attributes
                    return ret
            else:
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
            ex_info = sys.exc_info()[-1]
            raise VisitError(ex, ex_info)
        try:
            # debug = False
            node_dict = node.__dict__
            if self.get_flag_state("no_children_visits"):
                # reset
                self.clear_flag("no_children_visits")
                # get out
                raise NoChildrenVisits()

            if self.get_flag_state("reverse_visit"):
                visit_list = list(node_dict)[::-1]
                self.clear_flag("reverse_visit")
            else:
                visit_list = list(node_dict)

            for attr_name in visit_list:
                if self._check_visit_allowed(attr_name) is False:
                    continue

                if not isinstance(node_dict[attr_name], (tuple, list)):
                    self._visit_and_modify(node, attr_name)
                else:
                    # debug = True
                    # print(attr)
                    modified_statements = {}
                    to_delete = []
                    for idx, statement in enumerate(node_dict[attr_name]):
                        result = self._visit_and_modify(statement)
                        if result is None:
                            # print('will delete: {}'.format(statement))
                            to_delete.append(idx)
                        elif not isinstance(result, bool):
                            # returned something else, save
                            modified_statements[idx] = result
                        elif result:
                            node_dict[attr_name][idx] = result
                            # unflag as ignored due to modification
                            self._visited_nodes.remove(statement)
                        # process returned data
                    insertion_offset = 0
                    for idx, result in modified_statements.items():
                        if isinstance(result, (tuple, list)):
                            # print("inserting results into {}"
                            #      .format(node))
                            # print(node_dict[attr_name])
                            before = node_dict[attr_name][
                                : idx + insertion_offset
                            ]
                            after = node_dict[attr_name][
                                idx + insertion_offset + 1 :
                            ]
                            before.extend(result)
                            before.extend(after)
                            insertion_offset += len(result) - 1
                            attr_list = before
                            setattr(node, attr_name, attr_list)
                        else:
                            node_dict[attr_name][
                                idx + insertion_offset
                            ] = result
                            # setattr(node, attr_name, attr)

                    deletion_offset = 0
                    for idx in to_delete:
                        try:
                            del node_dict[attr_name][idx + deletion_offset]
                            deletion_offset -= 1
                        except Exception:
                            # couldn't delete!
                            pass
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
            ex_info = sys.exc_info()[-1]
            raise VisitError(ex, ex_info)
        # store as last visited node
        if node == ret:
            replaces = None
        else:
            replaces = node
        self._store_visit(VisitHistory(ret, replaces, self._visit_depth))
        self._visit_depth -= 1
        return ret

    def is_child_of_type(self, node, type_name):
        """Detect if parent of type is available."""
        if not hasattr(node, "parent"):
            return False
        if node.parent is not None:
            if node.parent.__class__.__name__ == type_name:
                return True
            return self.is_child_of_type(node.parent, type_name)
        else:
            return False

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
                else:
                    return node.parent
            return self.find_parent_by_type(node.parent, parent_type, level)
        else:
            return None


class ASTCopy(ASTVisitor):
    """Makes a fake copy of the AST."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)

    def _visit(self, node):

        try:
            node_dict = node.__dict__
            empty_members = {
                member_name: None
                for member_name, value in node_dict.items()
                if self._check_visit_allowed(member_name)
            }
            if hasattr(node, "_tx_position"):
                original_start_loc = node._tx_position
            else:
                original_start_loc = None
            if hasattr(node, "_tx_position_end"):
                original_end_loc = node._tx_position_end
            else:
                original_end_loc = None
            empty_members.update(
                {
                    "SCOFF_META": {
                        "ast_copy": True,
                        "original_start_loc": original_start_loc,
                        "original_end_loc": original_end_loc,
                    }
                }
            )
            class_obj = make_ast_object(node.__class__, None, **empty_members)
            for member in node_dict:
                if self._check_visit_allowed(member) is False:
                    continue
                if isinstance(getattr(node, member), (list, tuple)):
                    ret = []
                    for instance in getattr(node, member):
                        visit_ret = self._visit(instance)
                        try:
                            visit_ret.parent = class_obj
                        except Exception:
                            pass
                        ret.append(visit_ret)
                    setattr(class_obj, member, ret)
                else:
                    ret = self._visit(getattr(node, member))
                    try:
                        ret.parent = class_obj
                    except Exception:
                        pass
                    setattr(class_obj, member, ret)
            return class_obj
        except AttributeError:
            if isinstance(node, str):
                return node[:]
            elif isinstance(node, bool):
                return node
            elif isinstance(node, dict):
                return node.copy()
            elif node is not None:
                self._debug_visit("unknown: {}".format(node))
                return node


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
        tree._debug_visit("exiting {}".format(fn.__name__))
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

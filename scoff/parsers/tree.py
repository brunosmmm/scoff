"""General Parser utilities."""

import textwrap


class VisitError(Exception):
    """Exception while visiting."""

    def __init__(self, original_exception):
        """Initialize."""
        self.ex = original_exception

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
    members.update({'_tx_position': None})
    if subclass_of is None:
        class_decl = 'class {}:\n'.format(class_name)
    else:
        class_decl = 'class {}({}):\n'.format(class_name,
                                              subclass_of.__name__)
        _global = {subclass_of.__name__: subclass_of}
    member_decl = '\n'.join(['{} = {}'.format(name, value)
                             for name, value
                             in members.items()])

    exec(class_decl + textwrap.indent(member_decl, '    '),
         _global, _local)

    return _local[class_name]


def make_ast_object(class_name, subclass_of, *init_args, **members):
    """Make object."""
    cls = make_ast_class(class_name, subclass_of, _dummy_ast=True)
    obj = cls(*init_args)

    for name, value in members.items():
        setattr(obj, name, value)

    return obj


def make_ast(tree_dict, parent_name=None, depth=0):
    """Make an ast from scratch."""
    if len(tree_dict) != 1 and depth == 0:
        # error
        raise RuntimeError('only one root node allowed')

    if depth == 0:
        root_name, tree_dict = next(iter(tree_dict.items()))

    children = {}
    for node_name, node_child in tree_dict.items():
        if isinstance(node_child, dict):
            # a class
            sub_tree = make_ast(node_child, node_name, depth+1)
            children[node_name] = sub_tree
        elif isinstance(node_child, list):
            # several children
            child_list = []
            for child in node_child:
                sub_tree = make_ast(child, node_name, depth+1)
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
        ret = make_ast_object(cls_name,
                              None,
                              **children)

    return ret


class ASTVisitor:
    """Visits an AST."""

    def __init__(self, *disallowed, **options):
        """Initialize."""
        self._not_allowed = set()
        self.add_disallowed_prefixes(*disallowed)
        self._dont_visit = False
        self._flags = {}
        self._options = {'logger_fn': None}
        self.reset_visits()
        self.clear_flag('debug_visit')

        # flags
        self.clear_flag('no_children_visits')
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

    def _debug_visit(self, message):
        """Print debug messages when visiting."""
        if self.get_flag_state('debug_visit'):
            print(message)

    def reset_visits(self):
        """Reset visit record."""
        self._visited_nodes = set()

    def add_disallowed_prefixes(self, *prefixes):
        """Disallow visiting of attributes with a prefix."""
        self._not_allowed |= set(prefixes)

    def pause_visiting(self):
        """Stop visiting temporarily."""
        self._dont_visit = True

    def resume_visiting(self):
        """Resume visiting."""
        self._dont_visit = False

    def dont_visit_children(self):
        """Don't visit children of this node."""
        self.set_flag('no_children_visits')

    def has_been_visited(self, node):
        """Check if a node has been visited before."""
        return node in self._visited_nodes

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
            return None

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

        node_dict = getattr(node, '__dict__')
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
        node_dict = getattr(root, '__dict__')
        occurrences = []
        for attr_name, attr in node_dict.items():
            if self._check_visit_allowed(attr_name):
                if self.is_of_type(attr, node_type):
                    occurrences.append(attr)
                elif isinstance(attr, list):
                    for obj in attr:
                        occurrences.extend(self.get_all_occurrences(obj,
                                                                    node_type))
                elif isinstance(attr, str):
                    return []
                else:
                    occurrences.extend(self.get_all_occurrences(attr,
                                                                node_type))

        return occurrences

    def _visit_fn_post(self, cls_name, node):
        """Call corresponding function if present."""
        # print('exiting {}'.format(cls_name))
        try:
            fn = getattr(self, 'visit_{}'.format(cls_name))
        except AttributeError:
            return self._visit_default(node)

        # check if visited before
        if self.has_been_visited(node):
            if self.get_flag_state('ignore_visited'):
                return node
        else:
            self._visited_nodes |= set([node])

        return fn(node)

    def _visit_fn_pre(self, cls_name, node):
        # print('entering {}'.format(cls_name))
        try:
            fn = getattr(self, 'visitPre_{}'.format(cls_name))
        except AttributeError:
            return self._visit_pre_default(node)

        # check if visited before
        if self.has_been_visited(node):
            if self.get_flag_state('ignore_visited'):
                return node

        return fn(node)

    def visit(self, node):
        """Start visting at a certain node."""
        return self._visit(node)

    def _visit_default(self, node):
        try:
            fn = getattr(self, 'visit_Default')
        except AttributeError:
            return node

        return fn(node)

    def _visit_pre_default(self, node):
        try:
            fn = getattr(self, 'visitPre_Default')
        except AttributeError:
            return None

        return fn(node)

    def _check_visit_allowed(self, name):
        for disallowed in self._not_allowed:
            if name.startswith(disallowed):
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
        # call before visiting, cannot modify things
        try:
            if self._dont_visit is False:
                self._visit_fn_pre(node.__class__.__name__, node)
        except Exception as ex:
            raise VisitError(ex)
        try:
            # debug = False
            node_dict = getattr(node, '__dict__')
            if self.get_flag_state('no_children_visits'):
                # reset
                self.clear_flag('no_children_visits')
                # get out
                raise NoChildrenVisits()

            for attr_name in list(node_dict):
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
                            before = (node_dict[attr_name]
                                      [:idx+insertion_offset])
                            after = (node_dict[attr_name]
                                     [idx+insertion_offset+1:])
                            before.extend(result)
                            before.extend(after)
                            insertion_offset += len(result)-1
                            attr_list = before
                            setattr(node, attr_name, attr_list)
                        else:
                            node_dict[attr_name][idx+insertion_offset] = result
                            # setattr(node, attr_name, attr)

                    for idx in to_delete:
                        try:
                            del node_dict[attr_name][idx]
                        except:
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
                return node
        except Exception as ex:
            raise VisitError(ex)
        return ret

    def is_child_of_type(self, node, type_name):
        """Detect if parent of type is available."""
        try:
            getattr(node, 'parent')
        except AttributeError:
            return False
        if node.parent is not None:
            if node.parent.__class__.__name__ == type_name:
                return True
            return self.is_child_of_type(node.parent, type_name)
        else:
            return False

    def find_parent_by_type(self, node, parent_type, level=1):
        """Find nth hierarchical ocurrence of type, upwards."""
        try:
            getattr(node, 'parent')
        except AttributeError:
            return None
        if node.parent is not None:
            if node.parent.__class__.__name__ == parent_type:
                if level > 1:
                    return self.find_parent_by_type(node.parent, parent_type,
                                                    level-1)
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
            node_dict = getattr(node, '__dict__')
            empty_members = {member_name: None for member_name, value in
                             node_dict.items()
                             if self._check_visit_allowed(member_name)}
            class_obj = make_ast_object(node.__class__.__name__,
                                        None,
                                        **empty_members)
            for member in node_dict:
                if self._check_visit_allowed(member) is False:
                    continue
                if isinstance(getattr(node, member), (list, tuple)):
                    ret = []
                    for instance in getattr(node, member):
                        visit_ret = self._visit(instance)
                        try:
                            visit_ret.parent = class_obj
                        except:
                            pass
                        ret.append(visit_ret)
                    setattr(class_obj, member, ret)
                else:
                    ret = self._visit(getattr(node, member))
                    try:
                        ret.parent = class_obj
                    except:
                        pass
                    setattr(class_obj, member, ret)
            return class_obj
        except AttributeError:
            if isinstance(node, str):
                return node[:]
            elif isinstance(node, bool):
                return node
            elif node is not None:
                print('unknown: {}'.format(node))
                return node

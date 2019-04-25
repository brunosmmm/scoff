"""Parse abstract syntax trees."""

import textwrap
import copy


class ScoffASTObject:
    """Scoff abstract syntax tree object."""

    SCOFF_META = {}

    def __init__(self, **kwargs):
        """Initialize."""
        self.__non_visitable_children_names = []
        self.__visitable_children_names = []
        if "SCOFF_META" in kwargs:
            self.SCOFF_META = kwargs.pop("SCOFF_META")
        else:
            self.SCOFF_META = {}
        for name, value in kwargs.items():
            # ignore special names
            if not name.startswith("_") and name != "parent":
                self.__visitable_children_names.append(name)
            else:
                self.__non_visitable_children_names.append(name)
            setattr(self, name, value)

    @property
    def visitable_children(self):
        """Get visitable children."""
        # update
        visitable = {
            name: getattr(self, name)
            for name in self.__visitable_children_names
        }
        return visitable

    @property
    def visitable_children_names(self):
        """Get names of visitable children."""
        return self.__visitable_children_names

    def __dir__(self):
        """Get dir."""
        return self.__visitable_children_names

    def __deepcopy__(self, memo):
        members = {}
        for member_name, member_value in self.visitable_children:
            members[member_name] = copy.deepcopy(member_value)

        ret = self.__class__(
            parent=None, SCOFF_META=copy.deepcopy(self.SCOFF_META), **members
        )

        for member_value in members.values():
            if isinstance(member_value, ScoffASTObject):
                member_value.parent = ret
            elif isinstance(member_value, list):
                for _value in member_value:
                    if isinstance(_value, ScoffASTObject):
                        _value.parent = ret

        return ret

    def copy(self, parent=None):
        """Get a copy."""
        ret = copy.deepcopy(self)
        ret.parent = parent
        return ret


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

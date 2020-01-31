"""AST utility functions."""

import textwrap
from typing import Type, Any, Union
from scoff.ast import ScoffASTObject


def make_ast_class(class_name: str, subclass_of: Type, **members: Any) -> Type:
    """Make class on the fly.

    Arguments
    ---------
    class_name
      Name of class to construct
    subclass_of
      Which class to inherit from
    members
      Members of the dynamically constructed class
    """
    _global = {}
    _local = {}
    # comply with textX stuff being used
    members.update({"_tx_position": None})
    if subclass_of is None:
        class_decl = "class {}:\n".format(class_name)
    else:
        class_decl = "class {}({}):\n".format(class_name, subclass_of.__name__)
        _global = {subclass_of.__name__: subclass_of}
    class_decl += " " * 4 + "__slots__ = ({})\n".format(
        ", ".join('"{}"'.format(name) for name in members)
    )
    init_decl = "def __init__(self, {}):\n".format(
        ", ".join(["{}=None".format(name) for name in members])
    )
    init_decl += "\n".join(
        [
            "    self.{} = {}".format(name, value)
            for name, value in members.items()
        ]
    )

    exec(class_decl + textwrap.indent(init_decl, " " * 4), _global, _local)

    return _local[class_name]


def make_ast_object(
    cls: Union[str, Type], subclass_of: Type, *init_args: Any, **members: Any
) -> Any:
    """Make object.

    Arguments
    ---------
    cls
      AST Object class
    subclass_of
      Which class to inherit from
    init_args
      Object constructor arguments
    members
      Keyword arguments passed into constructor if subclass of ScoffASTObject
    """

    def fake_class_obj(cls_name):
        cls = make_ast_class(cls_name, subclass_of)
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
    """Make an ast from scratch.

    Marked for deprecation
    """
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
            (ret,) = ret
    else:
        ret = make_ast_object(cls_name, None, **children)

    return ret

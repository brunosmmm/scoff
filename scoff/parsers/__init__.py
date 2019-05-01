"""Parse abstract syntax trees."""

import textwrap
import copy


class ScoffASTObject:
    """Scoff abstract syntax tree object."""

    __slots__ = (
        "_parent",
        "_parent_key",
        "SCOFF_META",
        "_visitable_children_names",
        "_non_visitable_children_names",
    )

    def __init__(self, **kwargs):
        """Initialize."""
        self._initialized = False
        self._non_visitable_children_names = []
        self._visitable_children_names = []
        self._parent = None
        self._parent_key = None
        self.SCOFF_META = {}
        if "SCOFF_META" in kwargs:
            self.SCOFF_META = kwargs.pop("SCOFF_META")
        else:
            self.SCOFF_META = {}
        for name, value in kwargs.items():
            # ignore special names
            if isinstance(value, ScoffASTObject) and name != "parent":
                value.parent = self
                value._parent_key = name
            if not name.startswith("_") and name != "parent":
                self._visitable_children_names.append(name)
            else:
                self._non_visitable_children_names.append(name)
            setattr(self, name, value)

        self._initialized = True

    def __setattr__(self, name, value):
        if hasattr(self, "_initialized") and self._initialized:
            if name in self._visitable_children_names:
                if isinstance(value, ScoffASTObject):
                    value.parent = self
                    value._parent_key = name
                elif isinstance(value, (tuple, list)):
                    for _value in value:
                        if isinstance(_value, ScoffASTObject):
                            _value.parent = self
                            _value._parent_key = name
                # remove reference from old object
                old_obj = getattr(self, name)
                if isinstance(old_obj, ScoffASTObject):
                    # old_obj.parent = None
                    pass
                elif isinstance(old_obj, (list, tuple)):
                    for _value in old_obj:
                        if isinstance(_value, ScoffASTObject):
                            # _value.parent = None
                            pass
                del old_obj
        super().__setattr__(name, value)

    @property
    def parent(self):
        """Get parent."""
        return self._parent

    @parent.setter
    def parent(self, value):
        """Set parent."""
        self._parent = value

    @property
    def parent_key(self):
        """Get key name in parent."""
        return self._parent_key

    @property
    def visitable_children_names(self):
        """Get names of visitable children."""
        return self._visitable_children_names

    @property
    def nonvisitable_children_names(self):
        """Get names of children that are not visitable."""
        return self._non_visitable_children_names

    def _remove_backreferences(self):
        # print("__del__ called on {}".format(self.__class__.__name__))
        for member_name in self.visitable_children_names:
            # might already have been deleted
            if member_name in self.__dict__:
                child = getattr(self, member_name)
                if isinstance(child, ScoffASTObject):
                    child._remove_backreferences()
                elif isinstance(child, (tuple, list)):
                    for item in child:
                        if isinstance(item, ScoffASTObject):
                            item._remove_backreferences()
                del child
        self.parent = None

    # def __del__(self):
    #     """Destructor."""
    #     if self.parent is not None:
    #         # print(self.parent_key)
    #         if (
    #             self.parent_key is not None
    #             and hasattr(self.parent, self.parent_key)
    #             and getattr(self.parent, self.parent_key) == self
    #         ):
    #             # print(f"refusing to delete {self}")
    #             return
    #     # print(f"deleting {self}")
    #     self._remove_backreferences()
    #     for member_name in self.visitable_children_names:
    #         # might already been deleted
    #         if member_name in self.__dict__:
    #             del self.__dict__[member_name]

    #     for member_name in self.nonvisitable_children_names:
    #         if member_name in self.__dict__:
    #             del self.__dict__[member_name]

    #     del self.SCOFF_META
    #     if hasattr(self, "__visitable_children_names"):
    #         del self.__visitable_children_names
    #     if hasattr(self, "__non_visitable_children_names"):
    #         del self.__non_visitable_children_names
    #     if hasattr(self, "parent"):
    #         del self._parent

    def delete(self):
        """Setup for removal by garbage collector."""
        self._remove_backreferences()
        for member_name in self.visitable_children_names:
            if member_name in self.__dict__:
                if isinstance(self.__dict__[member_name], ScoffASTObject):
                    self.__dict__[member_name].delete()
                del self.__dict__[member_name]

    def __dir__(self):
        """Get dir."""
        return self._visitable_children_names

    def __deepcopy__(self, memo):
        members = {}
        for member_name in self.visitable_children_names:
            members[member_name] = copy.deepcopy(getattr(self, member_name))

        # flag as copy
        new_meta = copy.deepcopy(self.SCOFF_META)
        new_meta["ast_copy"] = True
        if hasattr(self, "_tx_position"):
            original_start_loc = self._tx_position
        else:
            original_start_loc = None
        if hasattr(self, "_tx_position_end"):
            original_end_loc = self._tx_position_end
        else:
            original_end_loc = None
        new_meta["original_end_loc"] = original_end_loc
        new_meta["original_start_loc"] = original_start_loc

        ret = self.__class__(parent=None, SCOFF_META=new_meta, **members)

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

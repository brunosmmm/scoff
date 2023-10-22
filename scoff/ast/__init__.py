"""Abstract syntax tree."""

import copy
from typing import Union, Optional, Any
from types import GenericAlias


class ASTDefinitionError(Exception):
    """Error in AST class definition."""


class ScoffASTObject:
    """Scoff abstract syntax tree object."""

    __slots__ = (
        "_parent",
        "_parent_key",
        "SCOFF_META",
        "_visitable_children_names",
        "_non_visitable_children_names",
        "_initialized",
        "_root",
        "_textx_data",
        "_precious",
    )
    _slot_types = None

    # NOTE: textx is setting things as a class variable!!!!
    _cls_textx_data = {}

    def __init__(self, root_node: bool = False, **kwargs: Any):
        """Initialize.

        :param root_node: Whether this is the root node or not
        :param kwargs: Any other attributes to be added to the node
        """
        self._initialized = False
        self._non_visitable_children_names = []
        self._visitable_children_names = []
        self._parent = None
        self._root = root_node
        self._parent_key = None
        self._textx_data = copy.copy(self._cls_textx_data)
        self._precious = False
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
            if name.startswith("_tx"):
                self._textx_data[name] = value
            else:
                self._check_slot_type(name, value)
                setattr(self, name, value)
        if hasattr(self, "_slot_types") and self._slot_types is not None:
            if len(self._slot_types) != len(self.__slots__):
                raise ASTDefinitionError("must declare all slot types or none")
        self._check_typing_definitions()

        self._initialized = True

    def _check_typing_definitions(self):
        """Check definitions."""
        annotations = self.__init__.__annotations__
        for slot_name in annotations:
            slot_type = annotations[slot_name]
            if hasattr(slot_type, "__args__"):
                slot_type_args = slot_type.__args__
                generic_alias_used = False
                for arg in slot_type_args:
                    if arg is None:
                        continue
                    if isinstance(arg, GenericAlias):
                        if generic_alias_used:
                            raise ASTDefinitionError(
                                "only one GenericAlias allowed in Union type"
                            )
                        generic_alias_used = True

    def _check_generic_alias(self, slot_type, value):
        """Check when using generic alias."""
        if isinstance(slot_type, GenericAlias):
            # cannot use isinstance directly
            if slot_type.__origin__ not in (list, tuple):
                raise ASTDefinitionError(
                    "only list or tuple supported for GenericAlias"
                )
            type_args = slot_type.__args__
            if len(type_args) > 1:
                raise ASTDefinitionError(
                    "GenericAlias with len > 1 not supported"
                )
            (slot_type,) = slot_type.__args__
            if isinstance(value, (list, tuple)):
                for _value in value:
                    if not isinstance(_value, slot_type):
                        if isinstance(slot_type, type):
                            expected = slot_type.__name__
                        else:
                            expected = repr(slot_type)
                        raise TypeError(
                            f"expected {expected}, "
                            f"got {_value.__class__.__name__}"
                        )
            return True
        return False

    def _check_slot_type(self, slot_name, value):
        """Check type."""
        if slot_name == "parent":
            return
        if hasattr(self, "_slot_types") and self._slot_types is not None:
            name_index = self.__slots__.index(slot_name)
            slot_type = self._slot_types[name_index]
            if slot_type is not None and not isinstance(value, slot_type):
                if isinstance(slot_type, type):
                    expected = slot_type.__name__
                else:
                    expected = repr(slot_type)
                raise TypeError(
                    f"expected {expected}, " f"got {value.__class__.__name__}"
                )
        else:
            annotations = self.__init__.__annotations__
            if slot_name in annotations:
                slot_type = annotations[slot_name]
                if self._check_generic_alias(slot_type, value):
                    return

                try:
                    is_instance = isinstance(value, slot_type)
                except TypeError:
                    # generic alias
                    if hasattr(slot_type, "__args__"):
                        slot_type_args = slot_type.__args__
                        for arg in slot_type_args:
                            if arg is None:
                                continue
                            self._check_generic_alias(arg, value)
                        return
                    else:
                        raise ASTDefinitionError("unknown typing error")

                if not is_instance:
                    if isinstance(slot_type, type):
                        expected = slot_type.__name__
                    else:
                        expected = repr(slot_type)
                    raise TypeError(
                        f"expected {expected}, "
                        f"got {value.__class__.__name__}"
                    )

    def __setattr__(self, name, value):
        """Set an attribute of the AST object.

        This will treat special attributes accordingly and try to set them.
        """
        if hasattr(self, "_initialized") and self._initialized:
            if name in self._visitable_children_names:
                self._check_slot_type(name, value)
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
        if name.startswith("_tx"):
            # HACK: set textX attributes
            if not hasattr(self, "_textx_data"):
                self._cls_textx_data[name] = value
            else:
                self._textx_data[name] = value
            return
        super().__setattr__(name, value)

    def __getattr__(self, name):
        """Get attribute."""
        if name.startswith("_tx"):
            if name in self._textx_data:
                return self._textx_data[name]

        raise AttributeError(name)

    def __delattr__(self, name):
        """Delete attribute."""
        if name.startswith("_tx"):
            if name in self._textx_data:
                del self._textx_data[name]
                return
        super().__delattr__(name)

    @property
    def initialized(self):
        """Get if fully initialized."""
        return hasattr(self, "_initialized") and self._initialized

    @property
    def parent(self):
        """Get parent."""
        if self._root:
            # emulate textx expected behavior
            raise AttributeError()
        return self._parent

    @parent.setter
    def parent(self, value: Union["ScoffASTObject", None]):
        """Set parent."""
        # self._textx_data.parent = value
        if hasattr(self, "_initialized") and self._initialized and self._root:
            return
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

    @property
    def textx_data(self):
        """Get textx data proxy object."""
        return self._textx_data

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
        new_meta["original_end_loc"] = self._textx_data.get("_tx_position_end")
        new_meta["original_start_loc"] = self._textx_data.get("_tx_position")

        ret = self.__class__(parent=None, SCOFF_META=new_meta, **members)

        for member_value in members.values():
            if isinstance(member_value, ScoffASTObject):
                member_value.parent = ret
            elif isinstance(member_value, list):
                for _value in member_value:
                    if isinstance(_value, ScoffASTObject):
                        _value.parent = ret
        return ret

    def copy(self, parent: Optional["ScoffASTObject"] = None):
        """Get a copy.

        :param parent: A node to set as parent after copying
        """
        ret = copy.deepcopy(self)
        ret.parent = parent
        return ret

    def _generate_code(self, **kwargs: Any) -> str:
        """Actually generate code."""
        raise NotImplementedError

    def generate_code(self, **kwargs: Any) -> str:
        """Generate code."""
        indent_str = kwargs.get("indent_str", "  ")
        indent_level = kwargs.get("indent", 0)
        ret = self._generate_code(**kwargs)
        return indent_str * indent_level + ret

    @property
    def precious(self):
        """Get precious."""
        return self._precious

    @precious.setter
    def precious(self, value: bool):
        """Set precious."""
        self._precious = value

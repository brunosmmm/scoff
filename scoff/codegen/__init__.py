"""Code generator."""

from typing import Dict, Type, Any, Callable


def indent(fn: Callable) -> Callable:
    """Indent decorator.

    Adds indentation to generated code
    :param fn: Code generation function
    """

    def wrapper(*args, **kwargs):
        if not isinstance(args[0], CodeGenerator):
            raise TypeError(
                "decorator can only be used on CodeGenerator " "objects"
            )
        # generate indentation
        args[0].increase_indent()
        if args[0].indent is True:
            indent_str = args[0].indent_str
        else:
            indent_str = ""

        if "dont_indent" in kwargs and kwargs["dont_indent"] is True:
            return fn(*args, **kwargs)
        else:
            ret = "\n".join(
                [indent_str + x for x in fn(*args, **kwargs).split("\n")]
            )
        args[0].decrease_indent()
        return ret

    return wrapper


class CodeGenerator:
    """Abstract class for code generators."""

    class_aliases: Dict[str, Type] = {}

    def __init__(self, indent: bool = False, indent_str: str = "    "):
        """Initialize.

        :param indent: Whether to indent code or node
        :param indent_str: Indentation string
        """
        self.indent_level = 0
        self.indent = indent
        self.indent_str = indent_str

    def increase_indent(self):
        """Increase indentation level."""
        self.indent_level += 1

    def decrease_indent(self):
        """Decrease indentation level."""
        if self.indent_level > 0:
            self.indent_level -= 1

    def add_class_alias(self, use_as: Type, alias_class: str):
        """Add class alias."""
        self.class_aliases[alias_class] = use_as

    def _check_validity(self, element: Any) -> bool:
        return True

    def dump_element(self, element: Any, **kwargs: Any) -> str:
        """Get code representation for an element.

        :param element: Element to be dumped
        :param kwargs: Additional flags
        :return: Generated code
        """
        cls_name = element.__class__.__name__
        gen_method_name = "gen_{}".format(cls_name)

        # check statement validity
        if self._check_validity(element) is False:
            raise ValueError("illegal statement passed: {}".format(element))

        # aliases
        if cls_name in self.class_aliases:
            cls_name = self.class_aliases[cls_name]
            gen_method_name = "gen_{}".format(cls_name)

        gen_method = None
        if hasattr(self, gen_method_name):
            gen_method = getattr(self, gen_method_name)
            return gen_method(element, **kwargs)
        if hasattr(element, "generate_code"):
            # try builtin code generation method
            gen_method = getattr(element, "generate_code")
            return gen_method(**kwargs)
        if element.__class__.__bases__:
            # try base class
            alt_gen_method_name = (
                f"gen_{element.__class__.__bases__[0].__name__}"
            )
            if hasattr(self, alt_gen_method_name):
                gen_method = getattr(self, alt_gen_method_name)
                return gen_method(element, **kwargs)

        raise TypeError(f"cannot generate code for object type {cls_name}")

    # builtin types

    def gen_int(self, element: int, **kwargs: Any) -> str:
        """Generate integer."""
        return str(element)

    def get_str(self, element: str, **kwargs: Any) -> str:
        """Generate string."""
        return element

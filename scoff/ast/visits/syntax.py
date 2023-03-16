"""Basic Syntax checker pass."""

from collections import deque, OrderedDict
from typing import Any, Dict, Tuple, Union, Optional, List, Type, Callable

from scoff.ast import ScoffASTObject
from scoff.ast.visits import ASTVisitor, VisitError
from scoff.ast.visits.scope import ScopeMixin
from scoff.errors import (
    ErrorCodeException,
    ErrorDescriptor,
    ErrorGeneratorMixin,
)


class SyntaxCheckerError(ErrorCodeException):
    """Syntax checker error."""


class SyntaxErrorDescriptor(ErrorDescriptor):
    """Error descriptor."""

    def __init__(self, *args):
        """Initialize.

        :param args: Any other ErrorDescriptor arguments
        """
        super().__init__(*args, exception_class=SyntaxCheckerError)


class SyntaxChecker(ASTVisitor, ErrorGeneratorMixin):
    """Syntax checks."""

    SYNTAX_ERR_GLOBAL_NAME_REDEFINED = 10
    SYNTAX_ERR_LOCAL_NAME_REDEFINED = 11
    SYNTAX_ERR_INVALID_IDENTIFIER = 12
    _SYNTAX_ERRORS = {}
    __SYNTAX_ERRORS = {
        SYNTAX_ERR_GLOBAL_NAME_REDEFINED: SyntaxErrorDescriptor(
            SYNTAX_ERR_GLOBAL_NAME_REDEFINED,
            "Re-definition of global name",
            "re-definition of global name" ' "{n}"',
        ),
        SYNTAX_ERR_LOCAL_NAME_REDEFINED: SyntaxErrorDescriptor(
            SYNTAX_ERR_LOCAL_NAME_REDEFINED,
            "Re-definition of local name",
            "re-definition of local name" ' "{n}"',
        ),
        SYNTAX_ERR_INVALID_IDENTIFIER: SyntaxErrorDescriptor(
            SYNTAX_ERR_INVALID_IDENTIFIER,
            "Invalid identifier",
            'invalid identifier: "{id}"',
        ),
    }

    def __init__(self, text: str, *args, **kwargs: Any):
        """Initialize.

        :param text: The text being parsed; this is used to track error \
        locations
        :param args: Any other visitor arguments
        :param kwargs: Any other visitor keyword arguments
        """
        super().__init__(*args, **kwargs)
        self._text = text
        self._SYNTAX_ERRORS.update(self.__SYNTAX_ERRORS)
        self._initialize()

    def _initialize(self, symbols=None, **flags):
        # (re)initialize
        self._pass_run = False
        self._collected_globals = OrderedDict()
        self._collected_locals = OrderedDict()
        self._collected_scopes = OrderedDict()
        self._scope_stack = deque()
        for flag_name, flag_value in flags.items():
            if bool(flag_value):
                self.set_flag(flag_name)
            else:
                self.clear_flag(flag_name)

        if symbols is not None:
            for symbol_name, symbol in symbols.items():
                self._collect_symbol(symbol_name, symbol)

    def visit(self, node: ScoffASTObject, flag_run=True):
        """Visit node.

        :param node: Node to start visiting at
        :param flag_run: Whether to flag as run after visiting or not
        """
        try:
            super().visit(node)
        except VisitError as err:
            if isinstance(err.ex, SyntaxCheckerError):
                raise err.ex
            # just raise
            raise
        if flag_run:
            self._pass_run = True

    def _visit_default(self, node: ScoffASTObject):
        """Override default visit from base class."""
        ret = super()._visit_default(node)
        if isinstance(node, ScopeMixin):
            self._exit_scope(node)
        return ret

    def _visit_pre_default(self, node: ScoffASTObject):
        """Override default pre-visit from base class."""
        if isinstance(node, ScopeMixin):
            self._enter_scope(node)
        return super()._visit_pre_default(node)

    def _enter_scope(self, location: ScoffASTObject):
        """Enter scope.

        :param location: Node which represents the scope, location is internal
        """
        if location is not None and location in self._collected_scopes:
            self._debug_visit(f"RE-ENTERING scope at {location}")
            # entering again
            self._scope_stack.append([location, self._collected_locals])
            _, self._collected_locals = self._collected_scopes[location]
        elif location is not None:
            self._debug_visit(f"entering scope at {location}")
            # create new
            # new_local_scope = self._collected_locals.copy()
            self._scope_stack.append([location, self._collected_locals])
            self._collected_locals = OrderedDict()

    def _exit_scope(self, location: ScoffASTObject):
        """Exit scope.

        :param location: Node which represents scope
        """
        self._debug_visit(
            "exiting scope, depth = {}".format(len(self._scope_stack))
        )
        if self._pass_run is False:
            old_local_scope = self._collected_locals.copy()
            enter_loc, self._collected_locals = self._scope_stack.pop()
            self._collected_scopes[enter_loc] = [location, old_local_scope]
        else:
            enter_loc, self._collected_locals = self._scope_stack.pop()

    def swap_scope_node(
        self, old_loc: ScoffASTObject, new_loc: ScoffASTObject
    ):
        """Replace scope node."""
        if old_loc is not None and old_loc in self._collected_scopes:
            if new_loc in self._collected_scopes:
                raise RuntimeError("cannot replace scope")
            self._debug_visit(f"replacing scope {old_loc} -> {new_loc}")
            # find in stack
            found = False
            for idx, (scope, _locals) in enumerate(self._scope_stack):
                if scope == old_loc:
                    found = True
                    break
            if found:
                self._scope_stack[idx] = [new_loc, _locals]

            collected_locals = self._collected_scopes.pop(old_loc)
            self._collected_scopes[new_loc] = collected_locals
        else:
            raise RuntimeError("cannot replace scope")

    def _collect_symbol(
        self,
        name: str,
        node: ScoffASTObject,
        globl: bool = False,
        ignore_redefine: bool = False,
    ):
        """Add symbol to symbol table.

        :param name: Symbol name
        :param node: The symbol
        :param globl: Whether this is a global name
        :param ignore_redefine: Ignore re-defines or raise error
        """
        # verify if identifier is valid
        if not self.is_valid_identifier(name):
            raise self.get_error_from_code(
                node, self.SYNTAX_ERR_INVALID_IDENTIFIER, id=name
            )
        if len(self._scope_stack) == 0 or globl is True:
            # global symbol
            self._debug_visit('collecting global symbol: "{}"'.format(name))
            if name in self._collected_globals and ignore_redefine is False:
                raise self.get_error_from_code(
                    node, self.SYNTAX_ERR_GLOBAL_NAME_REDEFINED, n=name
                )
            if name not in self._collected_globals:
                self._collected_globals[name] = node
        else:
            self._debug_visit('collecting local symbol: "{}"'.format(name))
            if name in self._collected_locals and ignore_redefine is False:
                raise self.get_error_from_code(
                    node, self.SYNTAX_ERR_LOCAL_NAME_REDEFINED, n=name
                )
            if name not in self._collected_locals:
                self._collected_locals[name] = node

    def get_node_scope(
        self, node: ScoffASTObject
    ) -> Dict[str, ScoffASTObject]:
        """Get scope in which this node is declared.

        :param node: An AST node
        :return: Symbol table for node scope
        """
        for location, (end_loc, scope) in self._collected_scopes.items():
            for symbol_name, symbol in scope.items():
                if symbol == node:
                    return scope
        for symbol_name, symbol in self._collected_globals.items():
            if symbol == node:
                return scope

    def get_current_scope_depth(self) -> int:
        """Get current scope depth.

        :return: Current scope depth
        """
        return len(self._scope_stack)

    @staticmethod
    def find_node_line_in_text(
        txt: str, position: int
    ) -> Union[None, Tuple[int, int]]:
        """Find node location in text.

        :param txt: Source text
        :param location: Character location in text
        :return: (line, col) location of node or None
        """
        current_pos = 0
        for idx, line in enumerate(txt.split("\n")):
            if position is None:
                return None
            if current_pos + len(line) + 1 < position:
                current_pos += len(line) + 1
                continue
            else:
                if current_pos != 0:
                    col = (position) % current_pos
                else:
                    col = 0
                return (idx + 1, col)

    def find_node_line(
        self,
        node: ScoffASTObject,
        alternate_node: Optional[ScoffASTObject] = None,
    ) -> Union[None, Tuple[int, int]]:
        """Find node location in text.

        :param node: An AST node
        :param alternate_node: An optional alternate node related to the node.\
        This will be used in case the original node's location is not found
        :return: Location in text
        """
        # FIXME: _tx attributes do not work
        if (
            not hasattr(node, "textx_data")
            and "_tx_position" not in node.textx_data
        ):
            if (
                alternate_node is None
                or not hasattr(alternate_node, "textx_data")
                or "_tx_position" not in alternate_node.textx_data
            ):
                return None
            node = alternate_node

        return self.find_node_line_in_text(
            self._text, node.textx_data["_tx_position"]
        )

    def get_error(
        self,
        node: ScoffASTObject,
        message: str,
        code: Optional[Union[str, int]] = None,
        exception: Optional[Exception] = None,
        alternate_node: Optional[ScoffASTObject] = None,
    ) -> SyntaxCheckerError:
        """Get syntax error exception.

        :param node: An AST node to use as the location
        :param message: The error message
        :param code: The error code
        :param exception: The error exception
        :param alternate_node: An alternate node to be used as location in \
        case the original cannot be located
        :return: A syntax error exception
        """
        line, col = self.find_node_line(node, alternate_node)
        loc_fmt = f"({line}.{col})"
        return SyntaxCheckerError(
            "at {}: {}".format(loc_fmt, message),
            code,
            exception,
        )

    def get_error_from_code(
        self,
        node: ScoffASTObject,
        code: Union[str, int],
        alternate_node: Optional[ScoffASTObject] = None,
        **msg_kwargs: str,
    ) -> SyntaxCheckerError:
        """Get exception from code.

        :param node: An AST object
        :param code: The error code
        :param alternate_node: Alternate node to use as location in case the \
        original cannot be located
        :return: A syntax error exception
        """
        if "_exception" in msg_kwargs:
            exception = msg_kwargs.pop("_exception")
        else:
            exception = None
        msg = super().get_error_from_code(
            code, self._SYNTAX_ERRORS, **msg_kwargs
        )
        return self.get_error(node, msg, code, exception, alternate_node)

    def scoped_symbol_lookup(self, name: str) -> Union[ScoffASTObject, None]:
        """In-scope Symbol lookup.

        :param name: Name to lookup
        :return: Symbols
        """
        # locals first
        if name in self._collected_locals:
            return self._collected_locals[name]
        for location, scope in self._scope_stack:
            if name in scope:
                return scope[name]
        if name in self._collected_globals:
            return self._collected_globals[name]

        return None

    # FIXME: the return value of this always causes me a ton of headache
    def _symbol_lookup(
        self, name: str
    ) -> List[Tuple[ScoffASTObject, Dict[str, ScoffASTObject]]]:
        """Overall symbol lookup.

        This looks up symbols in all nested scopes upwards.
        """
        ret = []
        if name in self._collected_globals:
            ret.append(
                [self._collected_globals[name], self._collected_globals]
            )

        for location, (end_loc, scope) in self._collected_scopes.items():
            if name in scope:
                ret.append([scope[name], scope])

        return ret

    def symbol_lookup(self, name: str) -> List[ScoffASTObject]:
        """Overall symbol lookup.

        This will look up symbols in all nested scopes upwards in the scope\
         hierarchy.

        :param name: Symbol name
        :return: Symbols
        """
        return [symbol for symbol, _ in self._symbol_lookup(name)]

    def report_symbols(self) -> Dict[str, Dict[str, ScoffASTObject]]:
        """Report all symbols collected.

        :return: Dictionary of symbols per scope
        """
        ret = {"globals": {}}
        for symbol_name, symbol in self._collected_globals.items():
            ret["globals"][symbol_name] = symbol

        for start_loc, (end_loc, scope) in self._collected_scopes.items():
            ret["scope_{}".format(start_loc)] = {}
            for symbol_name, symbol in scope.items():
                ret["scope_{}".format(start_loc)][symbol_name] = symbol

        return ret

    def get_global_symbols_by_type(
        self, symbol_type: Type
    ) -> Dict[str, ScoffASTObject]:
        """Return all symbols of type which were recorded.

        :param symbol_type: The symbol type
        :return: Dictionary with all symbols found
        """
        symbols_by_type = {}
        for symbol_name, symbol in self._collected_globals.items():
            if isinstance(symbol, symbol_type):
                symbols_by_type[symbol_name] = symbol

        return symbols_by_type

    def _clear_collected_scopes(self):
        """Clear scopes."""
        self._collected_scopes = OrderedDict()

    @classmethod
    def is_valid_identifier(cls, identifier: str) -> bool:
        """Determine if identifier is valid.

        :param identifier: String identifier for object
        :return: Whether the identifier is valid
        """
        if not hasattr(cls, "IDENTIFIER_REGEX"):
            # just return true, we accept all
            return True
        m = cls.IDENTIFIER_REGEX.match(identifier)
        return bool(m is not None)


# Typing aliases
NodeVisitorFunction = Callable[SyntaxChecker, Union[ScoffASTObject, None]]


def enter_scope(fn: NodeVisitorFunction) -> Callable:
    """Enter scope.

    Signal to the syntax checker that a scope is entered in this node.
    """

    def wrapper(chk, node):
        chk._enter_scope(node)
        return fn(chk, node)

    return wrapper


def enter_scope_after(fn: NodeVisitorFunction) -> Callable:
    """Enter scope after.

    Signal to the syntax checker that a scope is entered AFTER visiting this \
    node.
    :param fn: Node visitor function
    :return: Decorated function
    """

    def wrapper(chk, node):
        ret = fn(chk, node)
        chk._enter_scope(node)
        return ret

    return wrapper


def exit_scope(fn: NodeVisitorFunction) -> Callable:
    """Exit scope.

    Signal to the syntax checker that the current scope is exited when \
    visiting this node.
    :param fn: Node visitor function
    :return: Decorated function
    """

    def wrapper(chk, node):
        chk._exit_scope(node)
        return fn(chk, node)

    return wrapper


def exit_scope_after(fn: NodeVisitorFunction) -> Callable:
    """Exit scope after.

    Signal to the syntax checker that the current scope is exited AFTER \
    visiting this node.
    :param fn: Node visitor function
    :return: Decorated function
    """

    def wrapper(chk, node):
        ret = fn(chk, node)
        chk._exit_scope(node)
        return ret

    return wrapper


class AutoCollect:
    """Automatically collect symbol.

    collects the current node as symbol, using the node_field as the field \
    from which the symbol's name is sourced.
    """

    def __init__(self, node_field: str):
        """Initialize.

        :param node_field: Attribute name to source symbol name from
        """
        self._field = node_field

    def __call__(self, fn: NodeVisitorFunction):
        """Call."""

        def wrapper(chk, node):
            if not hasattr(node, self._field):
                raise RuntimeError(
                    "invalid attribute for node: {}".format(self._field)
                )
            chk._collect_symbol(getattr(node, self._field), node)
            return fn(chk, node)

        return wrapper


class AutoCollectConditional:
    """Automatically collect symbol depending on flag state.

    collects the current node as symbol, using the node_field as the field \
    from which the symbol's name is sourced, dependin on a condition
    """

    def __init__(self, node_field: str, chk_flag: str):
        """Initialize.

        :param node_field: Attribute name to source symbol name from
        :param chk_flag: Flag to check on visitor
        """
        self._field = node_field
        self._flag = chk_flag

    def __call__(self, fn: NodeVisitorFunction):
        """Call."""

        def wrapper(chk, node):
            if not hasattr(node, self._field):
                raise RuntimeError(
                    "invalid attribute for node: {}".format(self._field)
                )
            if chk.get_flag_state(self._flag):
                chk._collect_symbol(getattr(node, self._field), node)
            return fn(chk, node)

        return wrapper

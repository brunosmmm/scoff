"""Basic Syntax checker pass."""

from scoff.ast.visits import ASTVisitor, VisitError
from scoff.errors import (
    ErrorCodeException,
    ErrorDescriptor,
    ErrorGeneratorMixin,
)
from collections import deque, OrderedDict


class SyntaxCheckerError(ErrorCodeException):
    """Syntax checker error."""

    pass


class SyntaxErrorDescriptor(ErrorDescriptor):
    """Error descriptor."""

    def __init__(self, *args):
        """Initialize."""
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

    def __init__(self, text, *args, **kwargs):
        """Initialize."""
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

    def visit(self, node, flag_run=True):
        """Visit node."""
        try:
            super().visit(node)
        except VisitError as err:
            if isinstance(err.ex, SyntaxCheckerError):
                raise err.ex
            # just raise
            raise
        if flag_run:
            self._pass_run = True

    def _enter_scope(self, location):
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

    def _exit_scope(self, location):
        self._debug_visit(
            "exiting scope, depth = {}".format(len(self._scope_stack))
        )
        if self._pass_run is False:
            old_local_scope = self._collected_locals.copy()
            enter_loc, self._collected_locals = self._scope_stack.pop()
            self._collected_scopes[enter_loc] = [location, old_local_scope]
        else:
            enter_loc, self._collected_locals = self._scope_stack.pop()

    def _collect_symbol(self, name, node, globl=False, ignore_redefine=False):
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

    def get_node_scope(self, node):
        """Get scope in which this node is declared."""
        for location, (end_loc, scope) in self._collected_scopes.items():
            for symbol_name, symbol in scope.items():
                if symbol == node:
                    return scope
        for symbol_name, symbol in self._collected_globals.items():
            if symbol == node:
                return scope

    def get_current_scope_depth(self):
        """Get current scope depth."""
        return len(self._scope_stack)

    def find_node_line(self, node):
        """Find node location."""
        try:
            pos = getattr(node, "_tx_position")
        except AttributeError:
            return None
        return self._find_node_line(node, pos)

    @staticmethod
    def find_node_line_in_text(txt, position):
        current_pos = 0
        for idx, line in enumerate(txt.split("\n")):
            if position is None:
                return None
            if current_pos + len(line) < position:
                current_pos += len(line)
                continue
            else:
                if current_pos != 0:
                    col = (position - idx) % current_pos
                else:
                    col = 0
                return (idx + 1, col)

    def _find_node_line(self, node, position):
        """Find line where node is located."""
        return self.find_node_line_in_text(self._text, position)

    def get_error(self, node, message, code=None, exception=None):
        """Get syntax error exception."""
        return SyntaxCheckerError(
            "at {}: {}".format(self.find_node_line(node), message),
            code,
            exception,
        )

    def get_error_from_code(self, node, code, **msg_kwargs):
        """Get exception from code."""
        if "_exception" in msg_kwargs:
            exception = msg_kwargs.pop("_exception")
        else:
            exception = None
        msg = super().get_error_from_code(
            code, self._SYNTAX_ERRORS, **msg_kwargs
        )
        return self.get_error(node, msg, code, exception)

    def scoped_symbol_lookup(self, name):
        """In-scope Symbol lookup."""
        # locals first
        if name in self._collected_locals:
            return self._collected_locals[name]
        for location, scope in self._scope_stack:
            if name in scope:
                return scope[name]
        if name in self._collected_globals:
            return self._collected_globals[name]

        return None

    def _symbol_lookup(self, name):
        """Overall symbol lookup."""
        ret = []
        if name in self._collected_globals:
            ret.append(
                [self._collected_globals[name], self._collected_globals]
            )

        for location, (end_loc, scope) in self._collected_scopes.items():
            if name in scope:
                ret.append([scope[name], scope])

        return ret

    def symbol_lookup(self, name):
        """Overall symbol lookup."""
        return [symbol for symbol, scope in self._symbol_lookup(name)]

    def report_symbols(self):
        """Report all symbols collected."""
        ret = {"globals": {}}
        for symbol_name, symbol in self._collected_globals.items():
            ret["globals"][symbol_name] = symbol

        for start_loc, (end_loc, scope) in self._collected_scopes.items():
            ret["scope_{}".format(start_loc)] = {}
            for symbol_name, symbol in scope.items():
                ret["scope_{}".format(start_loc)][symbol_name] = symbol

        return ret

    def get_global_symbols_by_type(self, symbol_type):
        """Return all symbols of type which were recorded."""
        symbols_by_type = {}
        for symbol_name, symbol in self._collected_globals.items():
            if self.is_of_type(symbol, symbol_type):
                symbols_by_type[symbol_name] = symbol

        return symbols_by_type

    def _clear_collected_scopes(self):
        """Clear scopes."""
        self._collected_scopes = OrderedDict()

    @classmethod
    def is_valid_identifier(cls, identifier):
        """Determine if identifier is valid."""
        if not hasattr(cls, "IDENTIFIER_REGEX"):
            # just return true, we accept all
            return True
        m = cls.IDENTIFIER_REGEX.match(identifier)
        return bool(m is not None)


def enter_scope(fn):
    """Enter scope."""

    def wrapper(chk, node):
        chk._enter_scope(node)
        return fn(chk, node)

    return wrapper


def enter_scope_after(fn):
    """Enter scope after."""

    def wrapper(chk, node):
        ret = fn(chk, node)
        chk._enter_scope(node)
        return ret

    return wrapper


def exit_scope(fn):
    """Exit scope."""

    def wrapper(chk, node):
        chk._exit_scope(node)
        return fn(chk, node)

    return wrapper


def exit_scope_after(fn):
    """Exit scope after."""

    def wrapper(chk, node):
        ret = fn(chk, node)
        chk._exit_scope(node)
        return ret

    return wrapper


def auto_collect(fn, node_field):
    """Automatically collect symbol."""

    def wrapper(chk, node):
        if not hasattr(node, node_field):
            raise RuntimeError(
                "invalid attribute for node: {}".format(node_field)
            )
        chk._collect_symbol(getattr(node, node_field), node)

    return wrapper


class AutoCollect:
    """Automatically collect symbol."""

    def __init__(self, node_field):
        """Initialize."""
        self._field = node_field

    def __call__(self, fn):
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
    """Automatically collect symbol depending on flag state."""

    def __init__(self, node_field, chk_flag):
        """Initialize."""
        self._field = node_field
        self._flag = chk_flag

    def __call__(self, fn):
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

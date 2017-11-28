"""Basic Syntax checker pass."""

from .tree import ASTVisitor, VisitError
from collections import deque, OrderedDict


class SyntaxCheckerError(Exception):
    """Syntax checker error."""

    def __init__(self, message, code=None):
        """Initialize."""
        self.msg = message
        self.code = code

    def __repr__(self):
        """Representation."""
        if self.code is not None:
            err_code = '(#{})'.format(self.code)
        else:
            err_code = ''
        return '{} {}'.format(err_code, self.msg)

    def __str__(self):
        """Get string."""
        return self.__repr__()


class SyntaxErrorDescriptor:
    """Error descriptor."""

    def __init__(self, error_code, brief, fmt_str):
        """Initialize."""
        self.code = error_code
        self.brief = brief
        self.fmt_str = fmt_str

    def get_message(self, **msg_kwargs):
        """Get error message."""
        return self.fmt_str.format(**msg_kwargs)

    def get_exception(self, **msg_kwargs):
        """Get Exception."""
        err_msg = self.get_message(**msg_kwargs)
        return SyntaxCheckerError(err_msg, self.code)


class SyntaxChecker(ASTVisitor):
    """Syntax checks."""

    SYNTAX_ERR_GLOBAL_NAME_REDEFINED = 10
    SYNTAX_ERR_LOCAL_NAME_REDEFINED = 11
    _SYNTAX_ERRORS = {}
    __SYNTAX_ERRORS = {SYNTAX_ERR_GLOBAL_NAME_REDEFINED:
                       SyntaxErrorDescriptor(SYNTAX_ERR_GLOBAL_NAME_REDEFINED,
                                             'Re-definition of global name',
                                             're-definition of global name'
                                             ' "{n}"'),
                       SYNTAX_ERR_LOCAL_NAME_REDEFINED:
                       SyntaxErrorDescriptor(SYNTAX_ERR_LOCAL_NAME_REDEFINED,
                                             'Re-definition of local name',
                                             're-definition of local name'
                                             ' "{n}"')}

    def __init__(self, text, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self._text = text
        self._SYNTAX_ERRORS.update(self.__SYNTAX_ERRORS)
        self._initialize()

    def _initialize(self, **flags):
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
            self._debug_visit('RE-ENTERING scope at location {}'
                              .format(location))
            # entering again
            self._scope_stack.append([location, self._collected_locals])
            _, self._collected_locals = self._collected_scopes[location]
        else:
            self._debug_visit('entering scope')
            # create new
            # new_local_scope = self._collected_locals.copy()
            self._scope_stack.append([location, self._collected_locals])
            self._collected_locals = OrderedDict()

    def _exit_scope(self, location):
        self._debug_visit('exiting scope, depth = {}'
                          .format(len(self._scope_stack)))
        if self._pass_run is False:
            old_local_scope = self._collected_locals.copy()
            enter_loc, self._collected_locals = self._scope_stack.pop()
            self._collected_scopes[enter_loc] = [location, old_local_scope]
        else:
            enter_loc, self._collected_locals = self._scope_stack.pop()

    def _collect_symbol(self, name, node):
        if len(self._scope_stack) == 0:
            # global symbol
            self._debug_visit('collecting global symbol: "{}"'.format(name))
            if name in self._collected_globals:
                raise self.get_error_from_code(
                    node,
                    self.SYNTAX_ERR_GLOBAL_NAME_REDEFINED,
                    n=name)
            self._collected_globals[name] = node
        else:
            self._debug_visit('collecting local symbol: "{}"'.format(name))
            if name in self._collected_locals:
                raise self.get_error_from_code(
                    node,
                    self.SYNTAX_ERR_LOCAL_NAME_REDEFINED,
                    n=name)
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

    def find_node_line(self, node):
        """Find line where node is located."""
        try:
            getattr(node, '_tx_position')
        except AttributeError:
            return None
        current_pos = 0
        for idx, line in enumerate(self._text.split('\n')):
            if node._tx_position is None:
                return None
            if current_pos + len(line) < node._tx_position:
                current_pos += len(line)
                continue
            else:
                if current_pos != 0:
                    col = (node._tx_position-idx) % current_pos
                else:
                    col = 0
                return (idx+1, col)

    def get_error(self, node, message, code=None):
        """Get syntax error exception."""
        return SyntaxCheckerError('at {}: {}'.
                                  format(self.find_node_line(node),
                                         message), code)

    def get_error_from_code(self, node, code, **msg_kwargs):
        """Get exception from code."""
        if code not in self._SYNTAX_ERRORS:
            raise KeyError('unknown error code: {}'.format(code))

        msg = self._SYNTAX_ERRORS[code].get_message(**msg_kwargs)
        return self.get_error(node, msg, code)

    def scoped_symbol_lookup(self, name):
        """In-scope Symbol lookup."""
        # locals first
        for symbol_name, symbol in self._collected_locals.items():
            if symbol_name == name:
                return symbol
        for location, scope in self._scope_stack:
            for symbol_name, symbol in scope.items():
                if name == symbol_name:
                    return symbol
        for symbol_name, symbol in self._collected_globals.items():
            if name == symbol_name:
                return symbol
        return None

    def _symbol_lookup(self, name):
        """Overall symbol lookup."""
        ret = []
        for symbol_name, symbol in self._collected_globals.items():
            if name == symbol_name:
                ret.append([symbol, self._collected_globals])

        for location, (end_loc, scope) in self._collected_scopes.items():
            for symbol_name, symbol in scope.items():
                if name == symbol_name:
                    ret.append([symbol, scope])

        return ret

    def symbol_lookup(self, name):
        """Overall symbol lookup."""
        return [symbol for symbol, scope in self._symbol_lookup(name)]

    def report_symbols(self):
        """Report all symbols collected."""
        ret = {'globals': {}}
        for symbol_name, symbol in self._collected_globals.items():
            ret['globals'][symbol_name] = symbol

        for start_loc, (end_loc, scope) in self._collected_scopes.items():
            ret['scope_{}'.format(start_loc)] = {}
            for symbol_name, symbol in scope.items():
                ret['scope_{}'.format(start_loc)][symbol_name] = symbol

        return ret

    def get_global_symbols_by_type(self, symbol_type):
        """Return all symbols of type which were recorded."""
        symbols_by_type = {}
        for symbol_name, symbol in self._collected_globals.items():
            if self.is_of_type(symbol, symbol_type):
                symbols_by_type[symbol_name] = symbol

        return symbols_by_type

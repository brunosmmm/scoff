"""Parsing error generation."""


class ErrorCodeException(Exception):
    """Exception with error code."""

    def __init__(self, message, code=None, exception=None):
        """Initialize."""
        self.msg = message
        self.code = code
        self.exception = exception

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


class ErrorDescriptor:
    """Error descriptor."""

    def __init__(self, error_code, brief, fmt_str, exception_class):
        """Initialize."""
        if not issubclass(exception_class, ErrorCodeException):
            raise TypeError('argument "exception_class" must be an instance '
                            'of type ErrorCodeException')

        self.code = error_code
        self.brief = brief
        self.fmt_str = fmt_str
        self.ex_class = exception_class

    def get_message(self, **msg_kwargs):
        """Get error message."""
        return self.fmt_str.format(**msg_kwargs)

    def get_exception(self, **msg_kwargs):
        """Get Exception."""
        err_msg = self.get_message(**msg_kwargs)
        return self.ex_class(err_msg, self.code)


class ErrorGeneratorMixin:
    """Error generator Mixin."""

    def get_error_from_code(self, code, errors, **msg_kwargs):
        """Get error from code."""
        if code not in errors:
            raise KeyError('unknown error code: {}'.format(code))

        suffix = ''
        prefix = ''
        if '_msg_suffix' in msg_kwargs:
            suffix = msg_kwargs.pop('_msg_suffix')
        if '_msg_prefix' in msg_kwargs:
            prefix = msg_kwargs.pop('_msg_prefix')

        return '{prefix}{msg}{suffix}'.format(
            prefix=prefix,
            msg=errors[code].get_message(**msg_kwargs),
            suffix=suffix)

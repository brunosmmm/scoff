"""Error generation."""

from typing import Any, Union


class ErrorCodeException(Exception):
    """Exception with error code."""

    def __init__(
        self, message, code: Union[None, str, int] = None, exception=None
    ):
        """Initialize."""
        self.msg = message
        self.code = code
        self.exception = exception

    def __repr__(self):
        """Representation."""
        if self.code is not None:
            err_code = "(#{})".format(self.code)
        else:
            err_code = ""
        return "{} {}".format(err_code, self.msg)

    def __str__(self):
        """Get string."""
        return self.__repr__()


class ErrorDescriptor:
    """Error descriptor."""

    def __init__(
        self, error_code, brief, fmt_str, exception_class, debug_callback=None
    ):
        """Initialize."""
        if not issubclass(exception_class, ErrorCodeException):
            raise TypeError(
                'argument "exception_class" must be an instance '
                "of type ErrorCodeException"
            )

        self.code = error_code
        self.brief = brief
        self.fmt_str = fmt_str
        self.ex_class = exception_class
        if debug_callback is not None:
            if not callable(debug_callback):
                raise TypeError("debug_callback must be a callable")
        self._debug_callback = debug_callback

    def get_message(self, **msg_kwargs):
        """Get error message."""
        return self.fmt_str.format(**msg_kwargs)

    def get_exception(self, **msg_kwargs):
        """Get Exception."""
        err_msg = self.get_message(**msg_kwargs)
        return self.ex_class(err_msg, self.code)

    @property
    def debug_cb(self):
        """Get debug callback."""
        return self._debug_callback

    @debug_cb.setter
    def debug_cb(self, debug_callback):
        """Set debug callback."""
        if not callable(debug_callback):
            raise TypeError("debug_callback must be a callable")
        self._debug_callback = debug_callback


class ErrorGeneratorMixin:
    """Error generator Mixin."""

    @staticmethod
    def get_error_from_code(code, errors, **msg_kwargs):
        """Get error from code."""
        if code not in errors:
            raise KeyError("unknown error code: {}".format(code))

        suffix = ""
        prefix = ""
        if "_msg_suffix" in msg_kwargs:
            suffix = msg_kwargs.pop("_msg_suffix")
        if "_msg_prefix" in msg_kwargs:
            prefix = msg_kwargs.pop("_msg_prefix")

        # call error callback if exists
        err = errors[code]
        if err.debug_cb is not None:
            err.debug_cb(err, **msg_kwargs)

        return "{prefix}{msg}{suffix}".format(
            prefix=prefix, msg=err.get_message(**msg_kwargs), suffix=suffix,
        )

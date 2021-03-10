"""Error generation."""

from typing import Union, Optional, Callable, Type, Dict
from scoff.ast import ScoffASTObject

ExceptionCodeType = Union[str, int]


class ErrorCodeException(Exception):
    """Exception with error code."""

    def __init__(
        self,
        message: str,
        code: Optional[ExceptionCodeType] = None,
        exception: Optional[Exception] = None,
        alternate_node: Optional[ScoffASTObject] = None,
    ):
        """Initialize.

        :param msg: The error message
        :param code: The error code
        :param exception: An embedded exception associated to the error
        :param alternate_node: An alternate AST node associated to the error
        """
        self.msg = message
        self.code = code
        self.exception = exception

    def __repr__(self):
        """Get representation."""
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
        self,
        error_code: ExceptionCodeType,
        brief: str,
        fmt_str: str,
        exception_class: Type,
        debug_callback: Optional[Callable] = None,
    ):
        """Initialize.

        :param error_code: The error code
        :param brief: A brief description of the error
        :param fmt_str: A complete description of the error, including format \
        string pieces for templating the error message
        :param exception_class: Class of the exception for the error
        :param debug_callback: Optional callback to be called when error occurs
        """
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

    def get_message(self, **msg_kwargs: str) -> str:
        """Get error message.

        :param msg_kwargs: Values for formatting of the error message
        :return: Formatted error message
        """
        return self.fmt_str.format(**msg_kwargs)

    def get_exception(self, **msg_kwargs: str) -> Exception:
        """Get Exception.

        :param msg_kwargs: Values for formatting of the error message
        :return: Exception object
        """
        err_msg = self.get_message(**msg_kwargs)
        return self.ex_class(err_msg, self.code)

    @property
    def debug_cb(self):
        """Get debug callback."""
        return self._debug_callback

    @debug_cb.setter
    def debug_cb(self, debug_callback: Callable):
        """Set debug callback.

        :param debug_callback: The callback
        """
        if not callable(debug_callback):
            raise TypeError("debug_callback must be a callable")
        self._debug_callback = debug_callback


class ErrorGeneratorMixin:
    """Error generator Mixin."""

    @staticmethod
    def get_error_from_code(
        code: ExceptionCodeType,
        errors: Dict[ExceptionCodeType, ErrorDescriptor],
        **msg_kwargs: str
    ) -> str:
        """Get error from code.

        :param code: Error code
        :param errors: Dictionary containing possible errors
        :param msg_kwargs: Values for error message templating
        :return: Formatted error message
        """
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
            prefix=prefix,
            msg=err.get_message(**msg_kwargs),
            suffix=suffix,
        )

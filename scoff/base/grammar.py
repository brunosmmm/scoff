"""Parse grammars."""

from typing import Tuple, Any
from textx.metamodel import metamodel_from_file


def parse_text(text: str, grammar_file: str) -> Tuple[str, Any]:
    """Parse text directly.

    :param text: Text to be parsed
    :param grammar_file: Path to grammar file
    :return: Tuple (text, AST)
    """
    meta = metamodel_from_file(grammar_file)
    decl = meta.model_from_str(text)
    return (text, decl)


def parse_file(filename: str, grammar_file: str) -> Tuple[str, str]:
    """Parse a source file.

    :param filename: Path to file
    :param grammar_file: Path to grammar file
    :return: Tuple(text, AST)
    """
    f = open(filename, "r")
    text = "".join(f.readlines())
    f.close()

    return _parse_text(text, grammar_file)

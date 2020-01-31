"""Parse grammars."""

from typing import Tuple, Any
from textx.metamodel import metamodel_from_file


def _parse_text(text: str, grammar_file: str) -> Tuple[str, Any]:
    """Parse text directly."""
    meta = metamodel_from_file(grammar_file)
    decl = meta.model_from_str(text)
    return (text, decl)


def _parse_file(filename: str, grammar_file: str) -> Tuple[str, str]:
    """Parse some source."""
    f = open(filename, "r")
    text = "".join(f.readlines())
    f.close()

    return _parse_text(text, grammar_file)

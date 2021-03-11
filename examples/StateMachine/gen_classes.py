#!/usr/bin/env python3
"""Generate AST classes from grammar."""

import pkg_resources
from scoff.misc.textx import parse_textx_grammar, build_python_class_text

if __name__ == "__main__":

    the_grammar = pkg_resources.resource_filename("sm", "state_machine.tx")
    grammar_rules = parse_textx_grammar(the_grammar)

    dump_txt = """
\"\"\"Generated AST classes.\"\"\"
from scoff.ast import ScoffASTObject

"""
    cls_names = []
    for rule_name, rule_members in grammar_rules.items():
        class_name, class_txt = build_python_class_text(
            rule_name, "ScoffASTObject", *rule_members
        )
        dump_txt += class_txt + "\n\n"
        cls_names.append(class_name)

    dump_txt += "GENERATED_AST_CLASSES = ({})".format(", ".join(cls_names))

    print(dump_txt)

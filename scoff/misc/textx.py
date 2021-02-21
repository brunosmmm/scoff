"""Auto-generate custom TextX AST classes."""

import re

try:
    import black
except ImportError:
    black = None

GRAMMAR_RULE_REGEX = re.compile(
    r"([a-zA-Z_]\w*)\s*:(((['\"];['\"])|[^;])+);", re.S
)
RULE_MEMBER_REGEX = re.compile(
    r"([a-zA-Z_]\w*)\s*([?\+\*]?)=\s*([^\s]+)", re.S
)
if black is not None:
    BLACK_FILE_MODE = black.FileMode(line_length=79)


def parse_textx_rule(rule_definition):
    """Parse a rule definition."""
    members = re.findall(RULE_MEMBER_REGEX, rule_definition)

    # shortcut to optional members
    revised_members = []
    for member in members:
        name, operator, value = member
        if value.endswith("?"):
            operator = "?"

        revised_members.append((name, operator, value))

    return [(member[0], member[1]) for member in revised_members]


def parse_textx_grammar(grammar_file):
    """Parse grammar file."""
    with open(grammar_file, "r") as f:
        contents = f.read()

    rules = re.findall(GRAMMAR_RULE_REGEX, contents)

    grammar_rules = {}
    for rule in rules:
        rule_name = rule[0]
        rule_body = rule[1]
        rule_members = parse_textx_rule(rule_body.strip())
        if len(rule_members) < 1:
            continue

        grammar_rules[rule_name.strip()] = rule_members

    return grammar_rules


def build_python_class_text(class_name, subclass_of, *members):
    """Build python class declaration."""
    member_arguments = []
    optional_arguments = []
    for member in members:
        member_name, member_operator = member
        if member_operator in ("?", "*"):
            # optional
            optional_arguments.append("{name}=None".format(name=member_name))
        else:
            member_arguments.append(member_name)
    member_arguments.extend(optional_arguments)
    class_contents = """
class {name}({parent_class}):
    \"\"\"{name} AST.\"\"\"
    __slots__ = ({slots})
    def __init__(self, parent, {members}, **kwargs):
        \"\"\"Initialize.\"\"\"
        super().__init__(parent=parent, {member_assign}, **kwargs)
    """.format(
        name=class_name,
        parent_class=subclass_of,
        members=", ".join(member_arguments),
        slots=", ".join(
            [
                '"{}"'.format(member[0])
                for member in members
                if member != "parent"
            ]
        ),
        member_assign=", ".join(
            ["{name}={name}".format(name=member[0]) for member in members]
        ),
    )
    if black is not None:
        return (
            class_name,
            black.format_str(class_contents, mode=BLACK_FILE_MODE),
        )
    else:
        return (class_name, class_contents)

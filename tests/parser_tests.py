"""Other parser tests."""

from scoff.parsers.tree import ASTVisitor
from scoff.parsers import make_ast
import json

ast_json = """
{
    "Root": {
		"statements": [{
				"Definition": {
					  "name": [{
                "Name": {
                    "val": "def1"
                }
            }],
					  "value": [{
                "Value": {
                    "val": "1"
                }
            }]
				}
			},
			{
				"Definition": {
					  "name": [{
                "Name": {
                    "val": "def2"
                }
            }],
            "value": [{
                "Value": {
                    "val": 2
                }
            }]
				}
			}
		]
	}
}
    """
ast_dict = json.loads(ast_json)


def test_ast_maker():
    """Test make_ast."""
    ast = make_ast(ast_dict)


def test_visitor():
    """Test ASTVisitor."""
    visitor = ASTVisitor()
    ast = make_ast(ast_dict)
    ret = visitor.get_all_occurrences(ast, "Value")
    if len(ret) != 2:
        raise RuntimeError
    for obj in ret:
        if not visitor.is_of_type(obj, "Value"):
            raise RuntimeError

    first = visitor.get_first_occurrence(ast, "Value")
    if first != ret[0]:
        raise RuntimeError

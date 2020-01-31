"""AST Duplicator."""

from scoff.ast.visits import ASTVisitor
from scoff.ast import ScoffASTObject

import copy


class ASTCopy(ASTVisitor):
    """Makes a fake copy of the AST."""

    def _visit(self, node):

        try:
            if isinstance(node, ScoffASTObject):
                node_dict = node.visitable_children
            else:
                node_dict = {
                    name: item
                    for name, item in node.__dict__.items()
                    if not name.startswith("_") and name != "parent"
                }
            empty_members = {
                member_name: None for member_name, value in node_dict.items()
            }
            if hasattr(node, "_tx_position"):
                original_start_loc = node._tx_position
            else:
                original_start_loc = None
            if hasattr(node, "_tx_position_end"):
                original_end_loc = node._tx_position_end
            else:
                original_end_loc = None
            empty_members.update(
                {
                    "SCOFF_META": {
                        "ast_copy": True,
                        "original_start_loc": original_start_loc,
                        "original_end_loc": original_end_loc,
                    }
                }
            )
            # class_obj = make_ast_object(node.__class__, None, **empty_members)
            class_obj = copy.deepcopy(node)
            for member in node_dict:
                if self._check_visit_allowed(member) is False:
                    continue
                if isinstance(getattr(node, member), (list, tuple)):
                    ret = []
                    for instance in getattr(node, member):
                        visit_ret = self._visit(instance)
                        visit_ret.parent = class_obj
                        ret.append(visit_ret)
                    setattr(class_obj, member, ret)
                else:
                    ret = self._visit(getattr(node, member))
                    ret.parent = class_obj
                    setattr(class_obj, member, ret)
            return class_obj
        except AttributeError:
            if isinstance(node, str):
                return node[:]
            if isinstance(node, bool):
                return node
            if isinstance(node, dict):
                return node.copy()
            if node is not None:
                self._debug_visit("unknown: {}".format(node))
                return node
            raise

#!/usr/bin/env python3
"""Visit and check State Machines."""

import sys
import pkg_resources
from argparse import ArgumentParser
from scoff.base.grammar import parse_file
from scoff.ast.visits.syntax import (
    SyntaxChecker,
    enter_scope,
    exit_scope,
    SyntaxErrorDescriptor,
    SyntaxCheckerError,
)
from scoff.ast.visits.control import no_child_visits

from sm import STATE_MACHINE_CLASSES


class StateMachineChecker(SyntaxChecker):
    """Visit state machine definitions."""

    _SYNTAX_ERRORS = {
        "err1": SyntaxErrorDescriptor(
            "err1", "Event redeclared", "In state {s}: event {e} redeclared"
        ),
        "err2": SyntaxErrorDescriptor(
            "err2",
            "Event has no effect",
            "In state {s}: event {e} has no effect",
        ),
    }

    def __init__(self, *args, **kwargs):
        """Initialize."""
        super().__init__(*args, **kwargs)
        self._visited_states = set()
        self._state_data = {}
        self._current_state = None

    def visitStateMachine(self, node):
        """Visit state machine definition"""
        return node

    @enter_scope
    def visitPre_State(self, node):
        """Enter state. """
        self._current_state = node.name
        self._state_data[node.name] = {"actions": [], "transitions": {}}

    @exit_scope
    def visit_State(self, node):
        """Visit state definitions."""
        return node

    def visit_Event(self, node):
        """Visit event."""
        return node

    @no_child_visits
    def visitPre_Transition(self, node):
        """Enter transition."""
        # check error #1
        ret = self.scoped_symbol_lookup(node.event.name)
        if ret is not None:
            # already declared
            raise self.get_error_from_code(
                node, "err1", e=node.event.name, s=self.current_state
            )
        self._collect_symbol(node.event.name, node.event)

        # check error #2
        if node.to_state.name == self.current_state:
            # has no effect
            raise self.get_error_from_code(
                node, "err2", e=node.event.name, s=self.current_state
            )

    def visit_Transition(self, node):
        """Visit transition."""
        data = self.current_state_data
        transitions = data["transitions"]
        transitions[node.event.name] = node.to_state.name
        return node

    def visit_Command(self, node):
        """Visit command.

        This occurs in a state or in the main definition.
        """
        if self.current_state is not None:
            # state definition
            self._state_data[self.current_state]["actions"].append(node.name)

        return node

    @property
    def states(self):
        """Get states."""
        return list(self._state_data.keys())

    @property
    def current_state(self):
        """Get current state."""
        return self._current_state

    @property
    def current_state_data(self):
        """Get current state data."""
        if self.current_state is None:
            return None
        return self._state_data[self.current_state]

    def get_state_actions(self, state_name):
        """Get state actions."""
        return self._state_data[state_name]["actions"]

    def get_state_transitions(self, state_name):
        """Get state transitions."""
        return self._state_data[state_name]["transitions"]


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument("fname", help="state machine file")

    args = parser.parse_args()

    sm_grammar = pkg_resources.resource_filename("sm", "state_machine.tx")
    # load grammar and file
    text, ast = parse_file(args.fname, sm_grammar, STATE_MACHINE_CLASSES)

    # visit ast
    visitor = StateMachineChecker(text)
    try:
        visitor.visit(ast)
    except SyntaxCheckerError as ex:
        print(f"ERROR: {ex}")
        exit(1)

    # print info
    states = visitor.states
    print("Found states: " + ", ".join(states), file=sys.stderr)
    for state in states:
        print(f"State {state}:", file=sys.stderr)
        for action in visitor.get_state_actions(state):
            print(f" Action: {action}", file=sys.stderr)
        for _from, to in visitor.get_state_transitions(state).items():
            print(f" Transition: {_from} -> {to}", file=sys.stderr)

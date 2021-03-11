#!/usr/bin/env python3
"""Parse and visit state machine."""

import sys
import pkg_resources
from argparse import ArgumentParser
from collections import deque
from scoff.base.grammar import parse_file
from scoff.ast.visits.exclusive import ASTVisitor

from sm import STATE_MACHINE_CLASSES


class StateMachineVisitor(ASTVisitor):
    """Visit state machine definitions."""

    def __init__(self, **kwargs):
        """Initialize."""
        super().__init__(**kwargs)
        self._visited_states = set()
        self._state_data = {}
        self._state_stack = deque()
        self._ignore_state = False

    def visitStateMachine(self, node):
        """Visit state machine definition"""
        return node

    def visitPre_State(self, node):
        """Enter state.

        Avoid infinite recursion by keeping track of visited states
        """
        if node.name in self._state_data:
            self.dont_visit_children()
            self._ignore_state = True
            return
        self._state_data[node.name] = {"actions": [], "transitions": {}}
        self._state_stack.append(node.name)

    def visit_State(self, node):
        """Visit state definitions."""
        if self._ignore_state is False:
            self._state_stack.pop()
        else:
            self._ignore_state = False
        return node

    def visit_Event(self, node):
        """Visit event."""
        return node

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
        if not self._state_stack:
            return None
        return self._state_stack[-1]

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

    sys.setrecursionlimit(100)
    parser = ArgumentParser()
    parser.add_argument("fname", help="state machine file")

    args = parser.parse_args()

    sm_grammar = pkg_resources.resource_filename("sm", "state_machine.tx")
    # load grammar and file
    text, ast = parse_file(args.fname, sm_grammar, STATE_MACHINE_CLASSES)

    # visit ast
    visitor = StateMachineVisitor(debug_visit=True)
    visitor.visit(ast)

    # print info
    states = visitor.states
    print("Found states: " + ", ".join(states))
    for state in states:
        print(f"State {state}:")
        for action in visitor.get_state_actions(state):
            print(f" Action: {action}")
        for _from, to in visitor.get_state_transitions(state).items():
            print(f" Transition: {_from} -> {to}")

"""State Machine AST."""

from scoff.ast import ScoffASTObject


class StateMachine(ScoffASTObject):
    """State machine."""

    __slots__ = ("events", "resetEvents", "commands", "states")

    def __init__(self, events, resetEvents, commands, states, **kwargs):
        """Initialize."""
        super().__init__(
            root_node=True,
            parent=None,
            events=events,
            resetEvents=resetEvents,
            commands=commands,
            states=states,
            **kwargs,
        )

    def _generate_code(self, **kwargs):
        """Generate code."""
        fsm = ""
        events = "\n".join(
            [event.generate_code(indent=1, **kwargs) for event in self.events]
        )
        reset_evts = (
            "\n".join(["  " + event.name for event in self.resetEvents])
            if self.resetEvents is not None
            else ""
        )
        commands = "\n".join(
            [
                command.generate_code(indent=1, **kwargs)
                for command in self.commands
            ]
        )
        states = "\n".join(
            [state.generate_code(**kwargs) for state in self.states]
        )
        fsm += f"events\n{events}\nend\n"
        fsm += (
            f"\nresetEvents\n{reset_evts}\nend\n"
            if self.resetEvents is not None
            else ""
        )
        fsm += f"commands\n{commands}\nend\n"
        fsm += states
        return fsm


class Event(ScoffASTObject):
    """Events."""

    __slots__ = ("name", "code")

    def __init__(self, parent, name, code, **kwargs):
        """Initialize."""
        super().__init__(parent=parent, name=name, code=code, **kwargs)

    def _generate_code(self, **kwargs):
        """Generate code."""
        return f"{self.name} {self.code}"


class Command(ScoffASTObject):
    """Commands."""

    __slots__ = ("name", "code")

    def __init__(self, parent, name, code, **kwargs):
        """Initialize."""
        super().__init__(parent=parent, name=name, code=code, **kwargs)

    def _generate_code(self, **kwargs):
        """Generate code."""
        return f"{self.name} {self.code}"


class State(ScoffASTObject):
    """States."""

    __slots__ = ("name", "actions", "transitions")

    def __init__(self, parent, name, actions, transitions, **kwargs):
        """Initialize."""
        super().__init__(
            parent=parent,
            name=name,
            actions=actions,
            transitions=transitions,
            **kwargs,
        )

    def _generate_code(self, **kwargs):
        """Generate code."""
        state = f"state {self.name}\n"
        act_list = (
            ", ".join([action.name for action in self.actions])
            if self.actions is not None
            else ""
        )
        actions = (
            f"  actions {{{act_list}}}\n"
            if self.actions is not None and self.actions
            else ""
        )
        state += actions
        transitions = "\n".join(
            [
                transition.generate_code(indent=1, **kwargs)
                for transition in self.transitions
            ]
        )
        state += transitions
        state += "\nend"
        return state


class Transition(ScoffASTObject):
    """Transitions."""

    __slots__ = ("event", "to_state")

    def __init__(self, parent, event, to_state, **kwargs):
        """Initialize."""
        super().__init__(
            parent=parent, event=event, to_state=to_state, **kwargs
        )

    def _generate_code(self, **kwargs):
        """Generate code."""
        return f"{self.event.name} => {self.to_state.name}"


STATE_MACHINE_CLASSES = [StateMachine, Event, Command, State, Transition]

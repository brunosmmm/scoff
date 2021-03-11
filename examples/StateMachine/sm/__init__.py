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
            **kwargs
        )


class Event(ScoffASTObject):
    """Events."""

    __slots__ = ("name", "code")

    def __init__(self, parent, name, code, **kwargs):
        """Initialize."""
        super().__init__(parent=parent, name=name, code=code, **kwargs)


class Command(ScoffASTObject):
    """Commands."""

    __slots__ = ("name", "code")

    def __init__(self, parent, name, code, **kwargs):
        """Initialize."""
        super().__init__(parent=parent, name=name, code=code, **kwargs)


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
            **kwargs
        )


class Transition(ScoffASTObject):
    """Transitions."""

    __slots__ = ("event", "to_state")

    def __init__(self, parent, event, to_state, **kwargs):
        """Initialize."""
        super().__init__(
            parent=parent, event=event, to_state=to_state, **kwargs
        )


STATE_MACHINE_CLASSES = [StateMachine, Event, Command, State, Transition]

"""Visit objects."""


class ScoffVisitObject:
    """A temporary storage class used during visits."""


class ScoffVisitList(ScoffVisitObject, list):
    """Temporary list storage."""


class ScoffVisitDict(ScoffVisitObject, dict):
    """Temporary dict storage."""


class ScoffVisitSet(ScoffVisitObject, set):
    """Temporary set storage."""

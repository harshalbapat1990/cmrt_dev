"""Typed calculation failures shared by table calculators."""


class DatasetLookupError(ValueError):
    """A required factor lookup did not find a record in the selected dataset."""


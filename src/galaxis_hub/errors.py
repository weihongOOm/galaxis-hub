class DbError(Exception):
    """Wraps any underlying Supabase / network error so callers get a stable surface."""


class ProjectNotFoundError(Exception):
    """Raised by the DB layer when project_id has no matching row."""

    def __init__(self, project_id: str) -> None:
        super().__init__(project_id)
        self.project_id = project_id


class UnknownSectionError(Exception):
    """Raised by the tool layer when a requested section is not in VALID_SECTIONS."""

    def __init__(self, section: str) -> None:
        super().__init__(section)
        self.section = section

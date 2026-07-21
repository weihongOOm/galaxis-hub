import pytest

from galaxis_hub.db import GalaxisDB
from galaxis_hub.errors import DbError, ProjectNotFoundError


class FakeQuery:
    def __init__(self, table_name: str, data: list[dict]):
        self._table = table_name
        self._data = data
        self.last_ilike: tuple[str, str] | None = None
        self.last_eq: tuple[str, object] | None = None
        self.last_in: tuple[str, list[str]] | None = None
        self.last_order: tuple[str, bool] | None = None
        self.last_limit: int | None = None

    def select(self, columns):
        return self

    def ilike(self, column, pattern):
        self.last_ilike = (column, pattern)
        return self

    def eq(self, column, value):
        self.last_eq = (column, value)
        return self

    def in_(self, column, values):
        self.last_in = (column, list(values))
        return self

    def order(self, column, desc=False):
        self.last_order = (column, desc)
        return self

    def limit(self, n):
        self.last_limit = n
        return self

    def execute(self):
        return type("R", (), {"data": self._data})()


class FakeClient:
    def __init__(self, table_to_data: dict[str, list[dict]]):
        self._t = table_to_data
        self.calls: list[tuple[str, FakeQuery]] = []

    def table(self, name):
        q = FakeQuery(name, self._t.get(name, []))
        self.calls.append((name, q))
        return q


def test_search_projects_uses_ilike_and_limit():
    client = FakeClient(
        {"v_projects": [{"id": "p1", "client_name": "Acme", "website": "acme.com"}]}
    )
    db = GalaxisDB(client)
    rows = db.search_projects("acm", limit=5)
    assert rows == [{"id": "p1", "client_name": "Acme", "website": "acme.com"}]
    _, q = client.calls[0]
    assert q.last_ilike == ("client_name", "%acm%")
    assert q.last_order == ("client_name", False)
    assert q.last_limit == 5


def test_get_latest_output_without_sections_returns_all():
    client = FakeClient(
        {
            "v_latest_project_output": [
                {
                    "project_id": "p1",
                    "section": "keywords",
                    "content": "kw",
                    "created_at": "2024-01-01",
                },
            ],
            "v_projects": [{"id": "p1"}],
        }
    )
    db = GalaxisDB(client)
    rows = db.get_latest_output("p1")
    assert len(rows) == 1
    assert rows[0]["section"] == "keywords"


def test_get_latest_output_with_sections_uses_in_filter():
    client = FakeClient(
        {
            "v_latest_project_output": [
                {
                    "project_id": "p1",
                    "section": "keywords",
                    "content": "kw",
                    "created_at": "2024-01-01",
                },
            ],
            "v_projects": [{"id": "p1"}],
        }
    )
    db = GalaxisDB(client)
    db.get_latest_output("p1", sections=["keywords", "avatar"])
    _, q = client.calls[0]
    assert q.last_in == ("section", ["keywords", "avatar"])


def test_get_latest_output_raises_project_not_found_when_no_rows_and_no_project():
    client = FakeClient({"v_latest_project_output": [], "v_projects": []})
    db = GalaxisDB(client)
    with pytest.raises(ProjectNotFoundError):
        db.get_latest_output("missing")


def test_get_latest_output_returns_empty_when_project_exists_but_no_matching_sections():
    client = FakeClient(
        {
            "v_latest_project_output": [],
            "v_projects": [{"id": "p1"}],
        }
    )
    db = GalaxisDB(client)
    rows = db.get_latest_output("p1", sections=["keywords"])
    assert rows == []


def test_search_projects_wraps_db_errors():
    class ExplodingClient:
        def table(self, name):
            raise RuntimeError("boom")

    with pytest.raises(DbError):
        GalaxisDB(ExplodingClient()).search_projects("acm")

import pytest

from galaxis_hub.db import GalaxisDB
from galaxis_hub.errors import DbError
from galaxis_hub.tools import get_project_info, search_projects
from galaxis_hub.tools.get_project_info import _validate_sections

# --- search_projects ---


def test_search_projects_returns_db_results():
    db = GalaxisDB(
        _client_returning(
            v_projects=[
                {"id": "p1", "client_name": "Acme", "website": "acme.com"},
            ]
        )
    )
    assert search_projects(db, "acm") == [
        {"id": "p1", "client_name": "Acme", "website": "acme.com"}
    ]


def test_search_projects_empty_query_returns_empty_list_without_db_call():
    client = _client_returning(v_projects=[])
    db = GalaxisDB(client)
    assert search_projects(db, "   ") == []
    assert client.calls == []


def test_search_projects_wraps_db_error():
    class ExplodingClient:
        def table(self, name):
            raise RuntimeError("boom")

    with pytest.raises(DbError):
        search_projects(GalaxisDB(ExplodingClient()), "acm")


# --- get_project_info: validation ---


def test_validate_sections_none_returns_none():
    assert _validate_sections(None) is None


def test_validate_sections_empty_returns_none():
    assert _validate_sections([]) is None
    assert _validate_sections(["", "  "]) is None


def test_validate_sections_dedup_preserves_order():
    assert _validate_sections(["keywords", "avatar", "keywords"]) == ["keywords", "avatar"]


def test_validate_sections_rejects_unknown():
    from galaxis_hub.errors import UnknownSectionError

    with pytest.raises(UnknownSectionError) as exc:
        _validate_sections(["keywords", "not_a_section"])
    assert exc.value.section == "not_a_section"


# --- get_project_info: happy path ---


def test_get_project_info_groups_rows_by_section():
    db = GalaxisDB(
        _client_returning(
            v_latest_project_output=[
                {"project_id": "p1", "section": "kyc", "content": "K", "created_at": "2024-01-01"},
                {
                    "project_id": "p1",
                    "section": "keywords",
                    "content": "KW",
                    "created_at": "2024-01-02",
                },
            ],
            v_projects=[{"id": "p1"}],
        )
    )
    out = get_project_info(db, "p1")
    assert out == {"project_id": "p1", "sections": {"kyc": "K", "keywords": "KW"}}


def test_get_project_info_passes_sections_to_db():
    client = _client_returning(
        v_latest_project_output=[
            {
                "project_id": "p1",
                "section": "keywords",
                "content": "KW",
                "created_at": "2024-01-01",
            },
        ],
        v_projects=[{"id": "p1"}],
    )
    db = GalaxisDB(client)
    get_project_info(db, "p1", sections=["keywords"])
    _, q = client.calls[0]
    assert q.last_in == ("section", ["keywords"])


# --- get_project_info: error envelopes ---


def test_get_project_info_unknown_project_returns_envelope():
    db = GalaxisDB(
        _client_returning(
            v_latest_project_output=[],
            v_projects=[],
        )
    )
    out = get_project_info(db, "missing")
    assert out == {"error": "project_not_found", "project_id": "missing"}


def test_get_project_info_unknown_section_returns_envelope():
    db = GalaxisDB(_client_returning(v_latest_project_output=[]))
    out = get_project_info(db, "p1", sections=["nope"])
    assert out["error"] == "unknown_section"
    assert out["section"] == "nope"
    assert "keywords" in out["valid_sections"]


def test_get_project_info_blank_project_id_is_treated_as_not_found():
    db = GalaxisDB(_client_returning(v_latest_project_output=[], v_projects=[]))
    out = get_project_info(db, "   ")
    assert out["error"] == "project_not_found"


# --- helpers ---


class _FakeQuery:
    def __init__(self, data):
        self._data = data
        self.last_in = None

    def select(self, c):
        return self

    def ilike(self, c, p):
        return self

    def eq(self, c, v):
        return self

    def in_(self, c, v):
        self.last_in = (c, list(v))
        return self

    def order(self, c, desc=False):
        return self

    def limit(self, n):
        return self

    def execute(self):
        return type("R", (), {"data": self._data})()


class _FakeClient:
    def __init__(self, table_to_data):
        self._t = table_to_data
        self.calls = []

    def table(self, name):
        q = _FakeQuery(self._t.get(name, []))
        self.calls.append((name, q))
        return q


def _client_returning(**table_to_data):
    return _FakeClient(table_to_data)

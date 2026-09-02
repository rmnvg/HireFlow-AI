from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app import models  # noqa: F401
from app.database import Base


def test_expected_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == {"jobs", "candidates", "calls", "webhook_events"}


def test_all_tables_compile_for_postgresql() -> None:
    statements = [
        str(CreateTable(table).compile(dialect=postgresql.dialect()))
        for table in Base.metadata.sorted_tables
    ]

    assert len(statements) == 4
    assert all("CREATE TABLE" in statement for statement in statements)


def test_call_request_id_is_unique() -> None:
    request_id = Base.metadata.tables["calls"].columns["request_id"]
    assert request_id.unique is True


def test_foreign_keys_use_cascade_deletes() -> None:
    calls = Base.metadata.tables["calls"]
    assert next(iter(calls.columns["job_id"].foreign_keys)).ondelete == "CASCADE"
    assert next(iter(calls.columns["candidate_id"].foreign_keys)).ondelete == "CASCADE"


def test_candidate_apollo_id_is_unique_within_each_job() -> None:
    candidates = Base.metadata.tables["candidates"]
    unique_column_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in candidates.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }

    assert ("job_id", "apollo_id") in unique_column_sets

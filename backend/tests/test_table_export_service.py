from datetime import date

import pytest

from services import table_export_service as exports


def test_export_rejects_invalid_scope_and_csv_formulas():
    with pytest.raises(ValueError):
        exports.export_table("raw_sql", "csv")
    with pytest.raises(ValueError):
        exports.export_table("event", "csv", date_from=date(2026, 10, 29), date_to=date(2026, 10, 28))
    assert exports._cell("=HYPERLINK(\"bad\")") == "'=HYPERLINK(\"bad\")"


def test_export_refuses_unbounded_result(monkeypatch):
    class Cursor:
        def execute(self, *_): pass
        def fetchone(self): return {"count": exports.MAX_ROWS + 1}

    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): pass
        def cursor(self): return Cursor()

    monkeypatch.setattr(exports, "get_db", Connection)
    with pytest.raises(ValueError, match="narrow the filters"):
        exports.export_table("event", "xlsx")

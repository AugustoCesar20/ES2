# tests/test_integration.py

import json
from pathlib import Path
from unittest.mock import patch
import pytest

from toolkit_cli import (
    FileOrganizer,
    Converter,
    AddressBook,
    shutil as tk_shutil, 
)

# INTEGRACAO
@pytest.mark.integration
def test_apply_nao_mexe_de_verdade_com_patch(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("x", encoding="utf-8")
    moves_gravados = []

    def fake_move(src, dst):
        moves_gravados.append((str(src), str(dst)))

    with patch.object(tk_shutil, "move", side_effect=fake_move):
        org = FileOrganizer(tmp_path)
        plano = org.apply(simulate=False)

    assert plano == moves_gravados and len(plano) == 1

# INTEGRACAO
@pytest.mark.integration
def test_converter_varied_keys_roundtrip(tmp_path: Path):
    data = [{"a": 1, "b": 2}, {"a": 3, "c": 4}]
    jp, cp, op = tmp_path / "d.json", tmp_path / "d.csv", tmp_path / "out.json"
    jp.write_text(json.dumps(data), encoding="utf-8")

    rows, cols = Converter.json_to_csv(jp, cp)
    assert rows == 2 and cols == 3  

    rows2, _ = Converter.csv_to_json(cp, op)
    loaded = json.loads(op.read_text(encoding="utf-8"))
    assert rows2 == 2 and len(loaded) == 2 and set(loaded[0].keys()) == {"a", "b", "c"}

# INTEGRACAO
@pytest.mark.integration
def test_fileorganizer_plan_with_noext_and_uppercase(tmp_path: Path):
    (tmp_path / "Makefile").write_text("x", encoding="utf-8")
    (tmp_path / "IMG.JPG").write_text("x", encoding="utf-8")
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    org = FileOrganizer(tmp_path)

    plan = org.plan()
    assert "_sem_ext" in plan and "jpg" in plan and "txt" in plan

    moves_sim = org.apply(simulate=True)
    assert len(moves_sim) == 3

    recorded = []

    def fake_move(src, dst):
        recorded.append((str(src), str(dst)))

    with patch.object(tk_shutil, "move", side_effect=fake_move):
        moves_real = org.apply(simulate=False)

    assert moves_real == recorded and len(recorded) == 3

# INTEGRACAO
@pytest.mark.integration
def test_addressbook_filter_and_delete_missing(tmp_path: Path):
    db = tmp_path / "addr.sqlite3"
    ab = AddressBook(db_path=db)
    id2 = ab.add("Bruno", "bru@x.com", "222")

    assert any(r[0] == id2 for r in ab.list(q="Br"))
    assert ab.delete(999999) is False

# INTEGRACAO
@pytest.mark.integration
def test_addressbook_end_to_end(tmp_path: Path):
    db = tmp_path / "addr.sqlite3"
    ab = AddressBook(db_path=db)

    id1 = ab.add("Ana", "ana@x.com", "111")
    id2 = ab.add("Bruno", "bru@x.com", "222")

    all_ids = [r[0] for r in ab.list()]
    assert id1 in all_ids and id2 in all_ids
    filtered_ids = [r[0] for r in ab.list(q="Br")]
    assert id2 in filtered_ids 

    ab2 = AddressBook(db_path=db)
    still_there = [r[0] for r in ab2.list()]
    assert set(still_there) == set(all_ids)

    assert ab2.delete(id2) is True
    assert all(r[0] != id2 for r in ab2.list())

    assert ab2.delete(id1) is True
    assert ab2.list() == []

    assert ab2.delete(999999) is False

import json
from pathlib import Path
from toolkit_cli import TaskManager, NotesManager, HabitTracker, Calculator, pretty_table
import re

def test_managers_load_corrupted_reset(tmp_path: Path):
    # tasks
    p = tmp_path / "tasks.json"; p.write_text("{broken", encoding="utf-8")
    tm = TaskManager(path=p); assert tm.list() == []
    # notes
    p = tmp_path / "notes.json"; p.write_text("{broken", encoding="utf-8")
    nm = NotesManager(path=p); assert nm.list() == []
    # habits
    p = tmp_path / "habits.json"; p.write_text("{broken", encoding="utf-8")
    hb = HabitTracker(path=p); assert hb.list() == []
    # calc history
    p = tmp_path / "h.json"; p.write_text("{broken", encoding="utf-8")
    calc = Calculator(path=p); assert calc.list() == []

def test_pretty_table_formats():
    s = pretty_table([[1, "a"], [2, "b"]], headers=["ID", "Nome"])
    lines = s.splitlines()
    assert lines[0] == "ID | Nome"
    assert re.match(r"^1\s+\|\s+a\s*$", lines[2])
    assert re.match(r"^2\s+\|\s+b\s*$", lines[3])

    assert pretty_table([], []) == "(vazio)"

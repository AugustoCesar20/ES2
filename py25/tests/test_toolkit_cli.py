import json
from unittest.mock import patch

import pytest

from toolkit_cli import (
    TaskManager, Task,
    NotesManager, Note,
    HabitTracker, Habit,
    Calculator, safe_eval,
    TextUtils,
    Converter,
    FileOrganizer,
    AddressBook,
    TicTacToe
)

# -----------------------------
# TaskManager tests
# -----------------------------
@pytest.fixture
def tmp_tasks_path(tmp_path):
    return tmp_path / "tasks.json"

def test_taskmanager_crud(tmp_tasks_path):
    tm = TaskManager(path=tmp_tasks_path)
    # Add task
    t = tm.add("Test", priority=2)
    assert t.id == 1
    assert t.title == "Test"
    # List
    tasks = tm.list()
    assert len(tasks) == 1
    # Edit
    ok = tm.edit(1, title="Updated", priority=5)
    assert ok
    assert tm.list()[0].title == "Updated"
    # Toggle
    assert tm.toggle(1) is True
    assert tm.list()[0].done is True
    # Delete
    assert tm.delete(1) is True
    assert len(tm.list()) == 0

# -----------------------------
# NotesManager tests
# -----------------------------
@pytest.fixture
def tmp_notes_path(tmp_path):
    return tmp_path / "notes.json"

def test_notesmanager_add_search_delete(tmp_notes_path):
    nm = NotesManager(path=tmp_notes_path)
    n = nm.add("Title", "Body text", tags=["tag1"])
    assert n.id == 1
    # List
    all_notes = nm.list()
    assert all_notes[0].title == "Title"
    # Search
    found = nm.search("body")
    assert n in found
    # Delete
    assert nm.delete(n.id) is True
    assert nm.list() == []

# -----------------------------
# HabitTracker tests
# -----------------------------
@pytest.fixture
def tmp_habits_path(tmp_path):
    return tmp_path / "habits.json"

def test_habittracker_add_mark_stats(tmp_habits_path):
    hb = HabitTracker(path=tmp_habits_path)
    hb.add("Run")
    hb.mark("Run")
    habits = hb.list()
    assert len(habits) == 1
    dones, _, _ = hb.monthly_stats("Run", 2099, 1)
    # Since the date won't match 2099-01, stats should be zero
    assert dones == 0

# -----------------------------
# Calculator tests
# -----------------------------
@pytest.fixture
def tmp_calc_path(tmp_path):
    return tmp_path / "calc_history.json"

def test_calculator_eval(tmp_calc_path):
    calc = Calculator(path=tmp_calc_path)
    res = calc.eval("2 + 2")
    assert res == 4
    with pytest.raises(NameError):
        calc.eval("open('file')")

# -----------------------------
# TextUtils tests
# -----------------------------
def test_textutils_methods():
    stats = TextUtils.word_stats("Hello world\nTest")
    assert stats["words"] == 3
    assert TextUtils.is_palindrome("A man, a plan, a canal, Panama")
    anags = TextUtils.anagrams("listen", ["silent", "enlist", "google"])
    assert "silent" in anags and "enlist" in anags

# -----------------------------
# Converter tests
# -----------------------------
def test_converter_json_csv(tmp_path):
    json_path = tmp_path / "data.json"
    csv_path = tmp_path / "data.csv"
    data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    json_path.write_text(json.dumps(data), encoding="utf-8")
    rows, _ = Converter.json_to_csv(json_path, csv_path)
    assert rows == 2
    rows2, _ = Converter.csv_to_json(csv_path, tmp_path / "out.json")
    assert rows2 == 2

# -----------------------------
# FileOrganizer tests
# -----------------------------
def test_file_organizer(tmp_path):
    f1 = tmp_path / "a.txt"; f1.write_text("x")
    f2 = tmp_path / "b.py"; f2.write_text("y")
    org = FileOrganizer(tmp_path)
    plan = org.plan()
    assert "txt" in plan and "py" in plan
    moves = org.apply(simulate=True)
    assert len(moves) == 2

# -----------------------------
# AddressBook tests
# -----------------------------
@pytest.fixture
def tmp_addr_db(tmp_path):
    return tmp_path / "addr.sqlite3"

def test_addressbook_add_list_delete(tmp_addr_db):
    ab = AddressBook(db_path=tmp_addr_db)
    cid = ab.add("John", "john@test.com", "1234")
    rows = ab.list()
    assert rows[0][0] == cid
    assert ab.delete(cid) is True
    assert ab.list() == []

# -----------------------------
# TicTacToe tests
# -----------------------------
def test_tictactoe_moves_winner():
    ttt = TicTacToe()
    assert ttt.move(0)
    assert ttt.move(1)
    # fill a winning pattern for X
    ttt.board = ["X","X","X","O","O"," "," "," "," "]
    assert ttt.winner() == "X"
    ttt.board = ["X","O","X","O","X","O","O","X","O"]
    assert ttt.winner() == "empate"

# -----------------------------
# safe_eval tests
# -----------------------------
def test_safe_eval_ok():
    assert safe_eval("sin(pi/2)") == pytest.approx(1)
    assert safe_eval("abs(-10)") == 10

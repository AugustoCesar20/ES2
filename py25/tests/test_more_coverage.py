import json
from pathlib import Path
from unittest.mock import patch
import pytest

from toolkit_cli import (
    TaskManager, NotesManager, HabitTracker, Calculator, TextUtils,
    Converter, FileOrganizer, AddressBook, TicTacToe, Timer, shutil as tk_shutil
)

def test_taskmanager_filters_orders_and_edges(tmp_path: Path):
    p = tmp_path / "tasks.json"
    tm = TaskManager(path=p)
    t1 = tm.add("A", priority=5, due="2099-01-10", tags=["x"])
    t2 = tm.add("B", priority=1, due="2099-01-01", tags=["y"])
    t3 = tm.add("C", priority=3)
    assert (t1.id, t2.id, t3.id) == (1, 2, 3)

    tm.toggle(3)  
    titles_not_done = [t.title for t in tm.list(show_done=False)]
    assert "C" not in titles_not_done

    assert [t.title for t in tm.list(order="due")][:2] == ["B", "A"]

    only_y = tm.list(tag="y")
    assert len(only_y) == 1 and only_y[0].title == "B"

    tm.edit(1, title=None, tags=["x", "z"])
    edited = next(t for t in tm.list() if t.id == 1)
    assert "z" in edited.tags

    assert tm.toggle(999) is False
    assert tm.delete(999) is False

def test_notesmanager_filters_and_delete_missing(tmp_path: Path):
    p = tmp_path / "notes.json"
    nm = NotesManager(path=p)
    n1 = nm.add("Python", "std lib only", tags=["dev","cli"])
    n2 = nm.add("Shopping", "buy apples", tags=["personal"])
    assert [n.title for n in nm.list(tag="dev")] == ["Python"]
    assert n1 in nm.search("cli") and n2 not in nm.search("cli")
    assert nm.delete(123456) is False

def test_habits_stats_true_false_and_missing(tmp_path: Path):
    p = tmp_path / "habits.json"
    hb = HabitTracker(path=p)
    hb.add("Read")
    hb.mark("Read", date="2099-01-01", value=True)
    hb.mark("Read", date="2099-01-02", value=False)
    d, t, perc = hb.monthly_stats("Read", 2099, 1)
    assert d == 1 and t == 2 and 49.0 < perc < 51.0
    assert hb.monthly_stats("Unknown", 2099, 1) == (0, 0, 0.0)

def test_calculator_history_and_safe_names(tmp_path: Path):
    p = tmp_path / "h.json"
    c = Calculator(path=p)
    assert c.eval("min(10, round(3.6))") == 4
    c.eval("2+3")
    assert c.list(1)[0][1] == 5
    with pytest.raises(NameError):
        c.eval("foobar + 1")

def test_textutils_stats_palindrome_anagrams():
    stats = TextUtils.word_stats("Hello\nWorld\n")
    assert stats["lines"] == 2 and stats["words"] == 2
    assert TextUtils.is_palindrome("abc") is False
    an = TextUtils.anagrams("Listen", ["Silent","LISTEN","tinsel!","enlists"])
    assert set(an) == {"Silent", "tinsel!"}


def test_tictactoe_invalid_moves_and_diagonal_win():
    t = TicTacToe()
    assert t.move(0) is True
    assert t.move(0) is False
    assert t.move(9) is False
    t2 = TicTacToe()
    t2.board = ["O","X"," ","X","O"," "," "," ","O"]
    assert t2.winner() == "O"

def test_timer_pomodoro_calls_countdown():
    called = []
    def fake_countdown(seconds): called.append(seconds)
    with patch.object(Timer, "countdown", side_effect=fake_countdown):
        Timer.pomodoro(work=1, short_break=2, cycles=2)
    assert called == [60, 120, 60]

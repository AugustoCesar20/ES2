"""
Toolkit CLI — Um utilitário de linha de comando com 10 funcionalidades, feito
para ser executado diretamente no terminal.

Objetivo
--------
Fornecer um conjunto de ferramentas simples, porém úteis, acessíveis por um
menu textual minimalista. Tudo usa apenas bibliotecas da stdlib do Python.

Persistência
------------
Alguns módulos usam arquivos no diretório "data" (criado automaticamente):
- tasks.json           -> Gerenciador de tarefas
- notes.json           -> Bloco de notas
- habits.json          -> Rastreador de hábitos
- calc_history.json    -> Histórico da calculadora
- addressbook.sqlite3  -> Agenda de contatos (SQLite)

Funcionalidades (10)
--------------------
1) Tasks      — CRUD de tarefas com prioridade, prazo e filtro
2) Notes      — Notas simples com tags e busca por texto
3) Habits     — Rastreamento diário de hábitos e estatísticas
4) Calc       — Calculadora com histórico e expressões seguras
5) Text       — Utilidades de texto (contagem, palíndromo, anagramas)
6) Convert    — Conversor JSON <-> CSV
7) Files      — Organizador de arquivos por extensão (com simulação)
8) Timer      — Relógio Pomodoro e timer simples
9) AddressBk  — Agenda de contatos (SQLite) com pesquisa
10) TicTacToe — Jogo da velha no terminal

Como usar
--------
$ python toolkit_cli.py

Requisitos: Python 3.8+
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
# import getpass
# import itertools
import json
import math
import os
# import random
import re
import shutil
import sqlite3
# import sys
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

APP_NAME = "Toolkit CLI"
DATA_DIR = Path(__file__).with_name("data")
DATA_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Utilidades gerais
# ---------------------------------------------------------------------------


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause(msg: str = "Pressione Enter para continuar...") -> None:
    try:
        input(msg)
    except (EOFError, KeyboardInterrupt):
        pass


def header(title: str) -> None:
    print("=" * 70)
    print(title)
    print("=" * 70)


def input_nonempty(prompt: str) -> str:
    while True:
        try:
            s = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEntrada cancelada.")
            return ""
        if s:
            return s
        print("Por favor, digite algo.")


def confirm(prompt: str = "Confirma? [s/N] ") -> bool:
    try:
        v = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return v in {"s", "sim", "y", "yes"}


def pretty_table(rows: List[List[Any]], headers: Optional[List[str]] = None) -> str:
    if not rows and not headers:
        return "(vazio)"
    cols = len(headers) if headers else len(rows[0]) if rows else 0
    widths = [0] * cols
    data = []
    if headers:
        data.append([str(h) for h in headers])
    for r in rows:
        data.append(["" if c is None else str(c) for c in r])
    for row in data:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = []
    if headers:
        hdr = " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(data[0]))
        lines.append(hdr)
        lines.append("-+-".join("-" * w for w in widths))
        body = data[1:]
    else:
        body = data
    for row in body:
        lines.append(" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# 1) Tasks — Gerenciador de tarefas
# ---------------------------------------------------------------------------


TASKS_PATH = DATA_DIR / "tasks.json"


@dataclass
class Task:
    id: int
    title: str
    priority: int = 3  # 1 alta, 5 baixa
    due: Optional[str] = None  # ISO date
    done: bool = False
    tags: List[str] = field(default_factory=list)

class TaskManager:
    def __init__(self, path: Path = TASKS_PATH) -> None:
        self.path = path
        self.tasks: List[Task] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.tasks = [Task(**t) for t in raw]
            except Exception:
                self.tasks = []
        else:
            self.tasks = []

    def _save(self) -> None:
        self.path.write_text(json.dumps([dataclasses.asdict(t) for t in self.tasks], ensure_ascii=False, indent=2), encoding="utf-8")

    def _next_id(self) -> int:
        return (max((t.id for t in self.tasks), default=0) + 1)

    def add(self, title: str, priority: int = 3, due: Optional[str] = None, tags: Optional[List[str]] = None) -> Task:
        t = Task(id=self._next_id(), title=title, priority=max(1, min(5, priority)), due=due, tags=tags or [])
        self.tasks.append(t)
        self._save()
        return t

    def list(self, *, show_done: bool = True, tag: Optional[str] = None, order: str = "priority") -> List[Task]:
        items = [t for t in self.tasks if (show_done or not t.done)]
        if tag:
            items = [t for t in items if tag in t.tags]
        if order == "priority":
            items.sort(key=lambda t: (t.done, t.priority, t.due or ""))
        elif order == "due":
            items.sort(key=lambda t: (t.done, t.due or "9999-12-31", t.priority))
        else:
            items.sort(key=lambda t: (t.done, t.id))
        return items

    def toggle(self, task_id: int) -> bool:
        for t in self.tasks:
            if t.id == task_id:
                t.done = not t.done
                self._save()
                return True
        return False

    def delete(self, task_id: int) -> bool:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        if len(self.tasks) != before:
            self._save()
            return True
        return False

    def edit(self, task_id: int, **fields: Any) -> bool:
        for t in self.tasks:
            if t.id == task_id:
                for k, v in fields.items():
                    if hasattr(t, k) and v is not None:
                        setattr(t, k, v)
                self._save()
                return True
        return False


# ---------------------------------------------------------------------------
# 2) Notes — Bloco de notas com busca
# ---------------------------------------------------------------------------
NOTES_PATH = DATA_DIR / "notes.json"

@dataclass
class Note:
    id: int
    title: str
    body: str
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: dt.datetime.now().isoformat(timespec="seconds"))

class NotesManager:
    def __init__(self, path: Path = NOTES_PATH) -> None:
        self.path = path
        self.notes: List[Note] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.notes = [Note(**n) for n in raw]
            except Exception:
                self.notes = []
        else:
            self.notes = []

    def _save(self) -> None:
        self.path.write_text(json.dumps([dataclasses.asdict(n) for n in self.notes], ensure_ascii=False, indent=2), encoding="utf-8")

    def _next_id(self) -> int:
        return (max((n.id for n in self.notes), default=0) + 1)

    def add(self, title: str, body: str, tags: Optional[List[str]] = None) -> Note:
        n = Note(id=self._next_id(), title=title, body=body, tags=tags or [])
        self.notes.append(n)
        self._save()
        return n

    def list(self, tag: Optional[str] = None) -> List[Note]:
        items = self.notes
        if tag:
            items = [n for n in items if tag in n.tags]
        return sorted(items, key=lambda n: n.created_at, reverse=True)

    def delete(self, note_id: int) -> bool:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        if len(self.notes) != before:
            self._save()
            return True
        return False

    def search(self, q: str) -> List[Note]:
        ql = q.lower()
        return [n for n in self.notes if ql in n.title.lower() or ql in n.body.lower() or any(ql in t.lower() for t in n.tags)]


# ---------------------------------------------------------------------------
# 3) Habits — Rastreador de hábitos
# ---------------------------------------------------------------------------
HABITS_PATH = DATA_DIR / "habits.json"

@dataclass
class Habit:
    name: str
    records: Dict[str, bool] = field(default_factory=dict)  # yyyy-mm-dd -> True

class HabitTracker:
    def __init__(self, path: Path = HABITS_PATH) -> None:
        self.path = path
        self.habits: Dict[str, Habit] = {}
        self._load()
    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.habits = {name: Habit(name=name, records=rec) for name, rec in raw.items()}
            except Exception:
                self.habits = {}
        else:
            self.habits = {}

    def _save(self) -> None:
        payload = {name: h.records for name, h in self.habits.items()}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, name: str) -> None:
        self.habits.setdefault(name, Habit(name))
        self._save()

    def mark(self, name: str, date: Optional[str] = None, value: bool = True) -> None:
        if name not in self.habits:
            self.habits[name] = Habit(name)
        if not date:
            date = dt.date.today().isoformat()
        self.habits[name].records[date] = value
        self._save()

    def list(self) -> List[Habit]:
        return sorted(self.habits.values(), key=lambda h: h.name)

    def monthly_stats(self, name: str, year: int, month: int) -> Tuple[int, int, float]:
        habit = self.habits.get(name)
        if not habit:
            return (0, 0, 0.0)
        days = [d for d in habit.records.keys() if d.startswith(f"{year:04d}-{month:02d}-")]
        dones = sum(1 for d in days if habit.records[d])
        total = len(days)
        perc = (dones / total * 100.0) if total else 0.0
        return (dones, total, perc)


# ---------------------------------------------------------------------------
# 4) Calc — Calculadora com histórico
# ---------------------------------------------------------------------------
CALC_HISTORY_PATH = DATA_DIR / "calc_history.json"

SAFE_NAMES = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
SAFE_NAMES.update({
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
})

def safe_eval(expr: str) -> Any:
    # Avaliador simples e "seguro" para expressões numéricas
    code = compile(expr, "<expr>", "eval")
    for name in code.co_names:
        if name not in SAFE_NAMES:
            raise NameError(f"uso de nome não permitido: {name}")
    return eval(code, {"__builtins__": {}}, SAFE_NAMES)

class Calculator:
    def __init__(self, path: Path = CALC_HISTORY_PATH) -> None:
        self.path = path
        self.history: List[Tuple[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                self.history = [(h[0], h[1]) for h in raw]
            except Exception:
                self.history = []
        else:
            self.history = []

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")

    def eval(self, expr: str) -> Any:
        res = safe_eval(expr)
        self.history.append((expr, res))
        self._save()
        return res

    def list(self, n: int = 20) -> List[Tuple[str, Any]]:
        return self.history[-n:]


# ---------------------------------------------------------------------------
# 5) Text — Utilitários de texto
# ---------------------------------------------------------------------------
class TextUtils:
    @staticmethod
    def word_stats(text: str) -> Dict[str, Any]:
        words = re.findall(r"\w+", text, flags=re.UNICODE)
        chars = len(text)
        lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
        uniques = len({w.lower() for w in words})
        return {"chars": chars, "lines": lines, "words": len(words), "unique": uniques}

    @staticmethod
    def is_palindrome(s: str) -> bool:
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", s).lower()
        return cleaned == cleaned[::-1]

    @staticmethod
    def anagrams(word: str, candidates: Iterable[str]) -> List[str]:
        def sig(w: str) -> str:
            return "".join(sorted(re.sub(r"[^a-z]", "", w.lower())))
        target = sig(word)
        return [c for c in candidates if sig(c) == target and c.lower() != word.lower()]


# ---------------------------------------------------------------------------
# 6) Convert — JSON <-> CSV
# ---------------------------------------------------------------------------
class Converter:
    @staticmethod
    def json_to_csv(json_path: Path, csv_path: Path) -> Tuple[int, int]:
        data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON deve conter uma lista de objetos")
        keys = sorted({k for item in data for k in item.keys()})
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for item in data:
                w.writerow({k: item.get(k, "") for k in keys})
        return (len(data), len(keys))

    @staticmethod
    def csv_to_json(csv_path: Path, json_path: Path) -> Tuple[int, int]:
        with open(csv_path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            data = list(r)
        Path(json_path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return (len(data), len(r.fieldnames or []))


# ---------------------------------------------------------------------------
# 7) Files — Organizador por extensão
# ---------------------------------------------------------------------------
class FileOrganizer:
    def __init__(self, base: Path) -> None:
        self.base = Path(base)

    def plan(self) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {}
        for p in self.base.iterdir():
            if p.is_file():
                ext = p.suffix.lower().lstrip(".") or "_sem_ext"
                mapping.setdefault(ext, []).append(p.name)
        return dict(sorted(mapping.items()))

    def apply(self, simulate: bool = True) -> List[Tuple[str, str]]:
        moves: List[Tuple[str, str]] = []
        for ext, files in self.plan().items():
            target = self.base / ext
            if not simulate:
                target.mkdir(exist_ok=True)
            for fname in files:
                src = self.base / fname
                dst = target / fname
                moves.append((str(src), str(dst)))
                if not simulate:
                    try:
                        shutil.move(str(src), str(dst))
                    except Exception as e:
                        print(f"Falha ao mover {src} -> {dst}: {e}")
        return moves


# ---------------------------------------------------------------------------
# 8) Timer — Pomodoro e timer simples
# ---------------------------------------------------------------------------
class Timer:
    @staticmethod
    def countdown(seconds: int) -> None:
        start = time.time()
        end = start + seconds
        try:
            while True:
                remaining = int(end - time.time())
                if remaining <= 0:
                    print("\r00:00", end="\n")
                    break
                m, s = divmod(remaining, 60)
                print(f"\r{m:02d}:{s:02d}", end="", flush=True)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nCancelado.")

    @staticmethod
    def pomodoro(work: int = 25, short_break: int = 5, cycles: int = 4) -> None:
        for i in range(1, cycles + 1):
            print(f"Ciclo {i}/{cycles}: Trabalho {work} min")
            Timer.countdown(work * 60)
            if i < cycles:
                print(f"Pausa curta {short_break} min")
                Timer.countdown(short_break * 60)
        print("Pomodoro concluído!")


# ---------------------------------------------------------------------------
# 9) Address Book — Agenda (SQLite)
# ---------------------------------------------------------------------------
ADDR_DB = DATA_DIR / "addressbook.sqlite3"

class AddressBook:
    def __init__(self, db_path: Path = ADDR_DB) -> None:
        self.db_path = db_path
        self._ensure()

    def _ensure(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add(self, name: str, email: str = "", phone: str = "") -> int:
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(
                "INSERT INTO contacts (name, email, phone, created_at) VALUES (?, ?, ?, ?)",
                (name, email, phone, dt.datetime.now().isoformat(timespec="seconds")),
            )
            return int(cur.lastrowid)

    def list(self, q: str = "") -> List[Tuple[int, str, str, str, str]]:
        sql = "SELECT id, name, email, phone, created_at FROM contacts"
        params: Tuple[Any, ...] = ()
        if q:
            sql += " WHERE name LIKE ? OR email LIKE ? OR phone LIKE ?"
            like = f"%{q}%"
            params = (like, like, like)
        sql += " ORDER BY created_at DESC"
        with sqlite3.connect(self.db_path) as con:
            return list(con.execute(sql, params))

    def delete(self, cid: int) -> bool:
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute("DELETE FROM contacts WHERE id = ?", (cid,))
            return cur.rowcount > 0


# ---------------------------------------------------------------------------
# 10) TicTacToe — Jogo da velha
# ---------------------------------------------------------------------------
class TicTacToe:
    def __init__(self) -> None:
        self.board = [" "] * 9
        self.current = "X"

    def draw(self) -> None:
        b = self.board
        print(f" {b[0]} | {b[1]} | {b[2]} ")
        print("---+---+---")
        print(f" {b[3]} | {b[4]} | {b[5]} ")
        print("---+---+---")
        print(f" {b[6]} | {b[7]} | {b[8]} ")

    def move(self, pos: int) -> bool:
        if 0 <= pos <= 8 and self.board[pos] == " ":
            self.board[pos] = self.current
            self.current = "O" if self.current == "X" else "X"
            return True
        return False

    def winner(self) -> Optional[str]:
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),  # linhas
            (0, 3, 6), (1, 4, 7), (2, 5, 8),  # colunas
            (0, 4, 8), (2, 4, 6),            # diagonais
        ]
        for a, b, c in wins:
            if self.board[a] != " " and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if " " not in self.board:
            return "empate"
        return None

    def play_cli(self) -> None:
        clear()
        header("Jogo da Velha — Use posições 1..9")
        self.draw()
        while True:
            try:
                v = input(f"Jogador {self.current}, posição (1-9) ou 'q' para sair: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSaindo...")
                return
            if v.lower() in {"q", "s", "sair"}:
                return
            if not v.isdigit() or not (1 <= int(v) <= 9):
                print("Entrada inválida.")
                continue
            if not self.move(int(v) - 1):
                print("Casa ocupada.")
                continue
            clear()
            self.draw()
            w = self.winner()
            if w:
                if w == "empate":
                    print("Deu velha! ✨")
                else:
                    print(f"Jogador '{w}' venceu! 🎉")
                pause()
                return


# ---------------------------------------------------------------------------
# Interfaces de cada módulo (menus simples)
# ---------------------------------------------------------------------------

def ui_tasks() -> None:
    tm = TaskManager()
    while True:
        clear()
        header("Tarefas")
        print("1) Listar\n2) Adicionar\n3) Alternar status\n4) Editar\n5) Excluir\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            tag = input("Filtro por tag (opcional): ").strip() or None
            order = input("Ordenar por [priority/due/id]: ").strip() or "priority"
            rows = [[t.id, "✔" if t.done else " ", t.title, t.priority, t.due or "", ",".join(t.tags)] for t in tm.list(tag=tag, order=order)]
            print(pretty_table(rows, ["ID", "OK", "Título", "Pri", "Prazo", "Tags"]))
            pause()
        elif op == "2":
            title = input_nonempty("Título: ")
            pri = input("Prioridade (1-5) [3]: ").strip() or "3"
            due = input("Prazo (yyyy-mm-dd) [vazio]: ").strip() or None
            tags = [t.strip() for t in input("Tags separadas por vírgula: ").split(",") if t.strip()]
            t = tm.add(title, int(pri), due, tags)
            print(f"Criado: {t}")
            pause()
        elif op == "3":
            tid = input("ID: ").strip()
            print("OK" if tm.toggle(int(tid)) else "Não encontrado")
            pause()
        elif op == "4":
            tid = int(input("ID: ").strip())
            title = input("Novo título (enter p/ manter): ").strip() or None
            pri = input("Nova prioridade (1-5, enter p/ manter): ").strip()
            due = input("Novo prazo (yyyy-mm-dd, enter p/ manter): ").strip()
            tags = input("Novas tags (csv, enter p/ manter): ").strip()
            ok = tm.edit(tid,
                         title=title,
                         priority=int(pri) if pri else None,
                         due=due or None,
                         tags=[t.strip() for t in tags.split(",")] if tags else None)
            print("Atualizado" if ok else "Não encontrado")
            pause()
        elif op == "5":
            tid = input("ID: ").strip()
            print("Excluído" if tm.delete(int(tid)) else "Não encontrado")
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_notes() -> None:
    nm = NotesManager()
    while True:
        clear()
        header("Notas")
        print("1) Listar\n2) Adicionar\n3) Excluir\n4) Buscar\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            tag = input("Filtro por tag (opcional): ").strip() or None
            rows = [[n.id, n.title, ",".join(n.tags), n.created_at] for n in nm.list(tag)]
            print(pretty_table(rows, ["ID", "Título", "Tags", "Criado"]))
            pause()
        elif op == "2":
            title = input_nonempty("Título: ")
            print("Digite o corpo (finalize com uma linha contendo apenas '::fim'):")
            body_lines = []
            while True:
                line = input()
                if line.strip() == "::fim":
                    break
                body_lines.append(line)
            tags = [t.strip() for t in input("Tags (csv): ").split(",") if t.strip()]
            n = nm.add(title, "\n".join(body_lines), tags)
            print(f"Criada nota {n.id}")
            pause()
        elif op == "3":
            nid = input("ID: ").strip()
            print("Excluída" if nm.delete(int(nid)) else "Não encontrada")
            pause()
        elif op == "4":
            q = input_nonempty("Buscar por: ")
            rows = [[n.id, n.title, textwrap.shorten(n.body, 60), ",".join(n.tags)] for n in nm.search(q)]
            print(pretty_table(rows, ["ID", "Título", "Prévia", "Tags"]))
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_habits() -> None:
    hb = HabitTracker()
    while True:
        clear()
        header("Hábitos")
        print("1) Listar\n2) Adicionar hábito\n3) Marcar hoje\n4) Estatísticas do mês\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            rows = []
            today = dt.date.today().isoformat()
            for h in hb.list():
                mark = "✔" if h.records.get(today) else " "
                rows.append([h.name, mark, len(h.records)])
            print(pretty_table(rows, ["Hábito", "Hoje", "Dias marcados"]))
            pause()
        elif op == "2":
            name = input_nonempty("Nome do hábito: ")
            hb.add(name)
            print("Adicionado.")
            pause()
        elif op == "3":
            name = input_nonempty("Hábito: ")
            hb.mark(name)
            print("Marcado para hoje.")
            pause()
        elif op == "4":
            name = input_nonempty("Hábito: ")
            year = int(input("Ano (YYYY): ").strip() or dt.date.today().year)
            month = int(input("Mês (1-12): ").strip() or dt.date.today().month)
            done, total, perc = hb.monthly_stats(name, year, month)
            print(f"Concluídos {done}/{total} ({perc:.1f}%)")
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_calc() -> None:
    calc = Calculator()
    while True:
        clear()
        header("Calculadora (digite 'hist' para ver histórico, '0' para voltar)")
        try:
            expr = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if expr in {"0", "q", "sair"}:
            return
        if expr == "hist":
            rows = [[e, r] for e, r in calc.list(50)]
            print(pretty_table(rows, ["Expressão", "Resultado"]))
            pause()
            continue
        try:
            res = calc.eval(expr)
            print("=", res)
        except Exception as e:
            print("Erro:", e)
        pause()


def ui_text() -> None:
    while True:
        clear()
        header("Texto — utilidades")
        print("1) Contagem de palavras/linhas/caracteres\n2) Verificar palíndromo\n3) Procurar anagramas\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            print("Cole/Digite o texto (fim com '::fim'):")
            lines = []
            while True:
                line = input()
                if line.strip() == "::fim":
                    break
                lines.append(line)
            stats = TextUtils.word_stats("\n".join(lines))
            rows = [[k, v] for k, v in stats.items()]
            print(pretty_table(rows, ["Métrica", "Valor"]))
            pause()
        elif op == "2":
            s = input_nonempty("Texto: ")
            print("É palíndromo?", "Sim" if TextUtils.is_palindrome(s) else "Não")
            pause()
        elif op == "3":
            word = input_nonempty("Palavra base: ")
            cand = input("Candidatos (csv): ").strip().split(",")
            print("Anagramas:", ", ".join(TextUtils.anagrams(word, [c.strip() for c in cand if c.strip()])) or "(nenhum)")
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_convert() -> None:
    while True:
        clear()
        header("Conversão JSON/CSV")
        print("1) JSON -> CSV\n2) CSV -> JSON\n0) Voltar")
        op = input("> ").strip()
        try:
            if op == "1":
                j = Path(input_nonempty("Arquivo JSON: "))
                c = Path(input_nonempty("Arquivo CSV destino: "))
                rows, cols = Converter.json_to_csv(j, c)
                print(f"Gravado CSV com {rows} linhas e {cols} colunas")
                pause()
            elif op == "2":
                c = Path(input_nonempty("Arquivo CSV: "))
                j = Path(input_nonempty("Arquivo JSON destino: "))
                rows, cols = Converter.csv_to_json(c, j)
                print(f"Gravado JSON com {rows} objetos e {cols} campos")
                pause()
            elif op == "0":
                return
            else:
                print("Opção inválida.")
                pause()
        except Exception as e:
            print("Erro:", e)
            pause()


def ui_files() -> None:
    while True:
        clear()
        header("Organizador de Arquivos")
        print("1) Ver plano\n2) Aplicar (mover)\n0) Voltar")
        op = input("> ").strip()
        if op not in {"1", "2", "0"}:
            print("Opção inválida.")
            pause()
            continue
        if op == "0":
            return
        base = Path(input_nonempty("Diretório base: "))
        org = FileOrganizer(base)
        if op == "1":
            plan = org.plan()
            rows = []
            for ext, files in plan.items():
                rows.append([ext, len(files), ", ".join(files[:5]) + (" ..." if len(files) > 5 else "")])
            print(pretty_table(rows, ["Extensão", "Qtd", "Exemplos"]))
            pause()
        else:
            print("Isso moverá arquivos para subpastas por extensão. Continuar?")
            if not confirm():
                continue
            moves = org.apply(simulate=False)
            print(f"Movidos {len(moves)} arquivos.")
            pause()


def ui_timer() -> None:
    while True:
        clear()
        header("Timer / Pomodoro")
        print("1) Timer simples (minutos)\n2) Pomodoro (25/5 x4)\n3) Pomodoro personalizado\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            mins = int(input("Minutos: ").strip())
            Timer.countdown(mins * 60)
            pause("[Fim] Pressione Enter...")
        elif op == "2":
            Timer.pomodoro()
            pause()
        elif op == "3":
            w = int(input("Trabalho (min): ").strip())
            sb = int(input("Pausa curta (min): ").strip())
            cyc = int(input("Ciclos: ").strip())
            Timer.pomodoro(w, sb, cyc)
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_addressbook() -> None:
    ab = AddressBook()
    while True:
        clear()
        header("Agenda de Contatos")
        print("1) Listar\n2) Adicionar\n3) Excluir\n0) Voltar")
        op = input("> ").strip()
        if op == "1":
            q = input("Filtro (nome/email/telefone): ").strip()
            rows = [[cid, name, email, phone, created] for (cid, name, email, phone, created) in ab.list(q)]
            print(pretty_table(rows, ["ID", "Nome", "Email", "Telefone", "Criado"]))
            pause()
        elif op == "2":
            name = input_nonempty("Nome: ")
            email = input("Email: ").strip()
            phone = input("Telefone: ").strip()
            cid = ab.add(name, email, phone)
            print(f"Contato #{cid} adicionado.")
            pause()
        elif op == "3":
            cid = int(input("ID: ").strip())
            print("Excluído" if ab.delete(cid) else "Não encontrado")
            pause()
        elif op == "0":
            return
        else:
            print("Opção inválida.")
            pause()


def ui_tictactoe() -> None:
    TicTacToe().play_cli()


# ---------------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------------
MENU_ITEMS = [
    ("Tarefas", ui_tasks),
    ("Notas", ui_notes),
    ("Hábitos", ui_habits),
    ("Calculadora", ui_calc),
    ("Texto", ui_text),
    ("Conversão JSON/CSV", ui_convert),
    ("Organizador de Arquivos", ui_files),
    ("Timer / Pomodoro", ui_timer),
    ("Agenda (SQLite)", ui_addressbook),
    ("Jogo da Velha", ui_tictactoe),
]


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--auto", choices=["tasks", "notes", "habits", "calc", "text", "convert", "files", "timer", "address", "tictactoe"], help="Abrir módulo diretamente", default=None)
    args = parser.parse_args(argv)

    if args.auto:
        mapping = {
            "tasks": ui_tasks,
            "notes": ui_notes,
            "habits": ui_habits,
            "calc": ui_calc,
            "text": ui_text,
            "convert": ui_convert,
            "files": ui_files,
            "timer": ui_timer,
            "address": ui_addressbook,
            "tictactoe": ui_tictactoe,
        }
        mapping[args.auto]()
        return 0

    while True:
        clear()
        header(f"{APP_NAME} — menu principal")
        for i, (label, _) in enumerate(MENU_ITEMS, start=1):
            print(f"{i}) {label}")
        print("0) Sair")
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté mais!")
            return 0
        if choice == "0":
            print("Até mais!")
            return 0
        if not choice.isdigit() or not (1 <= int(choice) <= len(MENU_ITEMS)):
            print("Opção inválida.")
            pause()
            continue
        _, fn = MENU_ITEMS[int(choice) - 1]
        fn()


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path
from queue import Queue
from typing import Dict, List

import tkinter as tk
from tkinter import filedialog, ttk, messagebox

from src.core.config import AppConfig
from src.core.models import EvaluationResult
from src.pipelines.batch import process_file
from src.services.db import init_db, list_evaluations, count_evaluations
from src.services.export_excel import default_report_path, export_to_excel


class GuiApp(tk.Tk):
    def __init__(self, cfg: AppConfig, db_conn) -> None:
        super().__init__()
        self.cfg = cfg
        self.db_conn = db_conn
        self.title("Ocena rozmow - GUI")
        self.geometry("1100x700")

        self._results: Dict[str, EvaluationResult] = {}
        self._row_map: Dict[str, EvaluationResult] = {}
        self._page = 1
        self._page_size = 50
        self._name_filter = ""
        self._pending_files: List[str] = []
        self._queue: Queue = Queue()

        self._build_ui()
        self._load_from_db()
        self._poll_queue()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=8)

        self.btn_select = ttk.Button(top, text="Wybierz pliki MP3", command=self._choose_files)
        self.btn_select.pack(side=tk.LEFT)

        self.btn_start = ttk.Button(top, text="Start oceny", command=self._start_processing)
        self.btn_start.pack(side=tk.LEFT, padx=8)

        self.btn_export = ttk.Button(top, text="Eksportuj do Excela", command=self._export_excel)
        self.btn_export.pack(side=tk.LEFT, padx=8)

        self.btn_refresh = ttk.Button(top, text="Odswiez z bazy", command=self._load_from_db)
        self.btn_refresh.pack(side=tk.LEFT, padx=8)

        self.btn_open_reports = ttk.Button(top, text="Otworz folder raportow", command=self._open_reports)
        self.btn_open_reports.pack(side=tk.LEFT, padx=8)

        self.status = ttk.Label(top, text="Gotowe")
        self.status.pack(side=tk.LEFT, padx=12)

        mid = ttk.Frame(self)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        filter_bar = ttk.Frame(mid)
        filter_bar.pack(fill=tk.X, pady=4)
        ttk.Label(filter_bar, text="Szukaj konsultanta:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_bar, textvariable=self.filter_var, width=30)
        self.filter_entry.pack(side=tk.LEFT, padx=6)
        self.btn_filter = ttk.Button(filter_bar, text="Filtruj", command=self._apply_filter)
        self.btn_filter.pack(side=tk.LEFT)
        self.btn_clear_filter = ttk.Button(filter_bar, text="Wyczysc", command=self._clear_filter)
        self.btn_clear_filter.pack(side=tk.LEFT, padx=6)

        columns = ("file", "status", "score", "stars", "profanity", "excerpt")
        self.tree = ttk.Treeview(mid, columns=columns, show="headings", height=12)
        self.tree.heading("file", text="Plik")
        self.tree.heading("status", text="Status")
        self.tree.heading("score", text="Wynik %")
        self.tree.heading("stars", text="Gwiazdki")
        self.tree.heading("profanity", text="Wulgaryzmy")
        self.tree.heading("excerpt", text="Cytat")
        self.tree.column("file", width=340)
        self.tree.column("status", width=120)
        self.tree.column("score", width=90, anchor=tk.CENTER)
        self.tree.column("stars", width=90, anchor=tk.CENTER)
        self.tree.column("profanity", width=110, anchor=tk.CENTER)
        self.tree.column("excerpt", width=260)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.tree.tag_configure("good", background="#C6EFCE")
        self.tree.tag_configure("mid", background="#FFEB9C")
        self.tree.tag_configure("low", background="#FFC7CE")

        scrollbar = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        pager = ttk.Frame(bottom)
        pager.pack(fill=tk.X)
        self.btn_prev = ttk.Button(pager, text="Poprzednia", command=self._prev_page)
        self.btn_prev.pack(side=tk.LEFT)
        self.btn_next = ttk.Button(pager, text="Nastepna", command=self._next_page)
        self.btn_next.pack(side=tk.LEFT, padx=6)
        self.page_label = ttk.Label(pager, text="Strona 1")
        self.page_label.pack(side=tk.LEFT, padx=10)

        left = ttk.Frame(bottom)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Podsumowanie").pack(anchor=tk.W)
        self.summary = tk.Text(left, height=10, wrap=tk.WORD)
        self.summary.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(bottom)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)

        ttk.Label(right, text="Szczegoly oceny").pack(anchor=tk.W)
        self.details = tk.Text(right, height=10, wrap=tk.WORD)
        self.details.pack(fill=tk.BOTH, expand=True)

        note = ttk.Label(
            self,
            text="Uwaga: wybrane pliki sa kopiowane do folderu incoming i tam przetwarzane.",
        )
        note.pack(side=tk.BOTTOM, pady=4)

    def _choose_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Wybierz pliki MP3",
            filetypes=[("MP3", "*.mp3")],
        )
        if not paths:
            return

        self._pending_files = list(paths)
        for p in self._pending_files:
            name = Path(p).name
            self._upsert_row(name, status="Oczekuje")
        self.status.config(text=f"Wybrano {len(paths)} plikow. Kliknij Start oceny.")

    def _process_files(self, paths: List[str]) -> None:
        self.cfg.input_dir.mkdir(parents=True, exist_ok=True)
        processed = 0

        for p in paths:
            src = Path(p)
            dst = self.cfg.input_dir / src.name
            try:
                shutil.copy2(src, dst)
                self._queue.put(("status", src.name, "W trakcie", None))
                result = process_file(dst, self.cfg, self.db_conn)
                if result is None:
                    self._queue.put(("status", src.name, "Pominieto", None))
                else:
                    self._queue.put(("result", src.name, result))
            except Exception as exc:
                self._queue.put(("error", src.name, str(exc)))

            processed += 1
            self._queue.put(("progress", processed, len(paths)))

        self._queue.put(("done", None, None))

    def _start_processing(self) -> None:
        if not self._pending_files:
            messagebox.showinfo("Start", "Brak wybranych plikow.")
            return
        self.status.config(text=f"Wybrano {len(self._pending_files)} plikow. Przetwarzanie...")
        self.btn_select.config(state=tk.DISABLED)
        self.btn_start.config(state=tk.DISABLED)
        t = threading.Thread(target=self._process_files, args=(self._pending_files,), daemon=True)
        t.start()

    def _on_select(self, _event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item_id = selected[0]
        r = self._row_map.get(item_id)
        if not r:
            key = self.tree.item(item_id, "values")[0]
            r = self._results.get(key)
        if not r:
            return
        self.details.delete("1.0", tk.END)
        self.details.insert(tk.END, "Oceny kategorii:\n")
        for k, v in r.score_breakdown.items():
            ev = r.evidence_breakdown.get(k, "") if r.evidence_breakdown else ""
            if ev:
                self.details.insert(tk.END, f"- {k}: {v:.2f} | Dowod: {ev}\n")
            else:
                self.details.insert(tk.END, f"- {k}: {v:.2f}\n")
        self.details.insert(tk.END, "\nTranskrypcja:\n")
        self.details.insert(tk.END, r.transcript)

    def _export_excel(self) -> None:
        if not self._results:
            messagebox.showinfo("Eksport", "Brak wynikow do eksportu.")
            return
        rows = list(self._results.values())
        report_path = default_report_path(self.cfg.reports_dir)
        export_to_excel(rows, report_path)
        messagebox.showinfo("Eksport", f"Zapisano: {report_path}")

    def _open_reports(self) -> None:
        try:
            self.cfg.reports_dir.mkdir(parents=True, exist_ok=True)
            os.startfile(str(self.cfg.reports_dir.resolve()))
        except Exception as exc:
            messagebox.showerror("Folder raportow", str(exc))

    def _load_from_db(self) -> None:
        self._results.clear()
        self._row_map.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

        offset = (self._page - 1) * self._page_size
        rows = list_evaluations(
            self.db_conn, limit=self._page_size, offset=offset, name_filter=self._name_filter
        )
        for r in rows:
            self._results[r.file_name] = r
            self._upsert_row(
                r.file_name,
                status="Zakonczono",
                score=f"{r.score_total * 100:.2f}",
                stars=str(r.stars),
                profanity="TAK" if r.profanity_flag else "NIE",
                excerpt=r.evidence_summary,
                result=r,
            )
        self._update_summary()
        total = count_evaluations(self.db_conn, name_filter=self._name_filter)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        self.page_label.config(text=f"Strona {self._page} / {total_pages}")

    def _poll_queue(self) -> None:
        while not self._queue.empty():
            msg = self._queue.get()
            kind = msg[0]

            if kind == "status":
                filename, status, _ = msg[1], msg[2], msg[3]
                self._upsert_row(filename, status=status)
            elif kind == "result":
                filename, result = msg[1], msg[2]
                self._results[filename] = result
                self._upsert_row(
                    filename,
                    status="Zakonczono",
                    score=f"{result.score_total * 100:.2f}",
                    stars=str(result.stars),
                    profanity="TAK" if result.profanity_flag else "NIE",
                    excerpt=result.evidence_summary,
                    result=result,
                )
                self._update_summary()
            elif kind == "error":
                filename, err = msg[1], msg[2]
                self._upsert_row(filename, status="Blad")
                self.status.config(text=f"Blad: {filename}: {err}")
            elif kind == "progress":
                done, total = msg[1], msg[2]
                self.status.config(text=f"Postep: {done}/{total}")
            elif kind == "done":
                self.status.config(text="Gotowe")
                self.btn_select.config(state=tk.NORMAL)
                self.btn_start.config(state=tk.NORMAL)
                self._pending_files = []

        self.after(200, self._poll_queue)

    def _upsert_row(
        self,
        filename: str,
        status: str | None = None,
        score: str | None = None,
        stars: str | None = None,
        profanity: str | None = None,
        excerpt: str | None = None,
        result: EvaluationResult | None = None,
    ) -> None:
        tag = None
        if score:
            try:
                s = float(score)
                if s >= 90.0:
                    tag = "good"
                elif s >= 60.0:
                    tag = "mid"
                else:
                    tag = "low"
            except ValueError:
                tag = None

        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            if values and values[0] == filename:
                new_values = (
                    filename,
                    status or values[1],
                    score or values[2],
                    stars or values[3],
                    profanity or values[4],
                    excerpt or values[5],
                )
                if tag:
                    self.tree.item(item, values=new_values, tags=(tag,))
                else:
                    self.tree.item(item, values=new_values)
                if result:
                    self._row_map[item] = result
                return

        if tag:
            item_id = self.tree.insert(
                "",
                tk.END,
                values=(filename, status or "", score or "", stars or "", profanity or "", excerpt or ""),
                tags=(tag,),
            )
        else:
            item_id = self.tree.insert(
                "",
                tk.END,
                values=(filename, status or "", score or "", stars or "", profanity or "", excerpt or ""),
            )
        if result:
            self._row_map[item_id] = result

    def _update_summary(self) -> None:
        if not self._results:
            return
        avg = sum(r.score_total for r in self._results.values()) / len(self._results)
        prof = sum(1 for r in self._results.values() if r.profanity_flag)
        self.summary.delete("1.0", tk.END)
        self.summary.insert(tk.END, f"Liczba ocen: {len(self._results)}\n")
        self.summary.insert(tk.END, f"Sredni wynik: {avg * 100:.2f}%\n")
        self.summary.insert(tk.END, f"Wulgaryzmy: {prof}\n")

    def _apply_filter(self) -> None:
        self._name_filter = self.filter_var.get().strip()
        self._page = 1
        self._load_from_db()

    def _clear_filter(self) -> None:
        self.filter_var.set("")
        self._name_filter = ""
        self._page = 1
        self._load_from_db()

    def _next_page(self) -> None:
        total = count_evaluations(self.db_conn, name_filter=self._name_filter)
        total_pages = max(1, (total + self._page_size - 1) // self._page_size)
        if self._page < total_pages:
            self._page += 1
            self._load_from_db()

    def _prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load_from_db()


def run_gui(cfg: AppConfig, db_conn) -> None:
    app = GuiApp(cfg, db_conn)
    app.mainloop()

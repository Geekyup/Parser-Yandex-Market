import asyncio
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional

from app import Fetcher, extract_products, load_cookies, save_to_excel
import config


class ParsingCancelled(Exception):
    pass


class YandexParserApp:
    """Главное окно приложения Yandex Market Parser."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Yandex Market Parser")
        self.root.geometry("720x600")
        self.root.minsize(640, 500)

        self.cookies_path: Optional[str] = None
        self.output_path: Optional[str] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.cancel_requested = False

        self._build_ui()

    # ─────────────────────────── UI ───────────────────────────

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # ── Поисковый запрос ──────────────────────────────────
        frm_query = ttk.LabelFrame(self.root, text="Поисковый запрос")
        frm_query.pack(fill="x", **pad)
        self.query_entry = ttk.Entry(frm_query, font=("Segoe UI", 10))
        self.query_entry.pack(fill="x", padx=8, pady=8)
        self.query_entry.insert(0, config.SEARCH_PARAMS.get("text", ""))

        # ── Параметры ─────────────────────────────────────────
        frm_params = ttk.LabelFrame(self.root, text="Параметры")
        frm_params.pack(fill="x", **pad)

        # Страницы
        row1 = ttk.Frame(frm_params)
        row1.pack(fill="x", padx=8, pady=4)
        ttk.Label(row1, text="Количество страниц:").pack(side="left")
        self.pages_var = tk.IntVar(value=config.DEFAULT_PAGES)
        ttk.Spinbox(row1, from_=1, to=100, width=6, textvariable=self.pages_var).pack(
            side="left", padx=8
        )

        # Параллельность
        ttk.Label(row1, text="Параллельных запросов:").pack(side="left", padx=(16, 0))
        self.concurrency_var = tk.IntVar(value=config.CONCURRENCY)
        ttk.Spinbox(row1, from_=1, to=10, width=4, textvariable=self.concurrency_var).pack(
            side="left", padx=8
        )

        # Задержка
        ttk.Label(row1, text="Задержка (сек):").pack(side="left", padx=(16, 0))
        self.delay_var = tk.DoubleVar(value=config.DELAY)
        ttk.Spinbox(
            row1, from_=0.0, to=5.0, increment=0.1, width=5, format="%.1f",
            textvariable=self.delay_var,
        ).pack(side="left", padx=8)

        # Cookies
        row2 = ttk.Frame(frm_params)
        row2.pack(fill="x", padx=8, pady=4)
        ttk.Label(row2, text="Файл cookies.txt:").pack(side="left")
        self.cookies_label = ttk.Label(
            row2, text="(не выбран — парсинг без авторизации)", foreground="#888"
        )
        self.cookies_label.pack(side="left", padx=8)
        ttk.Button(row2, text="Выбрать файл...", command=self._choose_cookies).pack(side="right")

        # Файл результата
        row3 = ttk.Frame(frm_params)
        row3.pack(fill="x", padx=8, pady=4)
        ttk.Label(row3, text="Куда сохранить результат:").pack(side="left")
        self.output_label = ttk.Label(
            row3,
            text=f"{config.OUTPUT_FILE} (в папке программы)",
            foreground="#888",
        )
        self.output_label.pack(side="left", padx=8)
        ttk.Button(row3, text="Выбрать...", command=self._choose_output).pack(side="right")

        # ── Кнопки управления ─────────────────────────────────
        frm_actions = ttk.Frame(self.root)
        frm_actions.pack(fill="x", **pad)
        self.start_btn = ttk.Button(
            frm_actions, text="▶ Начать парсинг", command=self._on_start
        )
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(
            frm_actions, text="■ Остановить", command=self._on_stop, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=8)
        self.open_file_btn = ttk.Button(
            frm_actions, text="Открыть результат", command=self._open_result, state="disabled"
        )
        self.open_file_btn.pack(side="right")

        # ── Прогресс ──────────────────────────────────────────
        frm_progress = ttk.Frame(self.root)
        frm_progress.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(frm_progress, mode="determinate")
        self.progress.pack(fill="x")
        self.status_label = ttk.Label(frm_progress, text="Готов к запуску.")
        self.status_label.pack(anchor="w", pady=(4, 0))

        # ── Лог ───────────────────────────────────────────────
        frm_log = ttk.LabelFrame(self.root, text="Журнал")
        frm_log.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(
            frm_log, height=12, state="disabled", wrap="word", font=("Consolas", 9)
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    # ─────────────────────── Диалоги ──────────────────────────

    def _choose_cookies(self):
        path = filedialog.askopenfilename(
            title="Выбери файл cookies.txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")],
        )
        if path:
            self.cookies_path = path
            self.cookies_label.config(text=os.path.basename(path), foreground="#000")

    def _choose_output(self):
        path = filedialog.asksaveasfilename(
            title="Куда сохранить результат",
            defaultextension=".xlsx",
            initialfile=config.OUTPUT_FILE,
            filetypes=[("Excel файл", "*.xlsx")],
        )
        if path:
            self.output_path = path
            self.output_label.config(text=os.path.basename(path), foreground="#000")

    def _open_result(self):
        path = self.output_path or config.OUTPUT_FILE
        if os.path.exists(path):
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])

    # ─────────────────── Запуск / остановка ───────────────────

    def _on_start(self):
        query = self.query_entry.get().strip()
        if not query:
            messagebox.showerror("Ошибка", "Введи поисковый запрос")
            return

        pages = self.pages_var.get()
        output = self.output_path or config.OUTPUT_FILE
        self.output_path = output

        self.cancel_requested = False
        self._set_running(True)
        self._clear_log()
        self.progress.config(maximum=pages, value=0)

        self.worker_thread = threading.Thread(
            target=self._run_worker,
            args=(query, pages, output),
            daemon=True,
        )
        self.worker_thread.start()

    def _on_stop(self):
        self.cancel_requested = True
        self._append_log("Останавливаю после текущей страницы...")

    # ─────────────────────── Рабочий поток ────────────────────

    def _run_worker(self, query: str, pages: int, output: str):
        try:
            count = asyncio.run(
                self._parse(query, pages, output)
            )
            self.root.after(0, self._on_finished, count, output)
        except ParsingCancelled:
            self.root.after(0, self._on_cancelled)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    async def _parse(self, query: str, pages: int, output: str) -> int:
        cookies: dict = {}
        if self.cookies_path:
            try:
                cookies = load_cookies(self.cookies_path)
                self._log(f"✅ Загружено кук: {len(cookies)}")
            except Exception as e:
                self._log(f"⚠️ Не удалось загрузить куки: {e}")

        params = {**config.SEARCH_PARAMS, "text": query}

        fetcher = Fetcher(
            cookies=cookies,
            concurrency=self.concurrency_var.get(),
            delay=self.delay_var.get(),
            timeout=config.TIMEOUT,
        )

        seen: set = set()
        products: list = []
        completed = 0

        def on_page(page: int, html) -> None:
            """Вызывается сразу после завершения каждой страницы — в asyncio-потоке."""
            nonlocal completed

            if self.cancel_requested:
                return

            completed += 1

            if html:
                new = []
                for p in extract_products(html):
                    key = p["product_id"] or p["name"]
                    if key not in seen:
                        seen.add(key)
                        new.append(p)
                products.extend(new)
                self._log(
                    f"✅ Страница {page}/{pages}: {len(new)} товаров "
                    f"(итого {len(products)})"
                )
            else:
                self._log(f"⚠️ Страница {page}/{pages}: не загружена")

            self.root.after(0, self._update_progress, completed, pages)

        # Все страницы стартуют параллельно, семафор внутри Fetcher
        # ограничивает одновременные запросы до concurrency
        await fetcher.fetch_pages(params, pages=pages, page_callback=on_page)

        if self.cancel_requested:
            raise ParsingCancelled()

        if not products:
            return 0

        save_to_excel(products, output)
        self._log(f"💾 Сохранено в {output}")
        return len(products)

    # ─────────────────────── Хелперы UI ───────────────────────

    def _log(self, msg: str):
        """Безопасный лог из любого потока."""
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg: str):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.status_label.config(text=msg)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _update_progress(self, current: int, total: int):
        self.progress.config(maximum=total, value=current)

    def _set_running(self, running: bool):
        self.start_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")
        self.open_file_btn.config(state="disabled")

    # ─────────────────── Коллбэки результата ──────────────────

    def _on_finished(self, count: int, path: str):
        self._set_running(False)
        self.open_file_btn.config(state="normal" if count else "disabled")
        self.status_label.config(text=f"Готово! Собрано товаров: {count}")
        if count:
            messagebox.showinfo("Готово", f"Собрано {count} товаров.\nФайл: {path}")
        else:
            messagebox.showwarning(
                "Нет данных",
                "Не удалось собрать ни одного товара.\nПроверь запрос и куки.",
            )

    def _on_cancelled(self):
        self._set_running(False)
        self.status_label.config(text="Остановлено пользователем.")

    def _on_error(self, error_msg: str):
        self._set_running(False)
        self.status_label.config(text="Произошла ошибка.")
        messagebox.showerror("Ошибка", f"Что-то пошло не так:\n{error_msg}")


# ──────────────────────────────────────────────────────────────


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    YandexParserApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
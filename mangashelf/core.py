from __future__ import annotations

import os
import re
import shutil
import sqlite3
import unicodedata
import uuid
from dataclasses import dataclass, replace
from pathlib import Path


def normalized_path(path: str | Path) -> str:
    return os.path.normcase(os.path.realpath(path))


def chinese_number(text: str) -> float | None:
    text = unicodedata.normalize("NFKC", text).replace("两", "二").replace("〇", "零")
    try:
        return float(text)
    except ValueError:
        pass
    digits = {c: i for i, c in enumerate("零一二三四五六七八九")}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    if not text or any(c not in digits and c not in units for c in text):
        return None
    if not any(c in units for c in text):
        return float("".join(str(digits[c]) for c in text))
    total = section = number = 0
    for c in text:
        if c in digits:
            number = digits[c]
        elif c == "万":
            total += (section + number) * 10000
            section = number = 0
        else:
            section += (number or 1) * units[c]
            number = 0
    return float(total + section + number)


def chapter_number(filename: str) -> float | None:
    stem = unicodedata.normalize("NFKC", Path(filename).stem)
    chinese = re.search(r"第\s*([\d零〇一二两三四五六七八九十百千万]+(?:\.\d+)?)\s*[话話章回集]", stem)
    if chinese:
        return chinese_number(chinese.group(1))
    english = re.search(r"(?:chapter|chap|ch|episode|ep)\s*[._#-]?\s*(\d+(?:\.\d+)?)", stem, re.I)
    if english:
        return float(english.group(1))
    volume = re.search(r"第\s*([\d零〇一二两三四五六七八九十百千万]+)\s*卷",stem)
    if volume:
        return chinese_number(volume.group(1))
    volume = re.search(r"vol(?:ume)?\s*[._#-]?\s*(\d+(?:\.\d+)?)",stem,re.I)
    if volume:
        return float(volume.group(1))
    bracket = re.search(r"[\[【]\s*(\d+(?:\.\d+)?)\s*[\]】]",stem)
    if bracket:
        return float(bracket.group(1))
    # Strip release-group / year annotations before the numeric fallback.
    clean = re.sub(r"\[[^\]]*\]|【[^】]*】|\([^)]*\)", " ", stem)
    leading = re.match(r"\s*(\d+(?:\.\d+)?)(?=\D|$)", clean)
    if leading:
        return float(leading.group(1))
    trailing = re.search(r"(?:^|[\s_\-])([0-9]+(?:\.[0-9]+)?)\s*$", clean)
    return float(trailing.group(1)) if trailing else None


def natural_key(text: str) -> tuple:
    return tuple((1, float(s)) if re.fullmatch(r"\d+(?:\.\d+)?", s) else (0, s.casefold())
                 for s in re.split(r"(\d+(?:\.\d+)?)", unicodedata.normalize("NFKC", text)))


def chapter_sort_key(path: Path | str) -> tuple:
    p = Path(path)
    number = chapter_number(p.name)
    special = bool(re.search(r"番外|特典|外传|外傳|extra|special|omake", p.stem, re.I))
    return (2 if special else (0 if number is not None else 1), number or 0, natural_key(str(p)))


def number_text(number: float | None) -> str:
    return "未识别" if number is None else f"{number:g}"


def reading_pages(page: int, total: int, double: bool = True) -> tuple[int, ...]:
    if total<=0:
        return ()
    page = max(0,min(page,total-1))
    start = page-page%2 if double else page
    return tuple(range(start,min(total,start+(2 if double else 1))))


@dataclass
class ScannedChapter:
    path: str
    title: str
    number: float | None
    pages: int
    size: int
    mtime: float


def pdf_files(folder: Path) -> list[Path]:
    result = []
    for directory, _, files in os.walk(folder, followlinks=False,
                                        onerror=lambda e: (_ for _ in ()).throw(e)):
        result.extend(Path(directory) / name for name in files if name.lower().endswith(".pdf"))
    return sorted(result, key=chapter_sort_key)


@dataclass
class ImportPlan:
    source: Path
    target: Path
    book_id: str | None


class ImportCancelled(Exception):
    pass


def discard_staging(staging: Path, comics_dir: Path):
    root = (comics_dir/".incoming").resolve()
    resolved = staging.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError("无效的导入临时目录")
    if resolved.exists():
        shutil.rmtree(resolved)


def prepare_copy(plan: ImportPlan, comics_dir: Path, cancelled=lambda:False,
                 progress=lambda current,total,name:None) -> Path:
    """Copy a complete folder snapshot in a worker, before touching a live book."""
    staging = comics_dir/".incoming"/uuid.uuid4().hex
    staging.mkdir(parents=True)
    try:
        files = []
        roots = ([plan.target] if plan.target.exists() else [])+[plan.source]
        for root in roots:
            for directory,dirs,names in os.walk(root,followlinks=False,
                                               onerror=lambda exc:(_ for _ in ()).throw(exc)):
                if cancelled():
                    raise ImportCancelled()
                base = Path(directory)
                for entry in [base/name for name in dirs+names]:
                    if entry.is_symlink() or entry.is_junction():
                        raise ValueError(f"请使用普通文件夹，不能导入符号链接或目录联接：{entry}")
                for name in names:
                    path = base/name
                    files.append((path,path.relative_to(root),path.stat().st_size))
        total = max(1,sum(size for _,_,size in files))
        copied = 0
        for source,relative,size in files:
            destination = staging/relative
            destination.parent.mkdir(parents=True,exist_ok=True)
            with source.open("rb") as src,destination.open("wb") as dst:
                while chunk := src.read(1024*1024):
                    if cancelled():
                        raise ImportCancelled()
                    dst.write(chunk)
                    copied += len(chunk)
                    progress(copied,total,relative.name)
            shutil.copystat(source,destination)
        if cancelled():
            raise ImportCancelled()
        return staging
    except BaseException:
        discard_staging(staging,comics_dir)
        raise


class Library:
    def __init__(self, data_dir: Path, comics_dir: Path | None = None):
        self.data_dir = data_dir = Path(data_dir).resolve()
        self.comics_dir = Path(comics_dir or data_dir/"comics").resolve()
        self.comics_dir.mkdir(parents=True,exist_ok=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        self.cover_dir = data_dir / "covers"
        self.cover_dir.mkdir(exist_ok=True)
        self.db = sqlite3.connect(data_dir / "library.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ignored_folders (folder TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, folder TEXT UNIQUE NOT NULL,
                cover TEXT, created REAL DEFAULT (unixepoch()), updated REAL DEFAULT (unixepoch()),
                last_read REAL, last_chapter TEXT
            );
            CREATE TABLE IF NOT EXISTS chapters (
                id TEXT PRIMARY KEY, book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                path TEXT NOT NULL, title TEXT NOT NULL, number REAL, position INTEGER NOT NULL,
                pages INTEGER NOT NULL, page INTEGER DEFAULT 0, completed INTEGER DEFAULT 0,
                size INTEGER, mtime REAL, UNIQUE(book_id,path)
            );
        """)
        if "source_folder" not in {row[1] for row in self.db.execute("PRAGMA table_info(books)")}:
            self.db.execute("ALTER TABLE books ADD COLUMN source_folder TEXT")
        self._relocate()

    def _relocate(self):
        """Keep managed books readable after moving the complete portable app."""
        settings = dict(self.db.execute("SELECT key,value FROM settings"))
        roots = [(settings.get("comics_dir"),self.comics_dir),
                 (settings.get("data_dir"),self.data_dir)]
        def relocated(value):
            if not value:
                return value
            path = Path(value)
            for previous,current in roots:
                if previous and path.is_relative_to(Path(previous)):
                    return normalized_path(current/path.relative_to(previous))
            return value
        with self.db:
            for row in self.db.execute("SELECT id,folder,cover FROM books").fetchall():
                self.db.execute("UPDATE books SET folder=?,cover=? WHERE id=?",
                                (relocated(row["folder"]),relocated(row["cover"]),row["id"]))
            for row in self.db.execute("SELECT id,path FROM chapters").fetchall():
                self.db.execute("UPDATE chapters SET path=? WHERE id=?",(relocated(row["path"]),row["id"]))
            for row in self.db.execute("SELECT folder FROM ignored_folders").fetchall():
                self.db.execute("UPDATE ignored_folders SET folder=? WHERE folder=?",(relocated(row[0]),row[0]))
            self.db.executemany("INSERT OR REPLACE INTO settings VALUES(?,?)",
                                [("data_dir",normalized_path(self.data_dir)),("comics_dir",normalized_path(self.comics_dir))])

    def books(self):
        return self.db.execute("""SELECT b.*, COUNT(c.id) chapter_count,
            COALESCE(SUM(c.pages),0) total_pages, COALESCE(SUM(c.completed),0) finished,
            COALESCE(SUM(CASE WHEN c.completed THEN c.pages ELSE c.page END),0) read_pages
            FROM books b LEFT JOIN chapters c ON c.book_id=b.id GROUP BY b.id
            ORDER BY COALESCE(b.last_read,b.updated) DESC""").fetchall()

    def book(self, book_id):
        return self.db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()

    def by_folder(self, folder):
        key = normalized_path(folder)
        return self.db.execute("SELECT * FROM books WHERE folder=? OR source_folder=?", (key,key)).fetchone()

    def plan_import(self, folder: Path) -> ImportPlan:
        source = Path(normalized_path(folder))
        root = Path(normalized_path(self.comics_dir))
        if source == source.parent:
            raise ValueError("请选择一本漫画的文件夹，不能导入整个磁盘。")
        if source == root or root.is_relative_to(source):
            raise ValueError("请选择一本漫画的文件夹；漫画库根目录请使用“扫描漫画库”。")
        old = self.by_folder(source)
        if source.is_relative_to(root):
            if source.is_relative_to(root/".incoming"):
                raise ValueError("不能导入临时目录")
            return ImportPlan(source,source,old["id"] if old else None)
        if old and Path(old["folder"]).is_relative_to(root):
            return ImportPlan(source,Path(old["folder"]),old["id"])
        name = source.name.lstrip(".") or "漫画"
        target = root/name
        index = 2
        while target.exists() or self.by_folder(target):
            target = root/f"{name} ({index})"
            index += 1
        return ImportPlan(source,target,old["id"] if old else None)

    def unregistered_folders(self):
        ignored = {row[0] for row in self.db.execute("SELECT folder FROM ignored_folders")}
        return [folder for folder in sorted(self.comics_dir.iterdir())
                if folder.is_dir() and not folder.name.startswith(".") and not folder.is_symlink()
                and not folder.is_junction() and not self.by_folder(folder)
                and normalized_path(folder) not in ignored]

    def commit_copy(self, plan, title, scanned, cover, staging):
        if plan.source == plan.target:
            return self.import_book(plan.target,title,scanned,cover,plan.book_id)
        if staging is None or not staging.resolve().is_relative_to((self.comics_dir/".incoming").resolve()):
            raise ValueError("导入副本尚未准备完成")
        converted = []
        for chapter in scanned:
            relative = Path(normalized_path(chapter.path)).relative_to(plan.source)
            stat = (staging/relative).stat()
            if stat.st_size != chapter.size or abs(stat.st_mtime-chapter.mtime)>.01:
                raise ValueError("扫描后源文件发生变化，请重新导入。")
            converted.append(replace(chapter,path=str(plan.target/relative)))
        backup = self.comics_dir/".incoming"/uuid.uuid4().hex
        had_target = plan.target.exists()
        if had_target:
            plan.target.rename(backup)
        installed = False
        try:
            staging.rename(plan.target)
            installed = True
            book_id = self.import_book(plan.target,title,converted,cover,plan.book_id,str(plan.source))
        except BaseException:
            if installed:
                plan.target.rename(staging)
            if had_target:
                backup.rename(plan.target)
            raise
        if had_target:
            try:
                discard_staging(backup,self.comics_dir)
            except OSError:
                pass  # A locked backup is harmless; the live book and DB are already committed.
        return book_id

    def chapters(self, book_id):
        return self.db.execute("SELECT * FROM chapters WHERE book_id=? ORDER BY position", (book_id,)).fetchall()

    def import_book(self, folder: Path, title: str, scanned: list[ScannedChapter], cover: bytes | None,
                    existing_id=None, source_folder=None):
        if not title.strip():
            raise ValueError("漫画名称不能为空")
        if not scanned:
            raise ValueError("文件夹中没有可读取的 PDF")
        folder_key = normalized_path(folder)
        old = self.book(existing_id) if existing_id else self.by_folder(folder)
        book_id = old["id"] if old else uuid.uuid4().hex
        cover_path = self.cover_dir / f"{book_id}.png"
        # A failed cover write must not commit a partially imported book.
        if cover:
            temp = cover_path.with_suffix(".tmp")
            temp.write_bytes(cover)
            temp.replace(cover_path)
        with self.db:
            if old and old["folder"] != folder_key:
                for row in self.chapters(book_id):
                    relative = Path(row["path"]).relative_to(old["folder"])
                    self.db.execute("UPDATE chapters SET path=? WHERE id=?",(normalized_path(Path(folder_key)/relative),row["id"]))
            self.db.execute("""INSERT INTO books(id,title,folder,cover,source_folder) VALUES(?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET title=excluded.title,folder=excluded.folder,
                source_folder=COALESCE(excluded.source_folder,books.source_folder),
                cover=COALESCE(excluded.cover,books.cover),updated=unixepoch()""",
                (book_id,title.strip(),folder_key,str(cover_path) if cover else None,source_folder))
            self.db.execute("DELETE FROM ignored_folders WHERE folder=?",(folder_key,))
            # Keep old chapters (including unavailable files) and their progress.
            # They remain visible so a temporary disk disconnect never erases reading history.
            incoming = set()
            for position, chapter in enumerate(scanned):
                key = normalized_path(chapter.path)
                incoming.add(key)
                self.db.execute("""INSERT INTO chapters
                    (id,book_id,path,title,number,position,pages,size,mtime) VALUES(?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(book_id,path) DO UPDATE SET number=excluded.number,
                    position=excluded.position,pages=excluded.pages,size=excluded.size,mtime=excluded.mtime,
                    page=MIN(chapters.page,excluded.pages-1)""",
                    (uuid.uuid4().hex,book_id,key,chapter.title,chapter.number,position,
                     chapter.pages,chapter.size,chapter.mtime))
            tail = len(scanned)
            for row in self.chapters(book_id):
                if row["path"] not in incoming:
                    self.db.execute("UPDATE chapters SET position=? WHERE id=?", (tail,row["id"]))
                    tail += 1
        return book_id

    def rename(self, book_id, title):
        if not title.strip():
            raise ValueError("漫画名称不能为空")
        with self.db:
            self.db.execute("UPDATE books SET title=?,updated=unixepoch() WHERE id=?", (title.strip(),book_id))

    def progress(self, chapter_id, page, completed=False):
        row = self.db.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
        if not row:
            return
        page = max(0,min(page,row["pages"]-1))
        with self.db:
            self.db.execute("UPDATE chapters SET page=?,completed=MAX(completed,?) WHERE id=?",
                            (page,int(completed),chapter_id))
            self.db.execute("UPDATE books SET last_chapter=?,last_read=unixepoch() WHERE id=?",
                            (chapter_id,row["book_id"]))

    def remove(self, book_id):
        with self.db:
            row = self.book(book_id)
            if row:
                self.db.execute("INSERT OR IGNORE INTO ignored_folders VALUES(?)",(row["folder"],))
            self.db.execute("DELETE FROM books WHERE id=?", (book_id,))

    def reorder(self, book_id, ids):
        with self.db:
            for i, chapter_id in enumerate(ids):
                self.db.execute("UPDATE chapters SET position=? WHERE id=? AND book_id=?", (i,chapter_id,book_id))

    def close(self):
        self.db.close()

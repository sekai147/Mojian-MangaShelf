"""Create and verify real library files for the isolated installer smoke test."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pymupdf as fitz
from mangashelf.core import Library,ScannedChapter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","verify"])
    parser.add_argument("app_root",type=Path)
    args = parser.parse_args()
    root = args.app_root.resolve()
    allowed = Path(__file__).resolve().parents[1]/"test-output"
    if root==allowed or not root.is_relative_to(allowed):
        raise ValueError("Installer test data must stay inside test-output")
    manifest = root.parent/"preserved-files.json"
    if args.action=="prepare":
        folder = root/"comics"/"安装验证漫画"
        folder.mkdir(parents=True)
        pdf = folder/"第1话.pdf"
        with fitz.open() as doc:
            for index in range(3):
                page = doc.new_page(width=300,height=420)
                page.insert_text((30,50),f"INSTALLER TEST / PAGE {index+1}")
            doc.save(pdf)
        library = Library(root/"data",root/"comics")
        stat = pdf.stat()
        book_id = library.import_book(folder,"安装验证 · 自定义名称",
            [ScannedChapter(str(pdf),pdf.stem,1,3,stat.st_size,stat.st_mtime)],None)
        library.progress(library.chapters(book_id)[0]["id"],1)
        library.close()
        marker = root/"data"/"请保留.txt"
        marker.write_text("User-created data must survive upgrades and uninstall.",encoding="utf-8")
        paths = [pdf,marker,root/"data"/"library.sqlite3"]
        hashes = {str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        manifest.write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding="utf-8")
    else:
        for relative,expected in json.loads(manifest.read_text(encoding="utf-8")).items():
            path = root/relative
            assert path.is_file(),f"Missing user file: {relative}"
            assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,f"Changed user file: {relative}"
        with sqlite3.connect(root/"data"/"library.sqlite3") as db:
            assert db.execute("SELECT title FROM books").fetchone()[0]=="安装验证 · 自定义名称"
            assert db.execute("SELECT page FROM chapters").fetchone()[0]==1
    print(f"Installer data {args.action}: OK")


if __name__ == "__main__":
    main()

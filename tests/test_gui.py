"""Real PDF and Qt integration checks; all library data stays in test-output."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import time
import unittest
import shutil
from pathlib import Path

import pymupdf as fitz
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from mangashelf.app import MainWindow, ImportDialog, BookDialog

ROOT = Path(__file__).resolve().parent.parent/"test-output"


def make_pdf(path, chapter, pages=3):
    with fitz.open() as doc:
        for i in range(pages):
            page = doc.new_page(width=600,height=840)
            page.draw_rect(page.rect,color=None,fill=(.96,.95,.90))
            page.insert_text((40,55),"THE QUIET FOREST",fontsize=27,color=(.17,.28,.21))
            page.insert_text((40,84),f"CHAPTER {chapter:02}  /  PAGE {i+1:02}",fontsize=12)
            for index,(x,y,w,h) in enumerate([(40,110,520,270),(40,400,245,325),(305,400,255,325)]):
                rect = fitz.Rect(x,y,x+w,y+h)
                page.draw_rect(rect,color=(.18,.25,.21),fill=(.77+index*.04,.82+index*.03,.72+index*.04),width=2)
                for j in range(7):
                    px = x+22+j*(w-44)/7
                    page.draw_line((px,y+h-10),(px+12,y+35+j%3*22),color=(.30,.41,.31),width=5)
                page.draw_circle((x+w*.7,y+h*.2),min(w,h)*.08,color=None,fill=(.98,.96,.81))
            page.insert_text((40,785),"A sample story for testing your local manga reader.",fontsize=11)
        doc.save(path)


def wait_until(predicate, timeout=12):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        QApplication.processEvents()
        if predicate():
            return True
        QTest.qWait(25)
    return False


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        from mangashelf.app import STYLE, load_fonts
        load_fonts()
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)
        ROOT.mkdir(exist_ok=True)

    def test_import_reader_and_restart(self):
        data = ROOT/"library"
        if data.exists():
            shutil.rmtree(data)
        folder = ROOT/"林间来信"
        folder.mkdir(exist_ok=True)
        for i in [10,2,1]:
            make_pdf(folder/f"第{i}话.pdf",i)
        (folder/"损坏.pdf").write_bytes(b"this is not a pdf")
        with fitz.open() as doc:
            doc.new_page()
            doc.save(folder/"加密.pdf",encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw="owner",user_pw="secret")
        window = MainWindow(data)
        window.reader.view_mode.setCurrentIndex(1)
        window.show()
        QTest.qWait(100)
        dialog = ImportDialog(window.library,folder,window)
        dialog.show()
        self.assertTrue(wait_until(lambda:dialog.result_data is not None))
        self.assertEqual(len(dialog.result_data[0]),3)
        self.assertEqual(len(dialog.result_data[2]),2)
        self.assertEqual([c.number for c in dialog.result_data[0]],[1,2,10])
        dialog.name.setText("林间来信 · 自定义名称")
        self.assertTrue(wait_until(lambda:not dialog.worker.isRunning()))
        dialog.commit()
        self.assertTrue(wait_until(lambda:dialog.result()==QDialog.DialogCode.Accepted and not dialog.isVisible()))
        self.assertEqual(dialog.result(),QDialog.DialogCode.Accepted)
        book_id = dialog.book_id
        managed = Path(window.library.book(book_id)["folder"])
        self.assertTrue(managed.is_relative_to(window.library.comics_dir))
        self.assertNotEqual(managed,folder)
        self.assertTrue((managed/"第1话.pdf").is_file())
        # Reading must work with the original source folder removed.
        original_backup = folder.with_name(folder.name+"-source-away")
        folder.rename(original_backup)
        window.library_page.refresh()
        QTest.qWait(150)
        window.grab().save(str(ROOT/"bookshelf.png"))
        detail = BookDialog(window,book_id)
        detail.show()
        QTest.qWait(100)
        detail.grab().save(str(ROOT/"chapters.png"))
        detail.accept()
        window.start_reading(book_id)
        self.assertTrue(wait_until(lambda:window.reader.image.pixmap() is not None and not window.reader.image.pixmap().isNull()))
        window.reader.go_page(1)
        chapter_id = window.library.chapters(book_id)[0]["id"]
        self.assertTrue(wait_until(lambda:window.library.chapters(book_id)[0]["page"]==1))
        window.grab().save(str(ROOT/"reader.png"))
        window.reader.mode.setCurrentIndex(1)
        self.assertTrue(wait_until(lambda:not window.reader.timer.isActive() and not window.reader.tasks))
        window.reader.go_page(2)
        self.assertTrue(wait_until(lambda:window.library.chapters(book_id)[0]["completed"]==1))
        window.reader.move(1)
        self.assertEqual(window.reader.index,1)
        self.assertTrue(wait_until(lambda:window.library.book(book_id)["last_chapter"]!=chapter_id))
        original_backup.rename(folder)
        # The second import updates rather than duplicating the book.
        again = ImportDialog(window.library,folder,window)
        again.show()
        self.assertEqual(again.name.text(),"林间来信 · 自定义名称")
        self.assertTrue(wait_until(lambda:again.result_data is not None and not again.worker.isRunning()))
        again.commit()
        self.assertTrue(wait_until(lambda:again.result()==QDialog.DialogCode.Accepted and not again.isVisible()))
        self.assertEqual(len(window.library.books()),1)
        self.assertEqual(window.library.chapters(book_id)[0]["page"],2)
        # Broken source files display an error and never advance saved progress.
        row = window.library.chapters(book_id)[1]
        missing = Path(row["path"])
        renamed = missing.with_suffix(".hidden")
        missing.replace(renamed)
        try:
            window.reader.go_page(1)
            self.assertTrue(wait_until(lambda:"暂时无法打开此页" in window.reader.image.text()))
            self.assertEqual(window.library.chapters(book_id)[1]["page"],0)
        finally:
            renamed.replace(missing)
        window.close()
        window2 = MainWindow(data)
        self.assertEqual(window2.library.book(book_id)["title"],"林间来信 · 自定义名称")
        self.assertEqual(window2.library.chapters(book_id)[0]["page"],2)
        window2.close()

    def test_direct_comics_folder_discovery_and_relocation(self):
        import uuid
        home = ROOT/("portable-"+uuid.uuid4().hex)
        library_root = home/"comics"
        folder = library_root/"直接放入的漫画"
        folder.mkdir(parents=True)
        make_pdf(folder/"002.pdf",2)
        make_pdf(folder/"001.pdf",1)
        window = MainWindow(home/"data",library_root)
        window.show()
        window.scan_library(only_new=True)
        self.assertEqual(len(window.library.books()),1)
        book_id = window.library.books()[0]["id"]
        self.assertEqual(window.library.book(book_id)["title"],folder.name)
        self.assertEqual([c["number"] for c in window.library.chapters(book_id)],[1,2])
        window.library.rename(book_id,"直接导入后改名")
        window.library.progress(window.library.chapters(book_id)[0]["id"],1)
        window.scan_library()
        self.assertEqual(len(window.library.books()),1)
        self.assertEqual(window.library.book(book_id)["title"],"直接导入后改名")
        window.close()
        moved = home.with_name(home.name+"-moved")
        home.rename(moved)
        window = MainWindow(moved/"data",moved/"comics")
        window.show()
        row = window.library.chapters(book_id)[0]
        self.assertTrue(Path(row["path"]).is_file())
        self.assertTrue(Path(window.library.book(book_id)["cover"]).is_file())
        self.assertEqual(row["page"],1)
        window.start_reading(book_id)
        self.assertTrue(wait_until(lambda:window.reader.image.pixmap() is not None and not window.reader.image.pixmap().isNull()))
        window.close()

    def test_cancel_import_is_clean(self):
        window = MainWindow(ROOT/"cancel-library")
        folder = ROOT/"cancel-fixture"
        folder.mkdir(exist_ok=True)
        make_pdf(folder/"001.pdf",1)
        dialog = ImportDialog(window.library,folder,window)
        dialog.show()
        QApplication.processEvents()
        dialog.reject()
        self.assertTrue(wait_until(lambda:not dialog.isVisible()))
        self.assertFalse(window.library.books())
        window.close()


if __name__ == "__main__":
    unittest.main()

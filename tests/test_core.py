import uuid
import shutil
import unittest
from unittest.mock import patch
from pathlib import Path

from mangashelf.core import (Library, ScannedChapter, chapter_number, chapter_sort_key,
                             chinese_number, prepare_copy, ImportCancelled, reading_pages)


class SortingTests(unittest.TestCase):
    def test_recognizes_chinese_english_and_decimal_numbers(self):
        for filename,number in [("第十二话.pdf",12),("第两百零三章.pdf",203),
                                ("Chapter 010.pdf",10),("ch. 2.5.pdf",2.5),
                                ("００３.pdf",3),("[汉化组][015] 漫画.pdf",15),
                                ("第1卷 第十二话.pdf",12),("Vol 01 Chapter 20.pdf",20),
                                ("我的漫画 102.pdf",102),("001 开始.pdf",1)]:
            with self.subTest(filename=filename):
                self.assertEqual(chapter_number(filename),number)
        self.assertIsNone(chapter_number("序章.pdf"))

    def test_numeric_sort_and_extras(self):
        names = ["第10话.pdf","番外1.pdf","第2话.pdf","第1话.pdf","第2.5话.pdf"]
        self.assertEqual(sorted(names,key=chapter_sort_key),
                         ["第1话.pdf","第2话.pdf","第2.5话.pdf","第10话.pdf","番外1.pdf"])

    def test_chinese_numerals(self):
        for text,value in [("十",10),("一百零二",102),("一万零三",10003),("二〇二",202)]:
            self.assertEqual(chinese_number(text),value)

    def test_spread_alignment_and_odd_final_page(self):
        self.assertEqual(reading_pages(0,5),(0,1))
        self.assertEqual(reading_pages(1,5),(0,1))
        self.assertEqual(reading_pages(2,5),(2,3))
        self.assertEqual(reading_pages(99,5),(4,))
        self.assertEqual(reading_pages(0,1),(0,))
        self.assertEqual(reading_pages(2,5,False),(2,))
        self.assertEqual(reading_pages(0,0),())


class LibraryTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parent.parent/"test-output"
        test_root.mkdir(exist_ok=True)
        self.root = test_root/("core-"+uuid.uuid4().hex)
        self.root.mkdir()
        self.library = Library(self.root/"data")
        self.folder = self.root/"漫画"
        self.folder.mkdir()
        self.scanned = [ScannedChapter(str(self.folder/f"第{i}话.pdf"),f"第{i}话",i,5,50,1) for i in [1,2]]

    def tearDown(self):
        self.library.close()
        shutil.rmtree(self.root)

    def test_import_rename_refresh_and_progress_persist(self):
        book_id = self.library.import_book(self.folder,"漫画",self.scanned,None)
        chapters = self.library.chapters(book_id)
        self.library.progress(chapters[0]["id"],3)
        self.library.rename(book_id,"自定义书名")
        same = self.library.import_book(self.folder,"自定义书名",self.scanned,None)
        self.assertEqual(book_id,same)
        self.assertEqual(len(self.library.books()),1)
        self.assertEqual(self.library.chapters(book_id)[0]["page"],3)
        self.library.close()
        self.library = Library(self.root/"data")
        self.assertEqual(self.library.book(book_id)["title"],"自定义书名")
        self.assertEqual(self.library.book(book_id)["last_chapter"],chapters[0]["id"])

    def test_refresh_does_not_erase_unavailable_chapters(self):
        book_id = self.library.import_book(self.folder,"漫画",self.scanned,None)
        self.library.progress(self.library.chapters(book_id)[1]["id"],2)
        self.library.import_book(self.folder,"漫画",self.scanned[:1],None)
        self.assertEqual(len(self.library.chapters(book_id)),2)
        self.assertEqual(self.library.chapters(book_id)[1]["page"],2)

    def test_reorder_and_remove_preserve_source(self):
        source = self.folder/"第1话.pdf"
        source.write_bytes(b"source")
        book_id = self.library.import_book(self.folder,"漫画",self.scanned,None)
        ids = [row["id"] for row in self.library.chapters(book_id)]
        self.library.reorder(book_id,list(reversed(ids)))
        self.assertEqual(self.library.chapters(book_id)[0]["id"],ids[1])
        self.library.remove(book_id)
        self.assertTrue(source.is_file())
        self.assertFalse(self.library.chapters(book_id))

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError):
            self.library.import_book(self.folder," ",self.scanned,None)

    def real_chapters(self, folder=None):
        folder = folder or self.folder
        result = []
        for name in ["第1话.pdf","子章节/第2话.pdf"]:
            file = folder/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(b"original PDF content "+name.encode())
            stat = file.stat()
            result.append(ScannedChapter(str(file),file.stem,chapter_number(file.name),5,stat.st_size,stat.st_mtime))
        (folder/"说明.txt").write_text("whole folder",encoding="utf-8")
        return result

    def copy_import(self, folder, scanned, title="漫画"):
        plan = self.library.plan_import(folder)
        staged = prepare_copy(plan,self.library.comics_dir) if plan.source!=plan.target else None
        return self.library.commit_copy(plan,title,scanned,None,staged)

    def test_copy_is_independent_preserves_structure_and_progress(self):
        scanned = self.real_chapters()
        # Migrate an existing v1 linked book without losing its chapter IDs or progress.
        book_id = self.library.import_book(self.folder,"改过的书名",scanned,None)
        chapter_id = self.library.chapters(book_id)[0]["id"]
        self.library.progress(chapter_id,3)
        self.assertEqual(self.copy_import(self.folder,scanned,"改过的书名"),book_id)
        managed = Path(self.library.book(book_id)["folder"])
        self.assertTrue(managed.is_relative_to(self.library.comics_dir))
        self.assertTrue((managed/"子章节/第2话.pdf").is_file())
        self.assertTrue((managed/"说明.txt").is_file())
        shutil.rmtree(self.folder)
        self.assertTrue(Path(self.library.chapters(book_id)[0]["path"]).is_file())
        self.assertEqual(self.library.chapters(book_id)[0]["id"],chapter_id)
        self.assertEqual(self.library.chapters(book_id)[0]["page"],3)

    def test_repeat_source_and_same_name_collision(self):
        scanned = self.real_chapters()
        first = self.copy_import(self.folder,scanned)
        self.assertEqual(self.copy_import(self.folder,scanned),first)
        other = self.root/"another"/self.folder.name
        other_scanned = self.real_chapters(other)
        second = self.copy_import(other,other_scanned)
        self.assertNotEqual(first,second)
        self.assertNotEqual(self.library.book(first)["folder"],self.library.book(second)["folder"])
        self.assertEqual(len(self.library.books()),2)

    def test_failed_copy_and_cancel_leave_no_partial_book(self):
        self.real_chapters()
        plan = self.library.plan_import(self.folder)
        with patch("mangashelf.core.shutil.copystat",side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                prepare_copy(plan,self.library.comics_dir)
        self.assertFalse(plan.target.exists())
        self.assertFalse(list((self.library.comics_dir/".incoming").iterdir()))
        with self.assertRaises(ImportCancelled):
            prepare_copy(plan,self.library.comics_dir,cancelled=lambda:True)
        self.assertFalse(list((self.library.comics_dir/".incoming").iterdir()))
        self.assertFalse(self.library.books())
        self.assertTrue((self.folder/"第1话.pdf").is_file())

    def test_failed_database_update_restores_existing_copy(self):
        scanned = self.real_chapters()
        book_id = self.copy_import(self.folder,scanned)
        target = Path(self.library.book(book_id)["folder"])
        before = (target/"第1话.pdf").read_bytes()
        source = self.folder/"第1话.pdf"
        source.write_bytes(b"replacement")
        stat = source.stat()
        scanned[0] = ScannedChapter(str(source),source.stem,1,5,stat.st_size,stat.st_mtime)
        plan = self.library.plan_import(self.folder)
        staged = prepare_copy(plan,self.library.comics_dir)
        with patch.object(self.library,"import_book",side_effect=RuntimeError("database failure")):
            with self.assertRaises(RuntimeError):
                self.library.commit_copy(plan,"漫画",scanned,None,staged)
        self.assertEqual((target/"第1话.pdf").read_bytes(),before)
        self.assertTrue(self.library.chapters(book_id))

    def test_removed_managed_book_not_automatically_readded(self):
        book_id = self.copy_import(self.folder,self.real_chapters())
        self.library.remove(book_id)
        self.assertFalse(self.library.unregistered_folders())

    def test_library_parent_cannot_be_recursively_imported(self):
        with self.assertRaises(ValueError):
            self.library.plan_import(self.root)

    def test_reserved_staging_folder_name_is_safe(self):
        folder = self.root/"external"/".incoming"
        scanned = self.real_chapters(folder)
        plan = self.library.plan_import(folder)
        self.assertNotEqual(plan.target.name,".incoming")
        book_id = self.copy_import(folder,scanned)
        self.assertTrue(Path(self.library.chapters(book_id)[0]["path"]).is_file())


if __name__ == "__main__":
    unittest.main()

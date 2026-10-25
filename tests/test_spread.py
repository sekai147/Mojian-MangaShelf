import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import unittest
import uuid

import pymupdf as fitz
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from mangashelf.app import MainWindow, RenderTask, STYLE, load_fonts
from test_gui import ROOT, make_pdf, wait_until


class SpreadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.home = ROOT/("spread-"+uuid.uuid4().hex)
        self.folder = self.home/"comics"/"双页测试"
        self.folder.mkdir(parents=True)

    def render(self,path,rtl=False,double=True,page=0):
        task = RenderTask(1,str(path),page,900,500,"fit",double,rtl)
        results = []
        task.signals.done.connect(lambda *args:results.append(args))
        task.run()
        self.assertEqual(results[0][3],"")
        return task,results[0][1]

    def test_two_distinct_pages_rtl_order_and_plain_gap(self):
        path = self.folder/"colors.pdf"
        with fitz.open() as doc:
            first = doc.new_page(width=200,height=300)
            first.draw_rect(first.rect,fill=(1,0,0),color=None)
            second = doc.new_page(width=300,height=300)
            second.draw_rect(second.rect,fill=(0,0,1),color=None)
            doc.save(path)
        task,image = self.render(path)
        self.assertEqual(task.visible_pages,(0,1))
        self.assertEqual(task.visual_order,(0,1))
        self.assertGreater(image.pixelColor(0,image.height()//2).red(),240)
        self.assertGreater(image.pixelColor(image.width()-1,image.height()//2).blue(),240)
        gap = round(image.height()*2/3)
        self.assertEqual(image.pixelColor(gap+4,image.height()//2).alpha(),0)
        self.assertLessEqual(image.width(),901)
        self.assertLessEqual(image.height(),500)
        task,image = self.render(path,rtl=True)
        self.assertEqual(task.visual_order,(1,0))
        self.assertGreater(image.pixelColor(0,image.height()//2).blue(),240)
        self.assertGreater(image.pixelColor(image.width()-1,image.height()//2).red(),240)
        task,image = self.render(path,double=False,page=1)
        self.assertEqual(task.visible_pages,(1,))
        self.assertGreater(image.pixelColor(0,0).blue(),240)

    def test_spread_navigation_progress_and_saved_preferences(self):
        make_pdf(self.folder/"001.pdf",1,5)
        make_pdf(self.folder/"002.pdf",2,2)
        window = MainWindow(self.home/"data",self.home/"comics")
        window.show()
        window.scan_library(only_new=True)
        book_id = window.library.books()[0]["id"]
        try:
            window.start_reading(book_id)
            reader = window.reader
            self.assertTrue(reader.double_page())
            self.assertFalse(reader.toc_panel.isVisible())
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(0,1)))
            self.assertEqual(window.library.chapters(book_id)[0]["page"],1)
            reader.move(1)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(2,3)))
            self.assertEqual(window.library.chapters(book_id)[0]["page"],3)
            reader.move(1)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(4,)))
            self.assertTrue(window.library.chapters(book_id)[0]["completed"])
            reader.move(1)
            self.assertTrue(wait_until(lambda:reader.index==1 and reader.displayed_key[0]==reader.chapters[1]["id"]))
            self.assertEqual(reader.displayed_pages,(0,1))
            reader.move(-1)
            self.assertTrue(wait_until(lambda:reader.index==0 and reader.displayed_pages==(4,)))
            reader.go_page(3)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(2,3)))
            reader.rtl.setChecked(True)
            self.assertTrue(wait_until(lambda:reader.displayed_order==(3,2)))
            reader.view_mode.showPopup()
            QTest.keyClick(reader.view_mode.popup.options,Qt.Key.Key_Down)
            QTest.keyClick(reader.view_mode.popup.options,Qt.Key.Key_Return)
            self.assertEqual(reader.view_mode.currentIndex(),1)
            self.assertFalse(reader.view_mode.popup.isVisible())
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(2,)))
            reader.mode.showPopup()
            QTest.keyClick(reader.mode.popup.options,Qt.Key.Key_Escape)
            self.assertEqual(window.stack.currentIndex(),1)
            self.assertFalse(reader.mode.popup.isVisible())
            reader.view_mode.setCurrentIndex(0)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(2,3)))
            reader.go_page(1)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(0,1)))
            reader.page_spin.setText("4")
            reader.page_spin.editingFinished.emit()
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(2,3)))
            reader.progress_slider.setValue(4)
            self.assertTrue(wait_until(lambda:reader.displayed_pages==(4,)))
            self.assertEqual(window.library.chapters(book_id)[0]["page"],4)
            reader.view_mode.setCurrentIndex(1)
        finally:
            window.close()
        reopened = MainWindow(self.home/"data",self.home/"comics")
        self.assertEqual(reopened.reader.view_mode.currentIndex(),1)
        self.assertTrue(reopened.reader.rtl.isChecked())
        reopened.close()


if __name__ == "__main__":
    unittest.main()

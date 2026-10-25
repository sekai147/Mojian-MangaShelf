import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import unittest
import uuid
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from mangashelf.app import MainWindow, BookDialog, SettingsDialog, STYLE, load_fonts
from mangashelf.motion import Motion, TransitionLayer
from test_gui import ROOT, make_pdf, wait_until


class MotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.home = ROOT/("motion-"+uuid.uuid4().hex)
        folder = self.home/"comics"/"动画测试漫画"
        folder.mkdir(parents=True)
        make_pdf(folder/"001.pdf",1,5)
        make_pdf(folder/"002.pdf",2,3)
        self.window = MainWindow(self.home/"data",self.home/"comics")
        self.window.reader.view_mode.setCurrentIndex(1)
        self.window.show()
        self.window.scan_library(only_new=True)
        self.book_id = self.window.library.books()[0]["id"]

    def tearDown(self):
        self.window.close()
        QApplication.processEvents()

    def open_reader(self):
        self.window.start_reading(self.book_id)
        self.assertIsNotNone(self.window.stack_motion.layer)
        self.assertTrue(wait_until(lambda:self.window.reader.displayed_key is not None))
        self.assertTrue(wait_until(lambda:self.window.stack_motion.layer is None))
        return self.window.reader

    def test_page_effects_and_interruption_keep_latest_page(self):
        reader = self.open_reader()
        self.assertGreater(reader.page_spin.contentsRect().width(),50)
        for index,kind in enumerate(["slide","fade","turn"]):
            reader.page_effect.setCurrentIndex(index)
            target = index+1
            reader.go_page(target)
            self.assertTrue(wait_until(lambda:reader.displayed_key[1]==target and reader.page_motion.layer is not None))
            self.assertEqual(reader.page_motion.layer.kind,kind)
            self.assertTrue(reader.page_motion.layer.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
            reader.go_page(0)
            reader.go_page(4)
            reader.go_page(0)
            self.assertTrue(wait_until(lambda:reader.displayed_key[1]==0 and reader.page_motion.layer is None))
            self.assertEqual(self.window.library.chapters(self.book_id)[0]["page"],0)
            self.assertLessEqual(sum(layer.isVisible() for layer in reader.findChildren(TransitionLayer)),1)
        reader.page_effect.setCurrentIndex(3)
        reader.go_page(1)
        self.assertTrue(wait_until(lambda:reader.displayed_key[1]==1))
        self.assertIsNone(reader.page_motion.layer)

    def test_navigation_dialog_and_drawer_transitions(self):
        page = self.window.library_page
        page.set_filter("reading")
        self.assertTrue(wait_until(lambda:page.motion.layer is not None))
        page.set_filter("finished")
        page.set_filter("all")
        self.assertTrue(wait_until(lambda:page.motion.layer is None and not page.motion.timer.isActive()))
        self.assertEqual(page.filter,"all")
        detail = BookDialog(self.window,self.book_id)
        detail.show()
        self.assertTrue(wait_until(lambda:detail.motion.layer is not None))
        self.assertEqual(detail.motion.layer.kind,"zoom")
        detail.reject()
        self.assertIsNone(detail.motion.layer)
        reader = self.open_reader()
        reader.toggle_toc()
        self.assertTrue(wait_until(lambda:reader.toc.isVisible() and reader.toc_animation.state()==reader.toc_animation.State.Stopped))
        reader.toggle_toc()
        self.assertTrue(wait_until(lambda:not reader.toc.isVisible()))
        reader.toggle_toc()
        QTest.qWait(50)
        reader.toggle_toc()
        reader.toggle_toc()
        self.assertTrue(wait_until(lambda:reader.toc.isVisible() and reader.toc.width()>=170 and reader.toc_animation.state()==reader.toc_animation.State.Stopped))
        reader.change_chapter(1)
        self.assertTrue(wait_until(lambda:reader.displayed_key[0]==reader.chapters[1]["id"]))
        reader.back()
        self.assertEqual(self.window.stack.currentIndex(),0)
        self.assertIsNotNone(self.window.stack_motion.layer)
        self.assertIsNone(reader.page_motion.layer)
        self.assertTrue(wait_until(lambda:self.window.stack_motion.layer is None))

    def test_motion_switch_and_preferences_persist(self):
        reader = self.open_reader()
        reader.page_effect.setCurrentIndex(2)
        reader.go_page(1)
        self.assertTrue(wait_until(lambda:reader.page_motion.layer is not None))
        settings = SettingsDialog(self.window)
        settings.show()
        settings.animations.setChecked(False)
        self.assertFalse(self.window.animations_enabled)
        self.assertTrue(all(not choice.isEnabled() for choice in settings.effect_buttons))
        self.assertTrue(all(motion.layer is None for motion in self.window.findChildren(Motion)))
        reader.go_page(2)
        self.assertTrue(wait_until(lambda:reader.displayed_key[1]==2))
        self.assertIsNone(reader.page_motion.layer)
        settings.animations.setChecked(True)
        self.assertTrue(self.window.animations_enabled)
        settings.effect_buttons[1].click()
        self.assertEqual(reader.page_effect.currentIndex(),1)
        reader.page_effect.setCurrentIndex(2)
        self.assertTrue(settings.effect_buttons[2].isChecked())
        settings.animations.setChecked(False)
        settings.accept()
        self.window.close()
        self.window = MainWindow(self.home/"data",self.home/"comics")
        self.window.show()
        self.assertFalse(self.window.animations_enabled)
        self.assertEqual(self.window.reader.page_effect.currentIndex(),2)
        self.window.library_page.set_filter("reading")
        QTest.qWait(40)
        self.assertIsNone(self.window.library_page.motion.layer)


if __name__ == "__main__":
    unittest.main()

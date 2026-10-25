from __future__ import annotations

import argparse
import logging
import math
import os
from pathlib import Path
import sys
import traceback

import pymupdf as fitz
from PySide6.QtCore import (Qt, QSize, QThread, Signal, QTimer, QRunnable, QObject,
                            QThreadPool, QUrl, QVariantAnimation, QEasingCurve, QPointF, QRectF)
from PySide6.QtGui import (QColor, QPainter, QPen, QFont, QPixmap, QImage, QIcon, QFontDatabase,
                           QKeySequence, QShortcut, QDesktopServices, QLinearGradient, QPainterPath, QAction, QIntValidator)
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit, QComboBox, QStackedWidget,
    QScrollArea, QFileDialog, QMessageBox, QInputDialog, QDialog, QDialogButtonBox,
    QProgressBar, QListWidget, QListWidgetItem, QAbstractItemView, QSplitter,
    QSpinBox, QMenu, QSizePolicy, QCheckBox, QButtonGroup, QSlider)

from .core import (Library, ScannedChapter, chapter_number, pdf_files, number_text,
                   chapter_sort_key, prepare_copy, discard_staging, ImportCancelled, reading_pages)
from .motion import Motion
from .choices import ReaderChoice


STYLE = """
* {font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', sans-serif; font-size:13px;}
QMainWindow, QDialog {background:#f6f5f0; color:#263c35;}
QWidget {color:#263c35;}
QLabel {background:transparent;}
QFrame#sidebar {background:#eaece4; border-right:1px solid #dce0d5;}
QFrame#librarySummary {background:#f4f5ee; border:1px solid #d9dfd2; border-radius:13px;}
QLabel#summaryHeading {font-size:11px; font-weight:600; color:#7c8978;}
QLabel#summaryNumber {font-size:25px; font-weight:600; color:#35503d;}
QLabel#summaryCaption {font-size:11px; color:#8a9585;}
QFrame#summaryDivider {background:#dce2d5; border:0;}
QPushButton#libraryOpen {background:#36543f; color:#fffef4; border:0;
    border-radius:7px; font-size:12px; padding:7px 6px;}
QPushButton#libraryOpen:hover {background:#46654c;}
QPushButton#libraryOpen:pressed {background:#294331;}
QPushButton#libraryScan {background:#edf0e5; border:1px solid #d9e0ce;
    border-radius:7px; padding:0;}
QPushButton#libraryScan:hover {background:#dfe7d5; border-color:#bccbb2;}
QPushButton#sidebarSettings {background:transparent; border:0; border-radius:5px;
    color:#7b8976; font-size:11px; padding:4px 3px;}
QPushButton#sidebarSettings:hover {background:#dfe5d7; color:#3f5a43;}
QLabel#localStatus {font-size:10px; color:#8b9685;}
QLabel#localDot {background:#8da47e; border-radius:3px;}
QLabel#settingsTitle {font-size:23px; font-weight:700;}
QLabel#settingsSubtitle {font-size:11px; color:#8a9385;}
QLabel#settingsSection {font-size:17px; font-weight:600;}
QLabel#settingsItem {font-size:13px; font-weight:600;}
QLabel#settingsHint {font-size:11px; color:#8a9484;}
QFrame#settingsRail {background:#eaece2; border:0; border-radius:12px;}
QFrame#settingsCard {background:#fffefa; border:1px solid #e0e5d7; border-radius:12px;}
QPushButton#settingsNav {background:transparent; border:0; border-radius:7px;
    text-align:left; font-size:12px; padding:11px 10px; color:#7d8975;}
QPushButton#settingsNav:hover {background:#e1e7d8;}
QPushButton#settingsNav:checked {background:#d9e3d0; color:#35503d; font-weight:600;}
QPushButton#effectChoice {background:#f7f8f1; border:1px solid #e2e7d9;
    border-radius:8px; font-size:12px; padding:10px; color:#74816a;}
QPushButton#effectChoice:hover {background:#edf2e6; border-color:#b9cbaa;}
QPushButton#effectChoice:checked {background:#e9f0df; border:1px solid #8fa880; color:#35543a;}
QPushButton#effectChoice:disabled {background:#f6f6f1; border-color:#e9ebe3; color:#b0b6a7;}
QLabel#libraryPath {background:#f1f4e9; border:0; border-radius:7px;
    color:#718368; font-size:11px; padding:10px;}
QLabel#guideNumber {background:#e9eee0; color:#758d63; border-radius:10px; font-size:11px;}
QLabel#keyCap {background:#f0f2e9; border:1px solid #e0e5d6; border-radius:5px;
    padding:4px 8px; color:#78876c; font-size:10px;}
QWidget#readerDesk {background:#e5e8e0;}
QFrame#readerHeader {background:#f8f8f2; border-bottom:1px solid #dce2d5;}
QFrame#readerFooter {background:#f8f8f2; border-top:1px solid #dce2d5;}
QFrame#readerToc {background:#f3f5ec; border-right:1px solid #d8dfce;}
QLabel#readerTitle {font-size:17px; font-weight:600; color:#304a38;}
QLabel#readerMeta {font-size:10px; color:#89957f;}
QPushButton#readerTool {background:transparent; border:0; border-radius:8px; padding:7px;}
QPushButton#readerTool:hover {background:#e7edde;}
QPushButton#readerTool:checked {background:#dfe9d4;}
QPushButton#readerBack {background:transparent; border:0; font-size:12px; padding:8px 10px;}
QPushButton#readerBack:hover {background:#e7edde;}
QPushButton#readerPager {background:transparent; border:0; border-radius:19px;
    font-size:24px; padding:0; color:#708466;}
QPushButton#readerPager:hover {background:#d5decc; color:#38523c;}
QPushButton#readerPager:disabled {background:transparent; color:#bdc6b6;}
QListWidget#readerChapters {background:transparent; border:0; border-radius:0; padding:0;}
QListWidget#readerChapters::item {padding:13px 11px; border:0; font-size:12px;}
QListWidget#readerChapters::item:selected {background:#e0e9d6; color:#36533d;}
QComboBox#readerChoice {background:#edf1e5; border:1px solid #e0e6d7;
    border-radius:7px; padding:7px 9px; font-size:11px;}
QComboBox#readerChoice:hover {background:#e8efdf; border-color:#bacaaa;}
QComboBox[refinedPopup="true"]::down-arrow {image:none; width:0; height:0;}
QLineEdit#readerPageJump {background:#edf1e5; border:1px solid #dce4d2;
    border-radius:6px; padding:5px 7px; font-size:11px;}
QSlider#readerProgress::groove:horizontal {height:3px; background:#dce3d3; border-radius:1px;}
QSlider#readerProgress::sub-page:horizontal {background:#89a174; border-radius:1px;}
QSlider#readerProgress::handle:horizontal {background:#fafbf5; border:1px solid #8b9f7b;
    width:10px; height:10px; margin:-4px 0; border-radius:5px;}
QLabel#brand {font-size:30px; font-weight:700; letter-spacing:3px;}
QLabel#eyebrow {color:#7b897e; font-size:10px; letter-spacing:3px;}
QLabel#heading {font-size:30px; font-weight:700;}
QLabel#muted {color:#7d887f;}
QLabel#section {font-size:17px; font-weight:700;}
QPushButton {background:#fffefa; border:1px solid #dbe0d5; padding:10px 17px;
    border-radius:8px; color:#344b40;}
QPushButton:hover {background:#e9eee4; border-color:#bdcbbd;}
QPushButton:pressed {background:#dce5d8;}
QPushButton:disabled {color:#a9afa5; background:#efefe9;}
QPushButton#primary {background:#324f40; color:#fffef6; border:1px solid #324f40; font-weight:600;}
QPushButton#primary:hover {background:#42664f;}
QPushButton#nav {text-align:left; border:0; padding:13px 17px; background:transparent; color:#738073;}
QPushButton#nav:checked {background:#dce3d5; color:#294634; font-weight:700;}
QPushButton#nav:hover {background:#e0e6d9;}
QPushButton#quiet {background:transparent; border:0; color:#748274; padding:7px 10px;}
QLineEdit, QComboBox, QSpinBox {background:#fffefa; border:1px solid #dbe0d5; border-radius:7px;
    padding:9px 11px; selection-background-color:#527859; color:#2c4537;}
QLineEdit:focus {border-color:#668367;}
QSpinBox QLineEdit {border:0; padding:0; background:transparent;}
QComboBox::drop-down {border:0; width:24px;}
QComboBox QAbstractItemView {background:#fffefa; selection-background-color:#dce6d6; color:#263c35;}
QScrollArea {background:transparent; border:0;}
QScrollArea>QWidget>QWidget {background:transparent;}
QScrollBar:vertical {background:transparent; width:9px; margin:2px;}
QScrollBar::handle:vertical {background:#c5cec0; border-radius:3px; min-height:35px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height:0;}
QScrollBar:horizontal {background:transparent; height:9px;}
QScrollBar::handle:horizontal {background:#c5cec0; border-radius:3px; min-width:35px;}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {width:0;}
QListWidget {background:#fffefa; border:1px solid #dce2d5; border-radius:8px; outline:0; padding:5px;}
QListWidget::item {padding:13px 10px; border-bottom:1px solid #eff0e9; border-radius:4px;}
QListWidget::item:selected {background:#dfe9d9; color:#294634;}
QListWidget::item:hover {background:#edf0e7;}
QProgressBar {border:0; background:#e3e7dc; border-radius:3px; height:5px; text-align:center;}
QProgressBar::chunk {background:#799465; border-radius:3px;}
QFrame#card {background:#fffefa; border:1px solid #e1e5d9; border-radius:12px;}
QFrame#hero {background:#e9ecdf; border:1px solid #dce3d0; border-radius:16px;}
QToolTip {background:#294634; color:white; border:0; padding:7px;}
QMenu {background:#fffefa; border:1px solid #dce2d5; padding:5px;}
QMenu::item {padding:9px 24px;}
QMenu::item:selected {background:#dfe9d9;}
"""


def load_fonts():
    # Offscreen Qt and restricted Windows sessions may not enumerate system fonts.
    if "Microsoft YaHei UI" not in QFontDatabase.families():
        font = Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts/msyh.ttc"
        if font.is_file():
            QFontDatabase.addApplicationFont(str(font))


def application_icon():
    return QIcon(str(Path(__file__).resolve().parent/"assets"/"mangashelf.png"))


def sidebar_icon(kind, color="#6f8266"):
    pixmap = QPixmap(36,36)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color),1.35,Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "folder":
        path = QPainterPath(QPointF(2.5,6))
        path.lineTo(2.5,4.5)
        path.quadTo(2.5,3,4,3)
        path.lineTo(7,3)
        path.lineTo(8.5,5)
        path.lineTo(14,5)
        path.quadTo(15.5,5,15.5,6.5)
        path.lineTo(15.5,13.5)
        path.quadTo(15.5,15,14,15)
        path.lineTo(4,15)
        path.quadTo(2.5,15,2.5,13.5)
        path.closeSubpath()
        painter.drawPath(path)
    elif kind == "refresh":
        painter.drawArc(QRectF(3.5,3.5,11,11),50*16,280*16)
        path = QPainterPath(QPointF(14.5,3))
        path.lineTo(14.5,7)
        path.lineTo(10.5,7)
        painter.drawPath(path)
    elif kind == "contents":
        for y in [4,9,14]:
            painter.drawLine(QPointF(7,y),QPointF(15,y))
            painter.drawPoint(QPointF(3,y))
    elif kind == "fullscreen":
        for x,y,dx,dy in [(3,3,1,1),(15,3,-1,1),(3,15,1,-1),(15,15,-1,-1)]:
            painter.drawLine(QPointF(x,y),QPointF(x+4*dx,y))
            painter.drawLine(QPointF(x,y),QPointF(x,y+4*dy))
    elif kind == "back":
        painter.drawLine(QPointF(3,9),QPointF(15,9))
        painter.drawLine(QPointF(3,9),QPointF(8,4))
        painter.drawLine(QPointF(3,9),QPointF(8,14))
    else:
        for y,x in [(5,7),(12,11)]:
            painter.drawLine(QPointF(3,y),QPointF(15,y))
            painter.setBrush(QColor("#eaece4"))
            painter.drawEllipse(QPointF(x,y),2,2)
    painter.end()
    return QIcon(pixmap)


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback=None, primary=False, quiet=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName("primary")
    elif quiet:
        widget.setObjectName("quiet")
    if callback:
        widget.clicked.connect(callback)
    return widget


class BookArt(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(250, 140)
        self.setMaximumWidth(320)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width()/2-100, self.height()/2-60)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#d5ddc5"))
        p.drawEllipse(10,100,190,20)
        p.save()
        p.translate(26,10)
        p.rotate(-12)
        p.setBrush(QColor("#71826a"))
        p.drawRoundedRect(0,0,85,112,4,4)
        p.setBrush(QColor("#f5f1df"))
        p.drawRoundedRect(8,5,77,101,3,3)
        p.setPen(QPen(QColor("#c5cbb8"),1))
        for y in range(18,96,10):
            p.drawLine(19,y,72,y)
        p.restore()
        p.save()
        p.translate(103,0)
        p.rotate(9)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#3c5944"))
        p.drawRoundedRect(0,0,87,119,5,5)
        p.setPen(QPen(QColor("#78906c"),1))
        p.drawRect(12,12,62,94)
        p.setPen(QColor("#eee8cd"))
        p.setFont(QFont("Microsoft YaHei UI",20))
        p.drawText(18,26,55,64,Qt.AlignmentFlag.AlignCenter,"墨\n间")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#c58b5e"))
        p.drawRect(59,0,11,29)
        p.restore()
        p.end()


class SettingSwitch(QCheckBox):
    def __init__(self):
        super().__init__()
        self.setFixedSize(42,24)
        self.setAccessibleName("界面动画")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.position = 0.0
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(140)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.advance)
        self.toggled.connect(self.animate)

    def advance(self,value):
        self.position = float(value)
        self.update()

    def animate(self,checked):
        self.animation.stop()
        self.animation.setStartValue(self.position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()

    def hitButton(self,position):
        return self.rect().contains(position)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self.position
        color = QColor(*[round(a+(b-a)*p) for a,b in zip((202,211,193),(55,86,62))])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(1,1,40,22),11,11)
        painter.setBrush(QColor("#fffef7"))
        painter.drawEllipse(QPointF(12+18*p,12),8,8)
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#95aa82"),1,Qt.PenStyle.DotLine))
            painter.drawRoundedRect(QRectF(.5,.5,41,23),11.5,11.5)
        painter.end()


class SettingsDialog(QDialog):
    def __init__(self,window):
        super().__init__(window)
        self.owner = window
        self.setWindowTitle("偏好设置 · 墨间")
        self.setWindowIcon(application_icon())
        self.resize(760,600)
        self.setMinimumSize(680,520)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24,24,24,20)
        outer.setSpacing(20)
        header = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(application_icon().pixmap(42,42))
        mark.setFixedSize(42,42)
        header.addWidget(mark)
        heading = QVBoxLayout()
        heading.setSpacing(3)
        heading.addWidget(label("偏好设置","settingsTitle"))
        heading.addWidget(label("让阅读，按你喜欢的方式。","settingsSubtitle"))
        header.addLayout(heading,1)
        header.addWidget(label("MOJIAN  /  墨间","eyebrow"))
        outer.addLayout(header)
        body = QHBoxLayout()
        body.setSpacing(18)
        rail = QFrame()
        rail.setObjectName("settingsRail")
        rail.setFixedWidth(138)
        navigation = QVBoxLayout(rail)
        navigation.setContentsMargins(10,12,10,12)
        navigation.setSpacing(6)
        self.tabs = []
        for index,(title,icon) in enumerate([("阅读体验","settings"),("书库与帮助","folder")]):
            tab = button(title,lambda checked=False,i=index:self.select_section(i))
            tab.setObjectName("settingsNav")
            tab.setCheckable(True)
            tab.setIcon(sidebar_icon(icon))
            tab.setIconSize(QSize(15,15))
            navigation.addWidget(tab)
            self.tabs.append(tab)
        navigation.addStretch()
        note = label("慢慢翻页\n静静读完一个故事","settingsHint",True)
        note.setContentsMargins(8,0,0,0)
        navigation.addWidget(note)
        body.addWidget(rail)
        self.pages = QStackedWidget()
        self.pages.addWidget(self.reading_page())
        self.pages.addWidget(self.help_page())
        body.addWidget(self.pages,1)
        outer.addLayout(body,1)
        footer = QHBoxLayout()
        footer.addWidget(label("偏好自动保存","settingsHint"),1)
        close = button("完成",self.accept,primary=True)
        close.setDefault(True)
        close.setMinimumWidth(86)
        footer.addWidget(close)
        outer.addLayout(footer)
        self.motion = Motion(self,lambda:window.animations_enabled)
        action = window.library_page.animation_toggle
        self.animations.toggled.connect(action.setChecked)
        action.toggled.connect(self.sync_animations)
        window.reader.page_effect.currentIndexChanged.connect(self.sync_effect)
        self.view_picker.currentIndexChanged.connect(window.reader.view_mode.setCurrentIndex)
        window.reader.view_mode.currentIndexChanged.connect(self.view_picker.setCurrentIndex)
        self.reading_direction.toggled.connect(window.reader.rtl.setChecked)
        window.reader.rtl.toggled.connect(self.reading_direction.setChecked)
        self.sync_animations(window.animations_enabled)
        self.sync_effect(window.reader.page_effect.currentIndex())
        self.select_section(0,animate=False)

    def scroll_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        content = QVBoxLayout(host)
        content.setContentsMargins(0,1,8,1)
        content.setSpacing(13)
        scroll.setWidget(host)
        return scroll,content

    def card(self):
        frame = QFrame()
        frame.setObjectName("settingsCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16,15,16,15)
        layout.setSpacing(12)
        return frame,layout

    def reading_page(self):
        scroll,content = self.scroll_page()
        content.addWidget(label("阅读体验","settingsSection"))
        content.addWidget(label("为每一次翻页，留一点舒适的节奏。","settingsHint",True))
        card,layout = self.card()
        row = QHBoxLayout()
        row.addWidget(label("画面布局","settingsItem"),1)
        self.view_picker = QComboBox()
        self.view_picker.addItems(["双页展开","单页阅读"])
        self.view_picker.setCurrentIndex(self.owner.reader.view_mode.currentIndex())
        row.addWidget(self.view_picker)
        layout.addLayout(row)
        layout.addWidget(label("双页模式一次显示两页；章节末页不足两页时单独居中。","settingsHint",True))
        row = QHBoxLayout()
        words = QVBoxLayout()
        words.setSpacing(4)
        words.addWidget(label("从右向左阅读","settingsItem"))
        words.addWidget(label("右页优先，适合日漫；左右翻页方向同步调整。","settingsHint",True))
        row.addLayout(words,1)
        self.reading_direction = SettingSwitch()
        self.reading_direction.setAccessibleName("从右向左阅读")
        self.reading_direction.setChecked(self.owner.reader.rtl.isChecked())
        self.reading_direction.animation.stop()
        self.reading_direction.advance(1.0 if self.owner.reader.rtl.isChecked() else 0.0)
        row.addWidget(self.reading_direction)
        layout.addLayout(row)
        content.addWidget(card)
        card,layout = self.card()
        row = QHBoxLayout()
        words = QVBoxLayout()
        words.setSpacing(5)
        words.addWidget(label("界面动画","settingsItem"))
        words.addWidget(label("切换书架、章节和目录时显示过渡效果。","settingsHint",True))
        row.addLayout(words,1)
        row.addSpacing(12)
        self.animations = SettingSwitch()
        row.addWidget(self.animations)
        layout.addLayout(row)
        content.addWidget(card)
        card,layout = self.card()
        layout.addWidget(label("翻页效果","settingsItem"))
        layout.addWidget(label("选择一种翻页和章节切换的过渡方式。","settingsHint",True))
        choices = QGridLayout()
        choices.setSpacing(9)
        self.effect_group = QButtonGroup(self)
        self.effect_buttons = []
        for index,(title,caption) in enumerate([("滑动","轻移过渡"),("淡入","柔和叠化"),
                                                ("翻书","纸页翻转"),("关闭","直接显示")]):
            choice = button(f"{title}\n{caption}")
            choice.setObjectName("effectChoice")
            choice.setCheckable(True)
            choice.setMinimumHeight(63)
            self.effect_group.addButton(choice,index)
            self.effect_buttons.append(choice)
            choices.addWidget(choice,index//2,index%2)
        self.effect_group.idClicked.connect(self.owner.reader.page_effect.setCurrentIndex)
        layout.addLayout(choices)
        self.effect_note = label("翻页和章节切换使用同一效果。","settingsHint",True)
        layout.addWidget(self.effect_note)
        content.addWidget(card)
        content.addStretch()
        return scroll

    def help_page(self):
        scroll,content = self.scroll_page()
        content.addWidget(label("书库与帮助","settingsSection"))
        content.addWidget(label("漫画留在本机，故事随时继续。","settingsHint",True))
        card,layout = self.card()
        row = QHBoxLayout()
        row.addWidget(label("本地漫画库","settingsItem"),1)
        open_folder = button("打开文件夹",self.owner.open_comics,quiet=True)
        open_folder.setIcon(sidebar_icon("folder"))
        open_folder.setIconSize(QSize(14,14))
        row.addWidget(open_folder)
        layout.addLayout(row)
        self.library_path = label(str(self.owner.library.comics_dir),"libraryPath",True)
        self.library_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.library_path)
        layout.addWidget(label("导入会复制整个文件夹到这里，完成后可移动源文件夹。", "settingsHint",True))
        content.addWidget(card)
        card,layout = self.card()
        layout.addWidget(label("快速开始","settingsItem"))
        for index,(title,description) in enumerate([
            ("导入漫画","选择或拖入文件夹，每个 PDF 对应一个章节，书名可随时修改。"),
            ("自动整理","按文件名识别章节号并排序，也可以在目录里拖动调整。"),
            ("接着阅读","双击章节开始阅读，进度自动保存；末页之后衔接下一章。")],1):
            row = QHBoxLayout()
            row.setSpacing(10)
            number = label(str(index),"guideNumber")
            number.setFixedSize(21,21)
            number.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(number,0,Qt.AlignmentFlag.AlignTop)
            words = QVBoxLayout()
            words.setSpacing(4)
            words.addWidget(label(title))
            words.addWidget(label(description,"settingsHint",True))
            row.addLayout(words,1)
            layout.addLayout(row)
        content.addWidget(card)
        card,layout = self.card()
        layout.addWidget(label("常用快捷键","settingsItem"))
        for action,key in [("导入文件夹","Ctrl + O"),("翻页","← / →"),("下一页","Space"),
                           ("全屏阅读","F11"),("退出全屏 / 返回书架","Esc")]:
            row = QHBoxLayout()
            row.addWidget(label(action,"settingsHint"),1)
            row.addWidget(label(key,"keyCap"))
            layout.addLayout(row)
        content.addWidget(card)
        content.addWidget(label("把漫画文件夹直接放进 comics 后，点击书库卡片的刷新图标即可识别。"
                                "备份 comics 和 data，可同时保留漫画与阅读进度。","settingsHint",True))
        return scroll

    def sync_animations(self,enabled):
        previous = self.animations.blockSignals(True)
        self.animations.setChecked(enabled)
        self.animations.blockSignals(previous)
        self.animations.animation.stop()
        self.animations.advance(1.0 if enabled else 0.0)
        for choice in self.effect_buttons:
            choice.setEnabled(enabled)
        self.effect_note.setText("翻页和章节切换使用同一效果。" if enabled else "开启界面动画后，可选择翻页过渡效果。")

    def sync_effect(self,index):
        if 0<=index<len(self.effect_buttons):
            self.effect_buttons[index].setChecked(True)

    def select_section(self,index,animate=True):
        before = self.motion.capture() if hasattr(self,"motion") and animate else QPixmap()
        self.pages.setCurrentIndex(index)
        for i,tab in enumerate(self.tabs):
            tab.setChecked(i==index)
        if not before.isNull():
            self.motion.play(before,"fade",duration=160)

    def showEvent(self,event):
        super().showEvent(event)
        self.motion.reveal("zoom",200)


class ImportWorker(QThread):
    progress = Signal(int, int, str)
    ready = Signal(object, object, object)
    failed = Signal(str)

    def __init__(self, folder):
        super().__init__()
        self.folder = Path(folder)

    def run(self):
        try:
            files = pdf_files(self.folder)
            if not files:
                raise ValueError("这个文件夹及其子文件夹中没有 PDF 文件。")
            chapters, skipped, cover = [], [], None
            for index, path in enumerate(files):
                if self.isInterruptionRequested():
                    return
                self.progress.emit(index,len(files),path.name)
                try:
                    with fitz.open(path) as doc:
                        if doc.needs_pass:
                            raise ValueError("PDF 已加密，需要先移除密码")
                        if doc.page_count < 1:
                            raise ValueError("PDF 没有页面")
                        # Confirm at least the first page can be decoded.
                        first = doc.load_page(0)
                        if cover is None:
                            scale = min(360/max(first.rect.width,1),480/max(first.rect.height,1),3)
                            pix = first.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
                            cover = pix.tobytes("png")
                        stat = path.stat()
                        chapters.append(ScannedChapter(str(path),path.stem,chapter_number(path.name),
                                                       doc.page_count,stat.st_size,stat.st_mtime))
                except Exception as exc:
                    skipped.append(f"{path.relative_to(self.folder)}：{exc}")
            if self.isInterruptionRequested():
                return
            if not chapters:
                raise ValueError("没有可读取的 PDF。\n\n"+"\n".join(skipped[:12]))
            self.ready.emit(chapters,cover,skipped)
        except Exception as exc:
            self.failed.emit(str(exc))


class CopyWorker(QThread):
    progress = Signal(int,str)
    ready = Signal(object)
    failed = Signal(str)

    def __init__(self, plan, comics_dir):
        super().__init__()
        self.plan,self.comics_dir = plan,comics_dir
        self.last_progress = None

    def report_progress(self,current,total,name):
        value = min(100,int(100*current/total))
        if (value,name) != self.last_progress:
            self.last_progress = (value,name)
            self.progress.emit(value,name)

    def run(self):
        try:
            staged = prepare_copy(self.plan,self.comics_dir,self.isInterruptionRequested,self.report_progress)
            self.ready.emit(staged)
        except ImportCancelled:
            pass
        except Exception as exc:
            self.failed.emit(str(exc))


class ImportDialog(QDialog):
    def __init__(self, library, folder, parent=None, auto_commit=False):
        super().__init__(parent)
        self.setWindowTitle("导入漫画")
        self.setMinimumWidth(540)
        self.library, self.folder, self.book_id = library, Path(folder), None
        self.plan = library.plan_import(self.folder)
        self.auto_commit = auto_commit
        self.copying = False
        self.staged = None
        self.result_data = None
        self.worker = None
        self.pending_result = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,25,28,25)
        layout.setSpacing(15)
        layout.addWidget(label("把一个故事，放进书架。","section"))
        layout.addWidget(label(str(self.folder),"muted",True))
        layout.addWidget(label(f"保存到漫画库：{self.plan.target}","muted",True))
        layout.addWidget(label("漫画名称"))
        old = library.by_folder(folder)
        self.name = QLineEdit(old["title"] if old else self.folder.name)
        self.name.setMaxLength(150)
        self.name.setPlaceholderText("输入漫画名称")
        layout.addWidget(self.name)
        if old:
            layout.addWidget(label("此文件夹已导入，将更新章节并保留阅读进度。","muted",True))
        self.status = label("准备识别 PDF 章节…","muted",True)
        layout.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)
        self.summary = label("确认后将整个文件夹复制到漫画库；导入完成后可移动或删除源文件夹。"
                             if self.plan.source != self.plan.target else "该文件夹已在漫画库中，将直接识别章节。","muted",True)
        layout.addWidget(self.summary)
        actions = QHBoxLayout()
        actions.addStretch()
        self.cancel = button("取消",self.reject)
        self.confirm = button("导入书架",self.commit,primary=True)
        self.confirm.setEnabled(False)
        actions.addWidget(self.cancel)
        actions.addWidget(self.confirm)
        layout.addLayout(actions)
        QTimer.singleShot(0,self.scan)

    def scan(self):
        self.worker = ImportWorker(self.folder)
        self.worker.progress.connect(self.on_progress)
        self.worker.ready.connect(self.on_ready)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_finished(self):
        if self.pending_result is not None:
            super().done(self.pending_result)
        elif self.auto_commit and self.result_data and not self.copying:
            self.commit()

    def on_progress(self, current, total, name):
        self.bar.setRange(0,total)
        self.bar.setValue(current)
        self.status.setText(f"正在识别 {current+1} / {total} · {name}")

    def on_ready(self, chapters, cover, skipped):
        if self.pending_result is not None:
            return
        self.result_data = chapters,cover,skipped
        self.bar.setValue(self.bar.maximum())
        recognized = sum(c.number is not None for c in chapters)
        self.status.setText(f"已找到 {len(chapters)} 个章节 · {sum(c.pages for c in chapters)} 页")
        self.summary.setText(f"已识别 {recognized} 个章节号，其余按文件名自然排序；番外放在最后。"
                             + (f"\n跳过 {len(skipped)} 个文件：\n"+"\n".join(skipped[:5]) if skipped else ""))
        self.confirm.setEnabled(True)

    def on_failed(self, text):
        self.copying = False
        self.name.setEnabled(True)
        self.confirm.setEnabled(self.result_data is not None)
        self.cancel.setEnabled(True)
        self.status.setText("无法导入")
        self.summary.setText(text)
        # Automated scans stop for review on a failed folder.
        self.auto_commit = False

    def commit(self):
        if self.copying or self.pending_result is not None or not self.result_data:
            return
        if not self.name.text().strip():
            self.name.setFocus()
            self.name.setPlaceholderText("请填写漫画名称")
            return
        if self.worker and self.worker.isRunning():
            QTimer.singleShot(20,self.commit)
            return
        if self.plan.source == self.plan.target:
            self.on_copied(None)
            return
        self.copying = True
        self.name.setEnabled(False)
        self.confirm.setEnabled(False)
        self.bar.setRange(0,100)
        self.bar.setValue(0)
        self.status.setText("正在复制漫画文件夹…")
        self.worker = CopyWorker(self.plan,self.library.comics_dir)
        self.worker.progress.connect(self.on_copy_progress)
        self.worker.ready.connect(self.on_copied)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_copy_progress(self,percent,name):
        self.bar.setValue(percent)
        self.status.setText(f"正在复制 {percent}% · {name}")

    def on_copied(self,staged):
        self.staged = staged
        try:
            if self.pending_result is not None:
                return
            self.book_id = self.library.commit_copy(self.plan,self.name.text(),*self.result_data[:2],staged)
            self.accept()
        except Exception as exc:
            self.on_failed(str(exc))
        finally:
            if staged and staged.exists():
                discard_staging(staged,self.library.comics_dir)
            self.staged = None

    def done(self, result):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.status.setText("正在取消导入并清理临时副本…")
            self.cancel.setEnabled(False)
            self.pending_result = result
            return
        super().done(result)


class BookCard(QFrame):
    opened = Signal(str)
    menu_requested = Signal(str, object)

    def __init__(self, row):
        super().__init__()
        self.row = row
        self.setObjectName("card")
        self.setFixedWidth(210)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,12)
        layout.setSpacing(7)
        self.cover = QLabel()
        self.cover.setFixedSize(188,240)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover.setStyleSheet("background:#e4e8dc;border-radius:6px;")
        pix = QPixmap(row["cover"] or "")
        if not pix.isNull():
            self.cover.setPixmap(pix.scaled(self.cover.size(),Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.SmoothTransformation))
        else:
            self.cover.setText("墨间\n\nPDF 漫画")
        layout.addWidget(self.cover)
        title_row = QHBoxLayout()
        title = label(row["title"])
        title.setToolTip(row["title"])
        title.setStyleSheet("font-size:15px;font-weight:700;")
        title.setMaximumWidth(155)
        title_row.addWidget(title,1)
        more = button("···",quiet=True)
        more.setFixedSize(25,28)
        more.clicked.connect(lambda: self.menu_requested.emit(row["id"],more.mapToGlobal(more.rect().bottomLeft())))
        title_row.addWidget(more)
        layout.addLayout(title_row)
        layout.addWidget(label(f"{row['chapter_count']} 章节  /  {row['total_pages']} 页","muted"))
        percent = min(100,round(100*row["read_pages"]/max(row["total_pages"],1)))
        progress = QProgressBar()
        progress.setRange(0,100)
        progress.setValue(percent)
        progress.setTextVisible(False)
        progress.setFixedHeight(4)
        layout.addWidget(progress)
        caption = "已读完" if row["finished"] == row["chapter_count"] else (f"已读 {percent}%" if row["last_read"] else "等待翻开第一章")
        layout.addWidget(label(caption,"muted"))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit(self.row["id"])
        super().mouseReleaseEvent(event)


class LibraryPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.filter = "all"
        self.columns = 0
        self.rows = []
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(214)
        sidebar = QVBoxLayout(side)
        sidebar.setContentsMargins(24,36,24,26)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(application_icon().pixmap(38,38))
        mark.setFixedSize(38,38)
        brand.addWidget(mark)
        brand.addWidget(label("墨间","brand"))
        brand.addStretch()
        sidebar.addLayout(brand)
        sidebar.addWidget(label("MANGA SHELF","eyebrow"))
        sidebar.addSpacing(44)
        sidebar.addWidget(label("我的藏书","muted"))
        sidebar.addSpacing(10)
        self.nav = {}
        for key,text in [("all","01    全部漫画"),("reading","02    正在阅读"),("finished","03    已读完")]:
            b = button(text,lambda checked=False,k=key:self.set_filter(k))
            b.setObjectName("nav")
            b.setCheckable(True)
            b.setChecked(key=="all")
            self.nav[key] = b
            sidebar.addWidget(b)
        sidebar.addStretch()
        summary = QFrame()
        summary.setObjectName("librarySummary")
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(12,13,12,12)
        summary_layout.setSpacing(12)
        summary_layout.addWidget(label("我的书库","summaryHeading"))
        counts = QHBoxLayout()
        counts.setSpacing(8)
        self.book_count = label("0","summaryNumber")
        self.chapter_count = label("0","summaryNumber")
        for i,(number,caption) in enumerate([(self.book_count,"本漫画"),(self.chapter_count,"个章节")]):
            if i:
                divider = QFrame()
                divider.setObjectName("summaryDivider")
                divider.setFixedSize(1,31)
                counts.addWidget(divider)
            cell = QVBoxLayout()
            cell.setSpacing(1)
            number.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
            cell.addWidget(number)
            cell.addWidget(label(caption,"summaryCaption"))
            counts.addLayout(cell,1)
        summary_layout.addLayout(counts)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.open_library_button = button("打开漫画库",window.open_comics)
        self.open_library_button.setObjectName("libraryOpen")
        self.open_library_button.setIcon(sidebar_icon("folder","#f8f8eb"))
        self.open_library_button.setIconSize(QSize(14,14))
        self.open_library_button.setFixedHeight(32)
        actions.addWidget(self.open_library_button,1)
        self.scan_library_button = button("",window.scan_library)
        self.scan_library_button.setObjectName("libraryScan")
        self.scan_library_button.setIcon(sidebar_icon("refresh"))
        self.scan_library_button.setIconSize(QSize(16,16))
        self.scan_library_button.setFixedSize(32,32)
        self.scan_library_button.setToolTip("扫描漫画库，识别新增漫画和章节")
        self.scan_library_button.setAccessibleName("扫描漫画库")
        actions.addWidget(self.scan_library_button)
        summary_layout.addLayout(actions)
        sidebar.addWidget(summary)
        sidebar.addSpacing(7)
        footer = QHBoxLayout()
        footer.setSpacing(5)
        dot = label("","localDot")
        dot.setFixedSize(6,6)
        footer.addWidget(dot)
        footer.addWidget(label("本地保存","localStatus"))
        footer.addStretch()
        self.animation_toggle = QAction("界面动画",self)
        self.animation_toggle.setCheckable(True)
        self.animation_toggle.setChecked(window.animations_enabled)
        self.animation_toggle.toggled.connect(window.set_animations)
        self.settings_button = button("设置",self.show_settings)
        self.settings_button.setObjectName("sidebarSettings")
        self.settings_button.setIcon(sidebar_icon("settings","#829078"))
        self.settings_button.setIconSize(QSize(14,14))
        self.settings_button.setToolTip("动画偏好与使用说明")
        footer.addWidget(self.settings_button)
        sidebar.addLayout(footer)
        outer.addWidget(side)
        main = QWidget()
        content = QVBoxLayout(main)
        content.setContentsMargins(38,30,38,22)
        content.setSpacing(21)
        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("给故事，一个安静的角落。","muted"))
        self.heading = label("我的书架","heading")
        titles.addWidget(self.heading)
        header.addLayout(titles)
        header.addStretch()
        header.addWidget(button("＋  导入漫画文件夹",window.import_folder,primary=True))
        content.addLayout(header)
        self.hero = QFrame()
        self.hero.setObjectName("hero")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(25,16,16,16)
        hero_text = QVBoxLayout()
        hero_text.addWidget(label("YOUR NEXT CHAPTER","eyebrow"))
        self.hero_title = label("每一次翻页，都是新的相遇。","section")
        hero_text.addWidget(self.hero_title)
        self.hero_desc = label("导入一个文件夹，让散落的章节自动归位。","muted",True)
        hero_text.addWidget(self.hero_desc)
        self.resume = button("开始收藏  →",window.import_folder,quiet=True)
        self.resume.setMaximumWidth(200)
        hero_text.addWidget(self.resume)
        hero_layout.addLayout(hero_text,1)
        hero_layout.addWidget(BookArt())
        content.addWidget(self.hero)
        tools = QHBoxLayout()
        self.count = label("全部漫画 · 0","section")
        tools.addWidget(self.count)
        tools.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索漫画名称…")
        self.search.setClearButtonEnabled(True)
        self.search.setMaximumWidth(240)
        self.search.textChanged.connect(lambda:self.refresh_grid(animate=True))
        tools.addWidget(self.search)
        self.sort = QComboBox()
        self.sort.addItems(["最近阅读","名称排序","最近导入"])
        self.sort.currentIndexChanged.connect(lambda:self.refresh_grid(animate=True))
        tools.addWidget(self.sort)
        content.addLayout(tools)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0,0,0,0)
        self.grid.setHorizontalSpacing(22)
        self.grid.setVerticalSpacing(24)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop|Qt.AlignmentFlag.AlignLeft)
        self.scroll.setWidget(self.grid_host)
        self.motion = Motion(self.scroll.viewport(),lambda:window.animations_enabled)
        content.addWidget(self.scroll,1)
        self.footer = label("PDF 章节自动排序  ·  阅读进度自动保存","muted")
        content.addWidget(self.footer)
        outer.addWidget(main,1)

    def set_filter(self, key):
        self.filter = key
        for k,b in self.nav.items():
            b.setChecked(k==key)
        self.refresh_grid(animate=True)

    def show_settings(self):
        self.window.open_settings()

    def refresh(self):
        self.rows = list(self.window.library.books())
        for widget,value in [(self.book_count,len(self.rows)),
                             (self.chapter_count,sum(r["chapter_count"] for r in self.rows))]:
            widget.setText(str(value) if value<10000 else f"{value/10000:.1f}万")
            widget.setToolTip(str(value))
        last = next((row for row in self.rows if row["last_read"]),None)
        try:
            self.resume.clicked.disconnect()
        except RuntimeError:
            pass
        if last:
            self.hero_title.setText(f"故事未完，继续《{last['title']}》")
            self.hero_title.setWordWrap(True)
            self.hero_desc.setText("书签已为你留好，从上次停下的地方继续。")
            self.resume.setText("继续阅读  →")
            self.resume.clicked.connect(lambda:self.window.open_book(last["id"],True))
        else:
            self.hero_title.setText("每一次翻页，都是新的相遇。")
            self.hero_desc.setText("导入一个文件夹，让散落的章节自动归位。")
            self.resume.setText("开始收藏  →")
            self.resume.clicked.connect(self.window.import_folder)
        self.refresh_grid()

    def refresh_grid(self, animate=False):
        self.motion.cancel()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        query = self.search.text().strip().casefold()
        rows = [r for r in self.rows if query in r["title"].casefold()]
        if self.filter == "reading":
            rows = [r for r in rows if r["last_read"] and r["finished"] < r["chapter_count"]]
        elif self.filter == "finished":
            rows = [r for r in rows if r["finished"] == r["chapter_count"]]
        if self.sort.currentIndex() == 1:
            rows.sort(key=lambda r:r["title"].casefold())
        elif self.sort.currentIndex() == 2:
            rows.sort(key=lambda r:r["updated"],reverse=True)
        title = {"all":"全部漫画","reading":"正在阅读","finished":"已读完"}[self.filter]
        self.count.setText(f"{title} · {len(rows)}")
        self.columns = max(1,self.scroll.viewport().width()//232)
        if not rows:
            empty = QWidget()
            layout = QVBoxLayout(empty)
            layout.setContentsMargins(24,40,24,40)
            layout.addWidget(label("还没有找到故事","section"))
            layout.addWidget(label("换个关键词试试，或导入你的第一本漫画。","muted"))
            layout.addWidget(button("选择漫画文件夹",self.window.import_folder))
            self.grid.addWidget(empty,0,0)
        for i,row in enumerate(rows):
            card = BookCard(row)
            card.opened.connect(self.window.open_book)
            card.menu_requested.connect(self.window.book_menu)
            self.grid.addWidget(card,i//self.columns,i%self.columns)
        if animate:
            self.motion.reveal("rise",200)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        columns = max(1,self.scroll.viewport().width()//232)
        if columns != self.columns:
            QTimer.singleShot(0,self.refresh_grid)


class BookDialog(QDialog):
    def __init__(self, window, book_id):
        super().__init__(window)
        self.window, self.book_id = window,book_id
        self.setWindowTitle("漫画详情")
        self.resize(720,670)
        self.setMinimumSize(560,500)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26,24,26,24)
        layout.setSpacing(15)
        heading = QHBoxLayout()
        self.title = label("","heading",True)
        heading.addWidget(self.title,1)
        heading.addWidget(button("重命名",self.rename))
        layout.addLayout(heading)
        self.info = label("","muted",True)
        layout.addWidget(self.info)
        actions = QHBoxLayout()
        actions.addWidget(button("继续阅读  →",self.resume,primary=True))
        actions.addWidget(button("更新章节",self.update_folder))
        actions.addWidget(button("打开漫画文件夹",lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(self.window.library.book(book_id)["folder"]))))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(label("章节目录","section"))
        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.itemDoubleClicked.connect(self.read_selected)
        layout.addWidget(self.list,1)
        foot = QHBoxLayout()
        foot.addWidget(label("双击章节阅读 · 拖动章节调整顺序","muted"),1)
        foot.addWidget(button("恢复自动排序",self.auto_sort,quiet=True))
        layout.addLayout(foot)
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(button("移出书架",self.remove,quiet=True))
        bottom.addStretch()
        bottom.addWidget(button("阅读所选章节",self.read_selected,primary=True))
        bottom.addWidget(button("关闭",self.accept))
        layout.addLayout(bottom)
        self.reload()
        self.motion = Motion(self,lambda:window.animations_enabled)

    def showEvent(self,event):
        super().showEvent(event)
        self.motion.reveal("zoom",200)

    def reload(self):
        book = self.window.library.book(self.book_id)
        self.title.setText(book["title"])
        chapters = self.window.library.chapters(self.book_id)
        self.info.setText(f"{len(chapters)} 个章节 · {sum(c['pages'] for c in chapters)} 页\n{book['folder']}")
        self.list.clear()
        for index,c in enumerate(chapters):
            marker = "✓" if c["completed"] else ("◷" if c["page"] else "○")
            missing = "  [文件缺失]" if not Path(c["path"]).is_file() else ""
            item = QListWidgetItem(f"{marker}  {index+1:02}   {c['title']}    ·    {c['pages']} 页{missing}")
            item.setData(Qt.ItemDataRole.UserRole,c["id"])
            item.setToolTip(f"识别章节号：{number_text(c['number'])}\n{c['path']}")
            self.list.addItem(item)
        self.list.setCurrentRow(0)

    def save_order(self):
        self.window.library.reorder(self.book_id,[self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())])

    def auto_sort(self):
        chapters = sorted(self.window.library.chapters(self.book_id),key=lambda c:chapter_sort_key(c["path"]))
        self.window.library.reorder(self.book_id,[c["id"] for c in chapters])
        self.reload()

    def rename(self):
        self.window.rename_book(self.book_id)
        self.title.setText(self.window.library.book(self.book_id)["title"])

    def update_folder(self):
        self.save_order()
        self.window.import_folder(self.window.library.book(self.book_id)["folder"],show_book=False)
        self.reload()

    def resume(self):
        self.save_order()
        self.accept()
        self.window.start_reading(self.book_id)

    def read_selected(self,*args):
        item = self.list.currentItem()
        if not item:
            return
        chapter_id = item.data(Qt.ItemDataRole.UserRole)
        self.save_order()
        self.accept()
        self.window.start_reading(self.book_id,chapter_id)

    def remove(self):
        if self.window.remove_book(self.book_id):
            self.accept()

    def done(self,result):
        if self.window.library.book(self.book_id):
            self.save_order()
        super().done(result)


class RenderSignals(QObject):
    done = Signal(int,object,int,str)


class RenderTask(QRunnable):
    def __init__(self, token, path, page, width, height, mode, double=False, rtl=False, dpr=1.0):
        super().__init__()
        self.token,self.path,self.page = token,path,page
        self.width,self.height,self.mode = width,height,mode
        self.double,self.rtl,self.dpr = double,rtl,dpr
        self.visible_pages = ()
        self.visual_order = ()
        self.started = False
        self.signals = RenderSignals()

    def run(self):
        self.started = True
        try:
            with fitz.open(self.path) as doc:
                if doc.needs_pass:
                    raise ValueError("PDF 已加密，请先移除密码后重新导入。")
                if self.page >= doc.page_count:
                    raise ValueError("PDF 页数已变化，请返回详情并点击“更新章节”。")
                self.visible_pages = reading_pages(self.page,doc.page_count,self.double)
                self.visual_order = tuple(reversed(self.visible_pages)) if self.rtl else self.visible_pages
                pages = [doc.load_page(index) for index in self.visual_order]
                ratios = [page.rect.width/max(1,page.rect.height) for page in pages]
                gutter = round(8*self.dpr) if len(pages)>1 else 0
                width,height = self.width*self.dpr,self.height*self.dpr
                available_height = ((width-gutter)/sum(ratios) if self.mode=="width" else
                    min((width-gutter)/sum(ratios),height) if self.mode=="fit" else
                    max(page.rect.height for page in pages)*float(self.mode)*self.dpr)
                # Bound the combined raster, rather than granting each page a full allocation.
                max_height = (-gutter+math.sqrt(gutter*gutter+4*sum(ratios)*11_800_000))/(2*sum(ratios))
                display_height = max(1,int(min(available_height,max_height)))
                widths = [max(1,round(display_height*ratio)) for ratio in ratios]
                image = QImage(sum(widths)+gutter,display_height,QImage.Format.Format_ARGB32_Premultiplied)
                image.fill(Qt.GlobalColor.transparent)
                painter = QPainter(image)
                try:
                    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    x = 0
                    for page,page_width in zip(pages,widths):
                        scale = display_height/max(1,page.rect.height)
                        pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False,colorspace=fitz.csRGB)
                        page_image = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
                        painter.drawImage(QRectF(x,0,page_width,display_height),page_image)
                        x += page_width+gutter
                finally:
                    painter.end()
                image.setDevicePixelRatio(self.dpr)
                self.signals.done.emit(self.token,image,doc.page_count,"")
        except Exception as exc:
            self.signals.done.emit(self.token,None,0,str(exc))


class ReaderPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.chapters = []
        self.book_id = None
        self.index = self.page = 0
        self.token = 0
        self.tasks = {}
        self.displayed_key = None
        self.displayed_pages = ()
        self.displayed_order = ()
        self.pending_transition = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.render)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        top = QFrame()
        top.setObjectName("readerHeader")
        toolbar = QHBoxLayout(top)
        toolbar.setContentsMargins(24,13,24,13)
        toolbar.setSpacing(12)
        back = button("书架",self.back)
        back.setObjectName("readerBack")
        back.setIcon(sidebar_icon("back"))
        back.setIconSize(QSize(16,16))
        toolbar.addWidget(back)
        heading = QVBoxLayout()
        heading.setSpacing(3)
        self.title = label("","readerTitle")
        self.title.setMaximumWidth(250)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
        self.chapter_meta = label("","readerMeta")
        heading.addWidget(self.title)
        heading.addWidget(self.chapter_meta)
        toolbar.addLayout(heading,1)
        toolbar.addStretch()
        self.chapter_combo = QComboBox()
        self.chapter_combo.setObjectName("readerChoice")
        self.chapter_combo.setMinimumWidth(140)
        self.chapter_combo.setMaximumWidth(210)
        self.chapter_combo.setToolTip("切换章节")
        self.chapter_combo.activated.connect(self.change_chapter)
        toolbar.addWidget(self.chapter_combo)
        self.view_mode = ReaderChoice("阅读布局",["相邻两页并排显示","逐页显示，适合窄屏"])
        self.view_mode.setObjectName("readerChoice")
        self.view_mode.addItems(["双页展开","单页阅读"])
        self.view_mode.setCurrentIndex(0 if window.ui_setting("reader_layout","double")=="double" else 1)
        self.view_mode.currentIndexChanged.connect(self.change_view)
        toolbar.addWidget(self.view_mode)
        self.mode = ReaderChoice("画面缩放",["完整显示当前单页或双页","按窗口宽度显示，可上下滚动"],separator_before=2)
        self.mode.setObjectName("readerChoice")
        self.mode.addItems(["适合画面","适合宽度","75%","100%","125%","150%","200%"])
        self.mode.setToolTip("画面缩放")
        self.mode.currentIndexChanged.connect(self.change_zoom)
        toolbar.addWidget(self.mode)
        self.rtl = QCheckBox("日漫方向",self)
        self.rtl.setChecked(window.ui_setting("reader_rtl","0")=="1")
        self.rtl.setToolTip("启用后：左方向键下一页，右方向键上一页")
        self.rtl.hide()
        self.rtl.toggled.connect(self.change_direction)
        self.toc_button = self.tool_button("contents","章节目录",self.toggle_toc)
        self.toc_button.setCheckable(True)
        toolbar.addWidget(self.toc_button)
        toolbar.addWidget(self.tool_button("settings","阅读设置",window.open_settings))
        toolbar.addWidget(self.tool_button("fullscreen","全屏 · F11",self.fullscreen))
        layout.addWidget(top)
        self.splitter = QSplitter()
        self.splitter.setHandleWidth(1)
        self.toc_panel = QFrame()
        self.toc_panel.setObjectName("readerToc")
        self.toc_panel.setMaximumWidth(300)
        toc_layout = QVBoxLayout(self.toc_panel)
        toc_layout.setContentsMargins(16,22,16,16)
        toc_layout.setSpacing(16)
        toc_header = QHBoxLayout()
        toc_header.addWidget(label("章节目录","section"),1)
        toc_header.addWidget(button("×",self.toggle_toc,quiet=True))
        toc_layout.addLayout(toc_header)
        self.toc_count = label("","readerMeta")
        toc_layout.addWidget(self.toc_count)
        self.toc = QListWidget()
        self.toc.setObjectName("readerChapters")
        self.toc.setMinimumWidth(0)
        self.toc.currentRowChanged.connect(self.change_chapter)
        toc_layout.addWidget(self.toc,1)
        self.splitter.addWidget(self.toc_panel)
        self.toc_panel.hide()
        desk = QWidget()
        desk.setObjectName("readerDesk")
        desk_layout = QHBoxLayout(desk)
        desk_layout.setContentsMargins(16,24,16,24)
        desk_layout.setSpacing(8)
        self.prev_button = button("‹",lambda:self.move(1 if self.rtl.isChecked() else -1))
        self.prev_button.setObjectName("readerPager")
        self.prev_button.setFixedSize(38,38)
        desk_layout.addWidget(self.prev_button)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll.setStyleSheet("QScrollArea {background:transparent;} QScrollArea>QWidget>QWidget {background:transparent;}")
        self.scroll.viewport().setAutoFillBackground(False)
        self.page_host = QWidget()
        page_layout = QVBoxLayout(self.page_host)
        page_layout.setContentsMargins(4,4,4,4)
        self.image = QLabel("选择一个章节开始阅读")
        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image.setStyleSheet("color:#7a8b6d;background:transparent;")
        self.image.setTextFormat(Qt.TextFormat.PlainText)
        page_layout.addWidget(self.image,0,Qt.AlignmentFlag.AlignCenter)
        self.scroll.setWidget(self.page_host)
        self.page_motion = Motion(self.scroll.viewport(),lambda:window.animations_enabled)
        desk_layout.addWidget(self.scroll,1)
        self.next_button = button("›",lambda:self.move(-1 if self.rtl.isChecked() else 1))
        self.next_button.setObjectName("readerPager")
        self.next_button.setFixedSize(38,38)
        desk_layout.addWidget(self.next_button)
        self.splitter.addWidget(desk)
        self.splitter.setSizes([0,1000])
        self.splitter.splitterMoved.connect(lambda:self.schedule_render())
        self.toc_open = False
        self.toc_width = 230
        self.toc_animation = QVariantAnimation(self)
        self.toc_animation.setDuration(220)
        self.toc_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toc_animation.valueChanged.connect(self.move_toc)
        self.toc_animation.finished.connect(self.finish_toc)
        layout.addWidget(self.splitter,1)
        footer = QFrame()
        footer.setObjectName("readerFooter")
        bottom = QHBoxLayout(footer)
        bottom.setContentsMargins(28,12,28,12)
        bottom.setSpacing(14)
        self.status = label("","readerMeta")
        bottom.addWidget(self.status,1)
        self.page_effect = QComboBox(self)
        self.page_effect.addItems(["滑动翻页","淡入淡出","翻书效果","关闭翻页动画"])
        self.page_effect.setToolTip("选择翻页和章节切换的过渡效果")
        saved = window.ui_setting("page_effect","slide")
        self.page_effect.setCurrentIndex({"slide":0,"fade":1,"turn":2,"none":3}.get(saved,0))
        self.page_effect.currentIndexChanged.connect(self.change_page_effect)
        self.page_effect.hide()
        self.page_spin = QLineEdit()
        self.page_spin.setObjectName("readerPageJump")
        self.page_spin.setFixedSize(54,30)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setAccessibleName("跳转页码")
        self.page_spin.setToolTip("输入页码，按回车跳转")
        self.page_validator = QIntValidator(1,999999,self.page_spin)
        self.page_spin.setValidator(self.page_validator)
        self.page_spin.editingFinished.connect(self.jump_text)
        bottom.addWidget(self.page_spin)
        self.page_total = label("/ 0","readerMeta")
        self.page_total.setMinimumWidth(76)
        self.page_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom.addWidget(self.page_total)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setObjectName("readerProgress")
        self.progress_slider.setMinimumWidth(140)
        self.progress_slider.setMaximumWidth(260)
        self.progress_slider.setAccessibleName("阅读进度")
        self.progress_slider.sliderReleased.connect(lambda:self.go_page(self.progress_slider.value()))
        self.progress_slider.valueChanged.connect(lambda value:self.go_page(value) if not self.progress_slider.isSliderDown() else None)
        bottom.addWidget(self.progress_slider,2)
        bottom.addStretch()
        self.direction_hint = label("","readerMeta")
        bottom.addWidget(self.direction_hint,1,Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)
        for key,callback in [("Right",lambda:self.move(-1 if self.rtl.isChecked() else 1)),
                             ("Left",lambda:self.move(1 if self.rtl.isChecked() else -1)),
                             ("PgDown",lambda:self.move(1)),("PgUp",lambda:self.move(-1)),
                             ("Space",lambda:self.move(1)),("Home",lambda:self.go_page(0)),
                             ("End",lambda:self.go_page(self.chapters[self.index]["pages"]-1) if self.chapters else None),
                             ("F11",self.fullscreen),("Escape",self.escape)]:
            shortcut = QShortcut(QKeySequence(key),self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)

    def tool_button(self,icon,title,callback):
        control = button("",callback)
        control.setObjectName("readerTool")
        control.setIcon(sidebar_icon(icon))
        control.setIconSize(QSize(18,18))
        control.setFixedSize(34,34)
        control.setToolTip(title)
        control.setAccessibleName(title)
        return control

    def double_page(self):
        return self.view_mode.currentIndex()==0

    def change_view(self):
        self.prepare_page_transition(kind="fade")
        self.window.save_ui_setting("reader_layout","double" if self.double_page() else "single")
        if self.chapters:
            self.page = reading_pages(self.page,self.chapters[self.index]["pages"],self.double_page())[0]
            self.update_controls()
        self.schedule_render()

    def change_direction(self,checked):
        self.prepare_page_transition(kind="fade")
        self.window.save_ui_setting("reader_rtl","1" if checked else "0")
        if self.chapters:
            self.update_controls()
        self.schedule_render()

    def toggle_toc(self):
        self.toc_animation.stop()
        width = self.splitter.sizes()[0] if self.toc_panel.isVisible() else 0
        if self.toc_open and width>=170:
            self.toc_width = width
        self.toc_open = not self.toc_open
        if not self.window.animations_enabled:
            self.finish_toc()
            return
        self.toc_panel.setMinimumWidth(0)
        self.toc_panel.show()
        self.toc_button.setChecked(self.toc_open)
        self.move_toc(width)
        self.toc_animation.setStartValue(width)
        self.toc_animation.setEndValue(self.toc_width if self.toc_open else 0)
        self.toc_animation.start()

    def move_toc(self, width):
        total = max(1,sum(self.splitter.sizes()))
        self.splitter.setSizes([int(width),max(1,total-int(width))])

    def finish_toc(self):
        self.toc_animation.stop()
        self.toc_panel.setMinimumWidth(200 if self.toc_open else 0)
        self.toc_panel.setVisible(self.toc_open)
        self.toc_button.setChecked(self.toc_open)
        if self.toc_open:
            self.move_toc(self.toc_width)
        self.schedule_render()

    def change_page_effect(self, index):
        self.page_motion.cancel()
        self.pending_transition = None
        self.window.save_ui_setting("page_effect",["slide","fade","turn","none"][index])

    def prepare_page_transition(self, direction=1, kind=None):
        self.pending_transition = None
        choice = kind or ["slide","fade","turn",None][self.page_effect.currentIndex()]
        if choice and self.displayed_key and self.window.animations_enabled:
            before = self.page_motion.capture()
            physical_direction = -direction if self.rtl.isChecked() else direction
            self.pending_transition = before,choice,physical_direction
        else:
            self.page_motion.cancel()

    def change_zoom(self):
        self.prepare_page_transition(kind="fade")
        self.schedule_render()

    def load(self, book_id, chapter_id=None):
        self.token += 1
        self.timer.stop()
        self.page_motion.cancel()
        self.pending_transition = None
        self.displayed_key = None
        self.displayed_pages = ()
        self.displayed_order = ()
        self.image.clear()
        self.image.setFixedSize(300,100)
        self.image.setText("正在加载页面…")
        self.book_id = book_id
        book = self.window.library.book(book_id)
        self.title.setText(book["title"])
        self.title.setToolTip(book["title"])
        self.chapters = list(self.window.library.chapters(book_id))
        self.chapter_combo.blockSignals(True)
        self.toc.blockSignals(True)
        self.chapter_combo.clear()
        self.toc.clear()
        for i,c in enumerate(self.chapters):
            title = f"{i+1:02}  {c['title']}"
            self.chapter_combo.addItem(title)
            self.toc.addItem(title)
        self.chapter_combo.blockSignals(False)
        self.toc.blockSignals(False)
        self.toc_count.setText(f"共 {len(self.chapters)} 个章节")
        target = chapter_id or book["last_chapter"]
        index = next((i for i,c in enumerate(self.chapters) if c["id"]==target),0)
        self.change_chapter(index)

    def change_chapter(self, index, at_end=False, restart=False):
        if not self.chapters or not 0<=index<len(self.chapters):
            return
        self.prepare_page_transition(1 if index>=self.index else -1)
        self.index = index
        self.page = self.chapters[index]["pages"]-1 if at_end else (0 if restart else self.chapters[index]["page"])
        self.page = reading_pages(self.page,self.chapters[index]["pages"],self.double_page())[0]
        self.chapter_combo.blockSignals(True)
        self.toc.blockSignals(True)
        self.chapter_combo.setCurrentIndex(index)
        self.toc.setCurrentRow(index)
        self.chapter_combo.blockSignals(False)
        self.toc.blockSignals(False)
        self.update_controls()
        self.schedule_render()

    def update_controls(self):
        pages = self.chapters[self.index]["pages"]
        self.page_spin.blockSignals(True)
        self.page_validator.setRange(1,pages)
        self.page_spin.setText(str(self.page+1))
        self.page_spin.blockSignals(False)
        visible = reading_pages(self.page,pages,self.double_page())
        self.page_total.setText(f"— {visible[-1]+1} / {pages} 页" if len(visible)>1 else f"/ {pages} 页")
        self.status.setText(f"章节 {self.index+1:02} / {len(self.chapters):02}")
        self.chapter_meta.setText(f"{len(self.chapters)} 个章节  ·  {self.chapters[self.index]['pages']} 页")
        self.progress_slider.blockSignals(True)
        self.progress_slider.setRange(0,reading_pages(pages-1,pages,self.double_page())[0])
        self.progress_slider.setValue(self.page)
        self.progress_slider.blockSignals(False)
        previous = self.index>0 or self.page>0
        following = self.index+1<len(self.chapters) or visible[-1]<pages-1
        self.prev_button.setEnabled(following if self.rtl.isChecked() else previous)
        self.next_button.setEnabled(previous if self.rtl.isChecked() else following)
        self.prev_button.setToolTip("下一组" if self.rtl.isChecked() else "上一组")
        self.next_button.setToolTip("上一组" if self.rtl.isChecked() else "下一组")
        self.direction_hint.setText(("从右向左" if self.rtl.isChecked() else "从左向右")+"  ·  "+("双页" if self.double_page() else "单页"))

    def jump(self,value):
        self.go_page(value-1)

    def jump_text(self):
        if not self.chapters:
            return
        try:
            self.go_page(int(self.page_spin.text())-1)
        except ValueError:
            self.page_spin.setText(str(self.page+1))

    def go_page(self,page):
        if not self.chapters:
            return
        target = reading_pages(page,self.chapters[self.index]["pages"],self.double_page())[0]
        if target != self.page:
            self.prepare_page_transition(1 if target>self.page else -1)
        self.page = target
        self.update_controls()
        self.schedule_render()

    def move(self,delta):
        if not self.chapters:
            return
        target = self.page+delta*(2 if self.double_page() else 1)
        if target<0:
            if self.index>0:
                self.change_chapter(self.index-1,at_end=True)
        elif target>=self.chapters[self.index]["pages"]:
            if self.index+1<len(self.chapters):
                self.change_chapter(self.index+1,restart=True)
            else:
                self.status.setText("本书已读完。可切换章节重读，或返回书架。")
        else:
            self.go_page(target)

    def schedule_render(self):
        self.token += 1
        self.timer.start(80)

    def render(self):
        if not self.chapters or not self.isVisible():
            return
        self.pool.clear()
        self.tasks = {key:task for key,task in self.tasks.items() if task.started}
        mode = ["fit","width",.75,1,1.25,1.5,2][self.mode.currentIndex()]
        task = RenderTask(self.token,self.chapters[self.index]["path"],self.page,
                          max(80,self.scroll.viewport().width()-16),
                          max(80,self.scroll.viewport().height()-16),mode,
                          self.double_page(),self.rtl.isChecked(),self.devicePixelRatioF())
        task.signals.done.connect(self.rendered)
        self.tasks[self.token] = task
        if not self.image.pixmap() or self.image.pixmap().isNull():
            self.image.setText("正在加载页面…")
        self.pool.start(task)

    def rendered(self, token, image, pages, error):
        task = self.tasks.pop(token,None)
        if token != self.token or not self.isVisible():
            return
        if error:
            self.page_motion.cancel()
            self.pending_transition = None
            self.displayed_key = None
            self.displayed_pages = ()
            self.displayed_order = ()
            self.image.clear()
            self.image.setText("暂时无法打开此页\n\n"+error+"\n\n请检查漫画库中的文件，或重新导入该漫画。")
            self.image.setFixedSize(640,220)
            self.status.setText("页面加载失败；阅读进度未更新")
            return
        pixmap = QPixmap.fromImage(image)
        self.image.setPixmap(pixmap)
        self.image.setFixedSize(round(image.width()/image.devicePixelRatio()),round(image.height()/image.devicePixelRatio()))
        self.scroll.verticalScrollBar().setValue(0)
        self.scroll.horizontalScrollBar().setValue(0)
        chapter = self.chapters[self.index]
        self.displayed_key = chapter["id"],self.page
        self.displayed_pages = task.visible_pages
        self.displayed_order = task.visual_order
        if self.pending_transition:
            before,kind,direction = self.pending_transition
            self.pending_transition = None
            self.page_motion.play(before,kind,direction,260 if kind=="turn" else 190)
        last_visible = self.displayed_pages[-1]
        self.window.library.progress(chapter["id"],last_visible,last_visible==pages-1)
        self.chapters = list(self.window.library.chapters(self.book_id))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.schedule_render()

    def fullscreen(self):
        if self.window.isFullScreen():
            self.window.showNormal()
        else:
            self.window.showFullScreen()

    def escape(self):
        if self.window.isFullScreen():
            self.window.showNormal()
        else:
            self.back()

    def back(self):
        before = self.window.stack_motion.capture()
        self.token += 1
        self.timer.stop()
        self.page_motion.cancel()
        self.pending_transition = None
        self.finish_toc()
        self.timer.stop()
        if self.window.isFullScreen():
            self.window.showNormal()
        self.window.stack.setCurrentIndex(0)
        self.window.library_page.refresh()
        self.window.stack_motion.play(before,"slide",-1,240)


class MainWindow(QMainWindow):
    def __init__(self, data_dir, comics_dir=None):
        super().__init__()
        self.library = Library(data_dir,comics_dir)
        self.settings_dialog = None
        self.animations_enabled = self.ui_setting("animations","1") != "0"
        self.scanning_library = False
        self.setWindowTitle("墨间 · 漫画阅读器")
        self.setWindowIcon(application_icon())
        self.resize(1280,860)
        self.setMinimumSize(1020,680)
        self.setAcceptDrops(True)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.library_page = LibraryPage(self)
        self.reader = ReaderPage(self)
        self.stack.addWidget(self.library_page)
        self.stack.addWidget(self.reader)
        self.stack_motion = Motion(self.stack,lambda:self.animations_enabled)
        self.library_page.refresh()
        shortcut = QShortcut(QKeySequence("Ctrl+O"),self)
        shortcut.activated.connect(self.import_folder)

    def ui_setting(self,key,default):
        row = self.library.db.execute("SELECT value FROM settings WHERE key=?",("ui_"+key,)).fetchone()
        return row[0] if row else default

    def save_ui_setting(self,key,value):
        with self.library.db:
            self.library.db.execute("INSERT OR REPLACE INTO settings VALUES(?,?)",("ui_"+key,str(value)))

    def set_animations(self,enabled):
        self.animations_enabled = enabled
        self.save_ui_setting("animations","1" if enabled else "0")
        if not enabled:
            for motion in self.findChildren(Motion):
                motion.cancel()
            self.reader.pending_transition = None
            self.reader.finish_toc()

    def open_comics(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.library.comics_dir)))

    def open_settings(self,section="reading"):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.select_section(1 if section=="library" else 0,animate=False)
        self.settings_dialog.exec()

    def scan_library(self, only_new=False):
        if self.scanning_library:
            return
        self.scanning_library = True
        try:
            folders = (self.library.unregistered_folders() if only_new else
                       [p for p in sorted(self.library.comics_dir.iterdir())
                        if p.is_dir() and not p.name.startswith(".") and not p.is_symlink() and not p.is_junction()])
            for folder in folders:
                if not pdf_files(folder):
                    continue
                dialog = ImportDialog(self.library,folder,self,auto_commit=True)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    break
            self.library_page.refresh()
        except Exception as exc:
            QMessageBox.warning(self,"扫描未完成",str(exc))
        finally:
            self.scanning_library = False

    def import_folder(self, folder=None, show_book=True):
        if not isinstance(folder,(str,Path)):
            folder = QFileDialog.getExistingDirectory(self,"选择漫画文件夹：每个 PDF 是一个章节")
        if not folder:
            return
        if not Path(folder).is_dir():
            QMessageBox.warning(self,"文件夹不可用","原文件夹不存在或无法访问。请重新选择文件夹。")
            return
        if Path(folder).resolve() == self.library.comics_dir:
            self.scan_library()
            return
        try:
            dialog = ImportDialog(self.library,folder,self)
        except ValueError as exc:
            QMessageBox.warning(self,"无法导入",str(exc))
            return
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.library_page.refresh()
            if show_book:
                self.open_book(dialog.book_id)

    def open_book(self, book_id, resume=False):
        if resume:
            self.start_reading(book_id)
        else:
            BookDialog(self,book_id).exec()
            self.library_page.refresh()

    def start_reading(self,book_id,chapter_id=None):
        before = self.stack_motion.capture()
        self.stack.setCurrentIndex(1)
        self.reader.load(book_id,chapter_id)
        self.stack_motion.play(before,"slide",1,240)

    def rename_book(self,book_id):
        book = self.library.book(book_id)
        text,ok = QInputDialog.getText(self,"修改漫画名称","漫画名称：",text=book["title"])
        if ok:
            if not text.strip():
                QMessageBox.warning(self,"名称不能为空","请填写漫画名称。")
                return
            self.library.rename(book_id,text)
            self.library_page.refresh()

    def remove_book(self,book_id):
        book = self.library.book(book_id)
        answer = QMessageBox.question(self,"移出书架",f"将《{book['title']}》移出书架？\n书架记录和阅读进度将被清除，原 PDF 文件保留。")
        if answer==QMessageBox.StandardButton.Yes:
            self.library.remove(book_id)
            self.library_page.refresh()
            return True
        return False

    def book_menu(self,book_id,point):
        menu = QMenu(self)
        menu.addAction("继续阅读",lambda:self.start_reading(book_id))
        menu.addAction("章节目录",lambda:self.open_book(book_id))
        menu.addAction("修改漫画名称",lambda:self.rename_book(book_id))
        menu.addAction("更新章节",lambda:self.import_folder(self.library.book(book_id)["folder"]))
        menu.addSeparator()
        menu.addAction("移出书架",lambda:self.remove_book(book_id))
        menu.exec(point)

    def help(self):
        self.open_settings("library")

    def dragEnterEvent(self,event):
        if event.mimeData().hasUrls() and any(Path(u.toLocalFile()).is_dir() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self,event):
        folders = [u.toLocalFile() for u in event.mimeData().urls() if Path(u.toLocalFile()).is_dir()]
        for folder in folders:
            self.import_folder(folder)
        event.acceptProposedAction()

    def closeEvent(self,event):
        for motion in self.findChildren(Motion):
            motion.cancel()
        self.reader.toc_animation.stop()
        self.reader.token += 1
        self.reader.timer.stop()
        self.reader.pool.clear()
        self.reader.pool.waitForDone()
        self.library.close()
        event.accept()


def main():
    parser = argparse.ArgumentParser(description="墨间 PDF 漫画阅读器")
    parser.add_argument("--data-dir",type=Path)
    parser.add_argument("--self-check",type=Path,help=argparse.SUPPRESS)
    args = parser.parse_args()
    base = Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent
    data_dir = args.data_dir or base/"data"
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MangaShelf.Mojian.Reader")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("墨间")
    app.setOrganizationName("MangaShelf")
    app.setWindowIcon(application_icon())
    load_fonts()
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    app.setFont(QFont("Microsoft YaHei UI",10))
    try:
        window = MainWindow(data_dir,None if args.data_dir else base/"comics")
    except Exception as exc:
        QMessageBox.critical(None,"无法启动墨间",f"无法创建或读取本地书架。请将软件放在可写入的文件夹中。\n\n{exc}")
        return 1

    def handle_error(kind,value,tb):
        detail = "".join(traceback.format_exception(kind,value,tb))
        try:
            with (data_dir/"errors.log").open("a",encoding="utf-8") as stream:
                stream.write(detail+"\n")
        except OSError:
            pass
        QMessageBox.warning(window,"操作失败",f"{value}\n\n可在 data/errors.log 中查看详情。")

    sys.excepthook = handle_error
    window.show()
    if not args.self_check:
        QTimer.singleShot(0,lambda:window.scan_library(only_new=True))
    if args.self_check:
        def self_check():
            try:
                with fitz.open() as doc:
                    doc.new_page(width=100,height=100)
                    pix = doc[0].get_pixmap()
                    assert pix.width == 100
                args.self_check.parent.mkdir(parents=True,exist_ok=True)
                window.grab().save(str(args.self_check.with_suffix(".png")))
                args.self_check.write_text("Qt UI / Chinese fonts / SQLite / PDF renderer: OK",encoding="utf-8")
                window.close()
            except Exception as exc:
                args.self_check.write_text(str(exc),encoding="utf-8")
                app.exit(1)
        QTimer.singleShot(300,self_check)
    return app.exec()

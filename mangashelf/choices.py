"""Compact reader controls with consistent, keyboard-accessible option panels."""
from PySide6.QtCore import Qt, QSize, QRectF, QPoint, QEvent
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QFrame, QListWidget, QListWidgetItem,
    QVBoxLayout, QLabel, QStyledItemDelegate, QStyle, QApplication, QWidget)


class ChoiceDelegate(QStyledItemDelegate):
    def __init__(self,combo):
        super().__init__(combo)
        self.combo = combo

    def sizeHint(self,option,index):
        row = index.row()
        description = self.combo.description(row)
        gap = 9 if row==self.combo.separator_before else 0
        return QSize(220,(55 if description else 35)+gap)

    def paint(self,painter,option,index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        row = index.row()
        rect = QRectF(option.rect).adjusted(3,2,-3,-2)
        if row==self.combo.separator_before:
            painter.setPen(QPen(QColor("#e6ebdf"),1))
            painter.drawLine(rect.topLeft()+QPoint(9,2),rect.topRight()+QPoint(-9,2))
            rect.adjust(0,9,0,0)
        chosen = row==self.combo.currentIndex()
        hovered = bool(option.state & (QStyle.StateFlag.State_Selected|QStyle.StateFlag.State_MouseOver))
        painter.setPen(Qt.PenStyle.NoPen)
        if chosen or hovered:
            painter.setBrush(QColor("#e9f0e1" if chosen else "#f2f5eb"))
            painter.drawRoundedRect(rect,7,7)
        description = self.combo.description(row)
        font = QFont(option.font)
        font.setPixelSize(12)
        font.setWeight(QFont.Weight.Medium if chosen else QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#35533c" if chosen else "#53654a"))
        text = rect.adjusted(13,0,-33,0)
        if description:
            title = QRectF(text.left(),text.top()+7,text.width(),19)
            painter.drawText(title,Qt.AlignmentFlag.AlignVCenter,str(index.data()))
            font.setPixelSize(10)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(QColor("#89967f"))
            painter.drawText(QRectF(text.left(),text.top()+27,text.width(),15),
                             Qt.AlignmentFlag.AlignVCenter,description)
        else:
            painter.drawText(text,Qt.AlignmentFlag.AlignVCenter,str(index.data()))
        if chosen:
            x,y = rect.right()-19,rect.center().y()
            check = QPainterPath()
            check.moveTo(x-4,y)
            check.lineTo(x-1,y+3)
            check.lineTo(x+5,y-4)
            painter.setPen(QPen(QColor("#6d8a59"),1.6,Qt.PenStyle.SolidLine,
                                 Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(check)
        painter.restore()


class ChoicePopup(QFrame):
    def __init__(self,combo):
        super().__init__(combo,Qt.WindowType.Popup|Qt.WindowType.FramelessWindowHint|
                               Qt.WindowType.NoDropShadowWindowHint)
        self.combo = combo
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("readerChoicePopup")
        self.setFixedWidth(262)
        self.setStyleSheet("""
            QFrame#readerChoicePopup {background:#fffef8; border:1px solid #d9e2d0; border-radius:12px;}
            QLabel#choiceHeading {font-size:10px; font-weight:600; color:#98a18d; padding:3px 10px 5px;}
            QListWidget#readerOptionList {background:transparent; border:0; padding:0; outline:0;}
            QListWidget#readerOptionList::item {border:0; padding:0; background:transparent;}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(7,10,7,7)
        layout.setSpacing(2)
        heading = QLabel(combo.popup_title)
        heading.setObjectName("choiceHeading")
        layout.addWidget(heading)
        self.options = QListWidget()
        self.options.setObjectName("readerOptionList")
        self.options.setMouseTracking(True)
        self.options.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.options.setItemDelegate(ChoiceDelegate(combo))
        self.options.installEventFilter(combo)
        self.options.itemClicked.connect(self.choose)
        self.options.itemActivated.connect(self.choose)
        layout.addWidget(self.options)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#d9e2d0"),1))
        painter.setBrush(QColor("#fffef8"))
        painter.drawRoundedRect(QRectF(self.rect()).adjusted(.5,.5,-.5,-.5),12,12)
        painter.end()

    def choose(self,item):
        row = self.options.row(item)
        if row<0:
            return
        self.combo.setCurrentIndex(row)
        self.combo.hidePopup()
        self.combo.activated.emit(row)

    def hideEvent(self,event):
        QApplication.instance().removeEventFilter(self.combo)
        super().hideEvent(event)
        QComboBox.hidePopup(self.combo)
        self.combo.update()


class ReaderChoice(QComboBox):
    def __init__(self,title,descriptions=(),separator_before=None,parent=None):
        super().__init__(parent)
        self.popup_title = title
        self.descriptions = descriptions
        self.separator_before = separator_before
        self.popup = None
        self.setObjectName("readerChoice")
        self.setProperty("refinedPopup",True)
        self.setAccessibleName(title)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def description(self,row):
        return self.descriptions[row] if row<len(self.descriptions) else ""

    def showPopup(self):
        if self.popup is None:
            self.popup = ChoicePopup(self)
        options = self.popup.options
        options.clear()
        desired_height = 0
        for row in range(self.count()):
            item = QListWidgetItem(self.itemText(row))
            description = self.description(row)
            size = QSize(220,(55 if description else 35)+(9 if row==self.separator_before else 0))
            item.setSizeHint(size)
            item.setToolTip(self.itemText(row)+(f" · {description}" if description else ""))
            options.addItem(item)
            desired_height += size.height()
        options.setCurrentRow(self.currentIndex())
        available = self.screen().availableGeometry()
        options.setFixedHeight(min(desired_height,max(80,available.height()-100)))
        self.popup.adjustSize()
        bottom = self.mapToGlobal(self.rect().bottomRight())
        x = max(available.left()+8,min(bottom.x()-self.popup.width()+1,available.right()-self.popup.width()-8))
        y = bottom.y()+8
        if y+self.popup.height()>available.bottom()-8:
            y = self.mapToGlobal(self.rect().topLeft()).y()-self.popup.height()-8
        y = max(available.top()+8,y)
        self.popup.move(x,y)
        self.popup.show()
        QApplication.instance().installEventFilter(self)
        options.setFocus(Qt.FocusReason.PopupFocusReason)
        options.scrollToItem(options.currentItem())
        self.update()

    def hidePopup(self):
        if self.popup:
            self.popup.hide()
        super().hidePopup()
        self.update()

    def hideEvent(self,event):
        self.hidePopup()
        super().hideEvent(event)

    def eventFilter(self,watched,event):
        if (self.popup and self.popup.isVisible() and event.type()==QEvent.Type.MouseButtonPress
                and isinstance(watched,QWidget) and watched is not self.popup
                and not self.popup.isAncestorOf(watched)):
            self.hidePopup()
            if watched is self or self.isAncestorOf(watched):
                return True
        if self.popup and watched is self.popup.options:
            keys = (Qt.Key.Key_Escape,Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Up,Qt.Key.Key_Down,
                    Qt.Key.Key_Home,Qt.Key.Key_End,Qt.Key.Key_PageUp,Qt.Key.Key_PageDown,Qt.Key.Key_Space)
            if event.type()==QEvent.Type.ShortcutOverride and event.key() in keys:
                event.accept()
                return True
            if event.type()==QEvent.Type.KeyPress:
                if event.key()==Qt.Key.Key_Escape:
                    self.hidePopup()
                    self.setFocus(Qt.FocusReason.PopupFocusReason)
                    return True
                if event.key() in (Qt.Key.Key_Return,Qt.Key.Key_Enter,Qt.Key.Key_Space):
                    item = self.popup.options.currentItem()
                    if item:
                        self.popup.choose(item)
                    return True
        return super().eventFilter(watched,event)

    def paintEvent(self,event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#819473"),1.3,Qt.PenStyle.SolidLine,
                             Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        x,y = self.width()-14,self.height()/2
        direction = -1 if self.popup and self.popup.isVisible() else 1
        path = QPainterPath()
        path.moveTo(x-3,y-1.5*direction)
        path.lineTo(x,y+1.5*direction)
        path.lineTo(x+3,y-1.5*direction)
        painter.drawPath(path)
        painter.end()

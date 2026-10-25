"""Short, interruptible Qt transitions using viewport-sized snapshots."""
from PySide6.QtCore import QObject, QEvent, QTimer, QVariantAnimation, QEasingCurve, QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPixmap
from PySide6.QtWidgets import QWidget


class TransitionLayer(QWidget):
    def __init__(self, host, snapshot, kind, direction, incoming, duration, finished):
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setObjectName("transitionLayer")
        self.setStyleSheet("QWidget#transitionLayer {background:transparent; border:0;}")
        self.snapshot,self.kind,self.direction,self.incoming = snapshot,kind,direction,incoming
        self.progress = 0.0
        self.setGeometry(host.rect())
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(duration)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(self.advance)
        self.animation.finished.connect(finished)

    def advance(self, value):
        self.progress = float(value)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        source = QRectF(self.snapshot.rect())
        progress = self.progress
        if self.incoming:
            painter.fillRect(rect,QColor("#f6f5f0"))
            painter.setOpacity(progress)
            if self.kind == "zoom":
                scale = .965+.035*progress
                target = QRectF(0,0,rect.width()*scale,rect.height()*scale)
                target.moveCenter(rect.center())
            else:
                target = rect.translated(0,12*(1-progress))
            painter.drawPixmap(target,self.snapshot,source)
        elif self.kind == "turn":
            width = rect.width()*(1-progress)
            x = 0 if self.direction>0 else rect.width()-width
            target = QRectF(x,0,width,rect.height())
            painter.setOpacity(1-progress*.25)
            painter.drawPixmap(target,self.snapshot,source)
        else:
            painter.setOpacity(1-progress)
            offset = -self.direction*40*progress if self.kind == "slide" else 0
            painter.drawPixmap(rect.translated(offset,0),self.snapshot,source)
        painter.end()


class Motion(QObject):
    """One active transition per host; real controls remain interactive underneath."""
    def __init__(self, host, enabled=lambda:True):
        super().__init__(host)
        self.host,self.enabled = host,enabled
        self.layer = None
        self.pending = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._reveal)
        host.installEventFilter(self)

    def capture(self):
        self.cancel()
        if not self.enabled() or not self.host.isVisible() or self.host.size().isEmpty():
            return QPixmap()
        return self.host.grab()

    def play(self, before, kind="fade", direction=1, duration=220, incoming=False):
        self.cancel()
        if before.isNull() or not self.enabled() or not self.host.isVisible():
            return
        self.layer = TransitionLayer(self.host,before,kind,direction,incoming,duration,self.cancel)
        self.layer.show()
        self.layer.raise_()
        self.layer.animation.start()

    def reveal(self, kind="rise", duration=220):
        self.cancel()
        if self.enabled():
            self.pending = kind,duration
            self.timer.start(0)

    def _reveal(self):
        if self.pending and self.host.isVisible():
            kind,duration = self.pending
            snapshot = self.host.grab()
            self.play(snapshot,kind=kind,duration=duration,incoming=True)

    def cancel(self):
        self.timer.stop()
        self.pending = None
        if self.layer:
            layer,self.layer = self.layer,None
            layer.animation.stop()
            layer.hide()
            layer.deleteLater()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize,QEvent.Type.Hide):
            self.cancel()
        return False

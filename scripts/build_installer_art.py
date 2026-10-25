"""Create installer branding from the application's editable vector icon."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from mangashelf.app import load_fonts


def main():
    app = QApplication.instance() or QApplication([])
    load_fonts()
    root = Path(__file__).resolve().parents[1]
    output = root/"installer"/"assets"
    output.mkdir(parents=True,exist_ok=True)
    icon = QSvgRenderer(str(root/"mangashelf"/"assets"/"mangashelf.svg"))
    for scale in [1,2]:
        image = QImage(164*scale,314*scale,QImage.Format.Format_RGB32)
        image.fill(QColor("#294735"))
        painter = QPainter(image)
        painter.scale(scale,scale)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        icon.render(painter,QRectF(22,45,120,120))
        painter.setPen(QColor("#fbf8e9"))
        font = QFont("Microsoft YaHei UI")
        font.setPixelSize(27)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.drawText(QRectF(22,182,125,40),Qt.AlignmentFlag.AlignLeft,"墨间")
        font.setPixelSize(10)
        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(QColor("#c3cfb6"))
        painter.drawText(QRectF(22,229,125,20),Qt.AlignmentFlag.AlignLeft,"安静阅读，故事继续。")
        font.setPixelSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#91a488"))
        painter.drawText(QRectF(22,279,130,16),Qt.AlignmentFlag.AlignLeft,"MANGA SHELF")
        painter.end()
        assert image.save(str(output/f"wizard-{scale}x.bmp"),"BMP")
    small = QImage(55,55,QImage.Format.Format_RGB32)
    small.fill(QColor("#ffffff"))
    painter = QPainter(small)
    icon.render(painter,QRectF(4,4,47,47))
    painter.end()
    assert small.save(str(output/"wizard-small.bmp"),"BMP")
    print("Installer branding generated")


if __name__ == "__main__":
    main()

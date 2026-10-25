"""Render the editable SVG and write a multi-resolution Windows ICO using Qt."""
import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from pathlib import Path
import struct

from PySide6.QtCore import Qt, QRectF, QBuffer, QIODevice
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication


def render(renderer, size):
    image = QImage(size,size,QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter,QRectF(0,0,size,size))
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer,"PNG"):
        raise RuntimeError("Unable to encode icon")
    return bytes(buffer.data())


def main():
    app = QApplication.instance() or QApplication([])
    assets = Path(__file__).resolve().parents[1]/"mangashelf"/"assets"
    renderer = QSvgRenderer(str(assets/"mangashelf.svg"))
    if not renderer.isValid():
        raise RuntimeError("Invalid SVG icon")
    (assets/"mangashelf.png").write_bytes(render(renderer,512))
    sizes = [16,20,24,32,40,48,64,96,128,256]
    encoded = [(size,render(renderer,size)) for size in sizes]
    offset = 6+16*len(encoded)
    header = struct.pack("<HHH",0,1,len(encoded))
    entries,images = [],[]
    for size,image in encoded:
        entries.append(struct.pack("<BBBBHHII",size%256,size%256,0,0,1,32,len(image),offset))
        images.append(image)
        offset += len(image)
    (assets/"mangashelf.ico").write_bytes(header+b"".join(entries)+b"".join(images))
    print("Generated SVG-based PNG and 10-resolution Windows ICO")


if __name__ == "__main__":
    main()

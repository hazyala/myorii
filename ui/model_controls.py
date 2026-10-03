from PyQt6.QtCore import Qt, QPoint, QRectF
from PyQt6.QtGui import QPainter, QPainterPath, QRegion, QPen
from PyQt6.QtWidgets import QLineEdit,QToolButton,QListView,QComboBox
from ui.preferences import tr, set_local_style, set_localized_text, color

class PasswordEdit(QLineEdit):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)
        self.toggle=QToolButton(self)
        self.toggle.setCheckable(True)
        self.toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        set_localized_text(self.toggle,'보기')
        self.toggle.toggled.connect(self._toggle)
        self.setTextMargins(0,0,52,0)
        self.setMinimumHeight(36)
    def _toggle(self,visible):
        self.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        set_localized_text(self.toggle,'가리기' if visible else '보기')
    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.toggle.setGeometry(self.width()-53,3,50,max(20,self.height()-6))
    def hide_secret(self):
        self.toggle.setChecked(False)


class ModelComboBox(QComboBox):
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color("#667085"),1.6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        x=self.width()-18
        y=self.height()/2
        path=QPainterPath()
        path.moveTo(x-4,y-2);path.lineTo(x,y+2);path.lineTo(x+4,y-2)
        painter.drawPath(path)

    def showPopup(self):
        if not self.count(): return
        super().showPopup()
        popup=self.view().window()
        # Position relative to the field, rather than the selected item's row.
        origin=self.mapToGlobal(QPoint(0,self.height()+4))
        screen=self.screen().availableGeometry()
        width=min(self.width(),screen.width())
        row_height=max(34,self.view().sizeHintForRow(0))
        height=min(self.count(),self.maxVisibleItems(),8)*row_height+12
        x=max(screen.left(),min(origin.x(),screen.right()-width+1))
        popup.resize(width,height)
        popup.move(x,origin.y())
        path=QPainterPath()
        path.addRoundedRect(QRectF(popup.rect()),10,10)
        popup.setMask(QRegion(path.toFillPolygon().toPolygon()))


def model_combo(parent=None):
    combo=ModelComboBox(parent)
    combo.setObjectName('modelComboBox')
    view=QListView(combo)
    view.setObjectName('modelPopupList')
    view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground,False)
    set_local_style(view, """
        QListView { background: #ffffff; color: #20242c;
            border: 1px solid #dfe4ed; border-radius: 8px;
            font-size: 12px; padding: 4px; outline: none; }
        QListView::item { min-height: 24px; padding: 4px 10px;
            border-radius: 5px; margin: 1px 0; }
        QListView::item:selected { background: #e8f2ff; color: #2f80ff; }
        QListView::item:hover { background: #f3f6fb; }
    """)
    view.setAutoFillBackground(True)
    view.viewport().setAutoFillBackground(True)
    combo.setView(view)
    combo.setFixedHeight(34)
    return combo

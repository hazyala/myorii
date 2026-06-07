from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.llm.chat_service import DEFAULT_MODEL
from ui.assets import asset_path, tinted_icon
from ui.widgets.switch_button import SwitchButton


class SegmentedControl(QFrame):
    changed = pyqtSignal(str)

    def __init__(self, options: tuple[str, ...], active_index: int = 0) -> None:
        super().__init__()
        self.setObjectName("segmentedControl")
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[QPushButton] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        for index, label in enumerate(options):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumWidth(58)
            button.setFixedHeight(30)
            self._group.addButton(button, index)
            self._buttons.append(button)
            layout.addWidget(button)

        self._buttons[active_index].setChecked(True)
        self._group.idClicked.connect(lambda index: self.changed.emit(self._buttons[index].text()))


class SettingsSection(QFrame):
    def __init__(self, title: str, icon_name: str) -> None:
        super().__init__()
        self.setObjectName("settingsSection")

        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(0)

        header = QFrame()
        header.setObjectName("settingsSectionHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(10)

        icon = QLabel()
        icon.setFixedSize(19, 19)
        icon.setPixmap(
            QPixmap(str(asset_path("icons", icon_name))).scaled(
                icon.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        label = QLabel(title)
        label.setObjectName("settingsSectionTitle")

        header_layout.addWidget(icon)
        header_layout.addWidget(label)
        header_layout.addStretch(1)
        self.body.addWidget(header)

    def add_row(self, row: QWidget) -> None:
        self.body.addWidget(row)


class SettingsRow(QFrame):
    def __init__(self, title: str, subtitle: str | None = None, accent: bool = False) -> None:
        super().__init__()
        self.setObjectName("settingsRowAccent" if accent else "settingsRow")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(14, 11, 14, 11)
        self.layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        label = QLabel(title)
        label.setObjectName("settingsRowTitleAccent" if accent else "settingsRowTitle")
        text_layout.addWidget(label)

        if subtitle:
            caption = QLabel(subtitle)
            caption.setObjectName("settingsRowCaption")
            caption.setWordWrap(True)
            text_layout.addWidget(caption)

        self.layout.addLayout(text_layout, 1)

    def add_control(self, control: QWidget) -> None:
        self.layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


class SettingsView(QWidget):
    back_requested = pyqtSignal()
    model_changed = pyqtSignal(str)

    def __init__(self, models: list[str] | None = None) -> None:
        super().__init__()
        self.setObjectName("settingsPanel")
        self._models = models or [DEFAULT_MODEL]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        layout.addLayout(self._header())
        layout.addWidget(self._scroll_area(), 1)

    def _header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(18, 0, 8, 0)
        layout.setSpacing(12)

        avatar = QLabel()
        avatar.setFixedSize(48, 48)
        avatar.setPixmap(
            QPixmap(str(asset_path("characters", "myorii_profile.png"))).scaled(
                avatar.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        title = QLabel("설정")
        title.setObjectName("settingsTitle")
        subtitle = QLabel("Myorii를 내 취향에 맞게 설정해요")
        subtitle.setObjectName("settingsSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        close = QPushButton()
        close.setObjectName("iconButton")
        close.setText("×")
        close.setFixedSize(36, 36)
        close.setCursor(Qt.CursorShape.PointingHandCursor)
        close.clicked.connect(self.back_requested.emit)

        layout.addWidget(avatar)
        layout.addLayout(title_layout, 1)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        return layout

    def _scroll_area(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("settingsScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("settingsScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._general_section())
        content_layout.addWidget(self._local_model_section())
        content_layout.addWidget(self._integration_section())
        content_layout.addWidget(self._info_section())
        content_layout.addWidget(self._exit_section())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _general_section(self) -> QWidget:
        section = SettingsSection("일반", "settings.png")

        open_at_start = SettingsRow("시작 시 Myorii 열기")
        open_at_start.add_control(SwitchButton())
        section.add_row(open_at_start)

        theme = SettingsRow("테마")
        theme.add_control(SegmentedControl(("라이트", "다크")))
        section.add_row(theme)

        language = SettingsRow("언어")
        language.add_control(SegmentedControl(("한국어", "영어")))
        section.add_row(language)
        return section

    def _local_model_section(self) -> QWidget:
        section = SettingsSection("로컬 모델", "computer.png")

        model = SettingsRow("기본 모델", "로컬에 설치된 모델 중 기본으로 사용할 모델을 선택하세요.")
        combo = QComboBox()
        combo.setObjectName("modelComboBox")
        combo.setFixedHeight(34)
        combo.setMinimumWidth(190)
        combo.addItems(self._available_models())
        combo.setCurrentText(DEFAULT_MODEL)
        combo.currentTextChanged.connect(self.model_changed.emit)
        model.add_control(combo)
        section.add_row(model)

        manage = SettingsRow("모델 관리", "로컬 모델 추가, 삭제 및 정보를 확인할 수 있어요.")
        manage_button = QPushButton("모델 관리")
        manage_button.setObjectName("secondaryButton")
        manage_button.setCursor(Qt.CursorShape.PointingHandCursor)
        manage.add_control(manage_button)
        section.add_row(manage)
        return section

    def _integration_section(self) -> QWidget:
        section = SettingsSection("연동", "link.png")

        notion = SettingsRow("Notion 연동", "할일 목록을 Notion과 연동할 수 있어요.")
        connect = QPushButton("연동하기")
        connect.setObjectName("secondaryButton")
        connect.setCursor(Qt.CursorShape.PointingHandCursor)
        notion.add_control(connect)
        section.add_row(notion)
        return section

    def _info_section(self) -> QWidget:
        section = SettingsSection("정보", "info.png")

        version = SettingsRow("버전")
        version_value = QLabel("v0.1.0 (Beta)")
        version_value.setObjectName("versionLabel")
        version.add_control(version_value)
        section.add_row(version)

        help_row = SettingsRow("도움말")
        help_button = QPushButton("도움말")
        help_button.setObjectName("ghostActionButton")
        help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        help_row.add_control(help_button)
        section.add_row(help_row)

        feedback = SettingsRow("피드백 보내기")
        feedback_button = QPushButton("피드백")
        feedback_button.setObjectName("ghostActionButton")
        feedback_button.setCursor(Qt.CursorShape.PointingHandCursor)
        feedback.add_control(feedback_button)
        section.add_row(feedback)
        return section

    def _exit_section(self) -> QWidget:
        exit_button = QPushButton("앱 종료")
        exit_button.setObjectName("exitActionButton")
        exit_button.setIcon(tinted_icon("power.png", QColor("#ff2d2d"), QSize(19, 19)))
        exit_button.setIconSize(QSize(18, 18))
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(QApplication.quit)
        return exit_button

    def _available_models(self) -> list[str]:
        return self._models

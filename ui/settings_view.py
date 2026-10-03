from __future__ import annotations

from ui.preferences import set_local_style

from ui.preferences import (tr, localized_label, localized_button, set_localized_text, set_localized_placeholder, color, stylesheet)

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QStackedWidget,
    QLineEdit,
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
from storage import model_store
from ui.model_manager import ModelManager, ModelTask
from ui.model_controls import PasswordEdit, model_combo
from core.llm.cloud_client import CloudClient
from ui.assets import asset_path, tinted_icon
from ui.widgets.switch_button import SwitchButton


class SegmentedControl(QFrame):
    changed = pyqtSignal(str)
    index_changed = pyqtSignal(int)

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
            button = localized_button(label)
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
        self._group.idClicked.connect(self.index_changed.emit)


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
        icon.setProperty("themeIcon", icon_name)
        icon.setPixmap(tinted_icon(icon_name, color("#20242c"), QSize(19,19)).pixmap(19,19))

        label = localized_label(title)
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

        label = localized_label(title)
        label.setObjectName("settingsRowTitleAccent" if accent else "settingsRowTitle")
        text_layout.addWidget(label)

        if subtitle:
            caption = localized_label(subtitle)
            caption.setObjectName("settingsRowCaption")
            caption.setWordWrap(True)
            text_layout.addWidget(caption)

        self.layout.addLayout(text_layout, 1)

    def add_control(self, control: QWidget) -> None:
        self.layout.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


class ModelPages(QStackedWidget):
    def sizeHint(self):
        return self.currentWidget().sizeHint() if self.currentWidget() else super().sizeHint()
    def minimumSizeHint(self):
        return self.currentWidget().minimumSizeHint() if self.currentWidget() else super().minimumSizeHint()


class SettingsView(QWidget):
    back_requested = pyqtSignal()
    model_changed = pyqtSignal(str)
    backend_changed = pyqtSignal(str, str)
    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)

    def __init__(self, models: list[str] | None = None, preferences: dict[str,str] | None = None) -> None:
        super().__init__()
        self.setObjectName("settingsPanel")
        self._model_config = model_store.load()
        self._preferences = preferences or {"theme":"light","language":"ko"}
        self._models = models or [DEFAULT_MODEL]
        self._model_combo: QComboBox | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._header())
        layout.addWidget(self._scroll_area(), 1)

    def _header(self) -> QWidget:
        frame = QFrame()
        frame.setFixedHeight(46)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)
        back = QPushButton("‹")
        back.setObjectName("memoBackButton")
        back.setFixedSize(28, 28)
        back.setToolTip("이전 화면으로")
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self.back_requested.emit)
        title = localized_label("설정")
        title.setObjectName("settingsSectionTitle")
        layout.addWidget(back)
        layout.addWidget(title)
        layout.addStretch(1)
        return frame

    def _scroll_area(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("settingsScrollArea")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("settingsScrollContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(14, 4, 14, 14)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._general_section())
        content_layout.addWidget(self._local_model_section())
        content_layout.addWidget(self._integration_section())
        content_layout.addWidget(self._info_section())
        content_layout.addWidget(self._exit_section())
        content_layout.addStretch(1)

        scroll.setWidget(content)
        scroll.setMinimumWidth(0)
        return scroll

    def _general_section(self) -> QWidget:
        section = SettingsSection("일반", "settings.png")

        open_at_start = SettingsRow("시작 시 Myorii 열기")
        open_at_start.add_control(SwitchButton())
        section.add_row(open_at_start)

        theme = SettingsRow("테마")
        self.theme_control = SegmentedControl(("라이트", "다크"), int(self._preferences["theme"] == "dark"))
        self.theme_control.index_changed.connect(lambda index: self.theme_changed.emit(("light","dark")[index]))
        theme.add_control(self.theme_control)
        section.add_row(theme)

        language = SettingsRow("언어")
        self.language_control = SegmentedControl(("한국어", "영어"), int(self._preferences["language"] == "en"))
        self.language_control.index_changed.connect(lambda index: self.language_changed.emit(("ko","en")[index]))
        language.add_control(self.language_control)
        section.add_row(language)
        return section

    def _local_model_section(self) -> QWidget:
        section = SettingsSection("AI 모델", "computer.png")
        provider_row = SettingsRow("제공자")
        self.provider_control = SegmentedControl(("Ollama 로컬 모델", "API"),int(self._model_config["provider"] != "ollama"))
        self.provider_control.index_changed.connect(self._mode_changed)
        provider_row.add_control(self.provider_control)
        section.add_row(provider_row)
        self._model_pages=ModelPages()
        section.add_row(self._model_pages)

        local=QWidget();local_layout=QVBoxLayout(local)
        local_layout.setContentsMargins(14,12,14,14)
        local_layout.setSpacing(8)
        local_layout.addWidget(localized_label("기본 모델"))
        local_row=QHBoxLayout()
        self._model_combo=model_combo()
        self._model_combo.addItems(self._models)
        self._model_combo.setCurrentText(self._model_config["models"]["ollama"])
        self._model_combo.currentTextChanged.connect(self._local_model_selected)
        local_row.addWidget(self._model_combo,1)
        manage=localized_button("모델 관리")
        manage.setObjectName("secondaryButton")
        manage.setFixedHeight(34)
        manage.clicked.connect(self._open_model_manager)
        local_row.addWidget(manage)
        local_layout.addLayout(local_row)
        self._model_pages.addWidget(local)

        api=QWidget();api_layout=QVBoxLayout(api)
        api_layout.setContentsMargins(14,12,14,14)
        api_layout.setSpacing(8)
        api_layout.addWidget(localized_label("API 서비스"))
        self.api_provider_combo=model_combo()
        for name,value in (("OpenAI · GPT","openai"),("Google · Gemini","gemini"),("Anthropic · Claude","anthropic")):
            self.api_provider_combo.addItem(name,value)
        current=self._model_config["provider"]
        if current!='ollama': self.api_provider_combo.setCurrentIndex(model_store.PROVIDERS[1:].index(current))
        self.api_provider_combo.currentIndexChanged.connect(self._api_provider_changed)
        api_layout.addWidget(self.api_provider_combo)
        api_layout.addWidget(localized_label("API 키"))
        self.api_key=PasswordEdit()
        self.api_key.setObjectName("apiKeyInput")
        set_localized_placeholder(self.api_key,"API 키 · 비워두면 기존 키 유지")
        api_layout.addWidget(self.api_key)
        actions=QHBoxLayout()
        for source,slot in (("키 저장",self._save_api_key),("저장된 키 삭제",self._remove_api_key)):
            button=localized_button(source);button.setObjectName("secondaryButton");button.clicked.connect(slot);actions.addWidget(button)
        api_layout.addLayout(actions)
        api_layout.addWidget(localized_label("API 모델"))
        self.api_model_combo=model_combo()
        self.api_model_combo.setEditable(False)
        selected=self._model_config["models"][self.api_provider_combo.currentData()]
        if selected:self.api_model_combo.addItem(selected)
        self.api_model_combo.activated.connect(lambda _index:self._api_model_selected())
        model_row=QHBoxLayout()
        model_row.setSpacing(10)
        model_row.addWidget(self.api_model_combo,1)
        refresh=localized_button("목록 새로고침");refresh.setObjectName("secondaryButton")
        refresh.setMinimumHeight(34)
        refresh.clicked.connect(self._refresh_api_models)
        model_row.addWidget(refresh)
        api_layout.addLayout(model_row)
        notice=localized_label("API 사용 시 대화와 첨부 내용이 선택한 제공자에게 전송되며 API 요금이 발생할 수 있습니다.")
        notice.setWordWrap(True);notice.setObjectName("settingsRowCaption");api_layout.addWidget(notice)
        self.api_status=QLabel();self.api_status.setWordWrap(True);api_layout.addWidget(self.api_status)
        self._api_task=None
        self._model_pages.addWidget(api)
        self._model_pages.setCurrentIndex(int(current!='ollama'))
        return section

    def _integration_section(self) -> QWidget:
        section = SettingsSection("연동", "link.png")

        notion = SettingsRow("Notion 연동", "할일 목록을 Notion과 연동할 수 있어요.")
        connect = localized_button("연동하기")
        connect.setObjectName("secondaryButton")
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
        help_button = localized_button("도움말")
        help_button.setObjectName("ghostActionButton")
        help_row.add_control(help_button)
        section.add_row(help_row)
        feedback = SettingsRow("피드백 보내기")
        feedback_button = localized_button("피드백")
        feedback_button.setObjectName("ghostActionButton")
        feedback.add_control(feedback_button)
        section.add_row(feedback)
        return section

    def _exit_section(self) -> QWidget:
        exit_button = localized_button("앱 종료")
        exit_button.setObjectName("exitActionButton")
        exit_button.setIcon(tinted_icon("power.png", color("#ff2d2d"), QSize(19, 19)))
        exit_button.setIconSize(QSize(18, 18))
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(QApplication.quit)
        return exit_button

    def _mode_changed(self,index):
        if hasattr(self,'_api_task') and self._api_task and self._api_task.isRunning():
            self.provider_control._buttons[self._model_pages.currentIndex()].setChecked(True)
            return
        self.api_key.clear();self.api_key.hide_secret()
        self._model_pages.setCurrentIndex(index)
        self._model_pages.updateGeometry()
        provider='ollama' if index==0 else self.api_provider_combo.currentData()
        self._model_config['provider']=provider
        self.backend_changed.emit(provider,self._model_config['models'][provider])

    def _api_provider_changed(self,_index):
        self.api_key.clear();self.api_key.hide_secret()
        provider=self.api_provider_combo.currentData()
        self.api_model_combo.blockSignals(True)
        self.api_model_combo.clear()
        model=self._model_config['models'][provider]
        if model:self.api_model_combo.addItem(model)
        self.api_model_combo.blockSignals(False)
        self.api_status.clear()
        if self._model_pages.currentIndex()==1:
            self._model_config['provider']=provider
            self.backend_changed.emit(provider,model)

    def _local_model_selected(self,model):
        if not model:return
        self._model_config['models']['ollama']=model
        if self._model_config['provider']=='ollama': self.backend_changed.emit('ollama',model)

    def _api_model_selected(self):
        if self._model_pages.currentIndex()!=1:return
        provider=self.api_provider_combo.currentData()
        model=self.api_model_combo.currentText().strip()
        self._model_config['models'][provider]=model
        self.backend_changed.emit(provider,model)

    def _api_operation(self,operation,result):
        if self._api_task and self._api_task.isRunning():return
        self.api_status.setText(tr('작업 중...'))
        for control in self._model_pages.widget(1).findChildren(QWidget):
            if isinstance(control,(QPushButton,QComboBox,QLineEdit)):control.setEnabled(False)
        self._api_task=ModelTask(operation,self)
        self._api_task.result.connect(result)
        self._api_task.failure.connect(self.api_status.setText)
        self._api_task.finished.connect(self._api_ready)
        self._api_task.start()

    def _api_ready(self):
        for control in self._model_pages.widget(1).findChildren(QWidget):
            if isinstance(control,(QPushButton,QComboBox,QLineEdit)):control.setEnabled(True)

    def _save_api_key(self):
        key=self.api_key.text().strip();provider=self.api_provider_combo.currentData()
        if not key:self.api_status.setText(tr('API 키를 입력해주세요.'));return
        def operation(progress):
            model_store.set_key(provider,key)
            return CloudClient(provider,key).list_models()
        def result(models):
            self.api_key.clear();self.api_key.hide_secret();self._apply_api_models(provider,models)
        self._api_operation(operation,result)

    def _remove_api_key(self):
        provider=self.api_provider_combo.currentData()
        def result(_):
            self.api_key.clear();self.api_key.hide_secret();self.api_status.setText(tr('저장된 API 키를 삭제했습니다.'))
        self._api_operation(lambda progress:model_store.set_key(provider,''),result)

    def _apply_api_models(self,provider,models):
        selected=self._model_config['models'][provider]
        self.api_model_combo.blockSignals(True)
        self.api_model_combo.clear();self.api_model_combo.addItems(models)
        self.api_model_combo.setCurrentIndex(self.api_model_combo.findText(selected) if selected in models else (0 if models else -1))
        self.api_model_combo.blockSignals(False)
        self._api_model_selected()
        self.api_status.setText(tr('모델 목록을 불러왔습니다.') if models else tr('사용 가능한 채팅 모델이 없습니다.'))

    def _refresh_api_models(self):
        provider=self.api_provider_combo.currentData()
        self._api_operation(lambda progress:CloudClient(provider).list_models(),lambda models:self._apply_api_models(provider,models))

    def _open_model_manager(self):
        dialog=ModelManager('ollama',self._model_config['models']['ollama'],self)
        dialog.model_selected.connect(self._managed_model_selected)
        dialog.exec()
        if dialog.models_loaded:
            self.update_models([dialog.list.item(i).text() for i in range(dialog.list.count())])

    def _managed_model_selected(self,model):
        if model not in self._models:self._models.append(model)
        self._model_config['models']['ollama']=model
        self.update_models(self._models)
        self._local_model_selected(model)

    def update_models(self,models):
        self._models=list(models)
        if self._model_combo is None:return
        selected=self._model_config['models']['ollama']
        self._model_combo.blockSignals(True);self._model_combo.clear();self._model_combo.addItems(self._models)
        self._model_combo.setCurrentIndex(self._model_combo.findText(selected))
        self._model_combo.blockSignals(False)

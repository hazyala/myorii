"""Non-blocking local model management and API credential setup."""
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QListWidget,QMessageBox
from ui.preferences import tr, localized_label, localized_button, stylesheet
from core.llm.ollama_client import OllamaClient
from core.llm.cloud_client import CloudClient, CloudAPIError
from storage import model_store

class ModelTask(QThread):
    result = pyqtSignal(object)
    failure = pyqtSignal(str)
    progress = pyqtSignal(str)
    def __init__(self, operation, parent):
        super().__init__(parent);self.operation=operation
    def run(self):
        try: self.result.emit(self.operation(self.progress.emit))
        except CloudAPIError as exc: self.failure.emit(str(exc))
        except Exception: self.failure.emit(tr('모델 작업에 실패했습니다. Ollama 실행 상태 또는 API 키체인 접근을 확인해주세요.'))

class ModelManager(QDialog):
    model_selected = pyqtSignal(str)
    def __init__(self,provider,selected,parent=None):
        super().__init__(parent)
        self.provider=provider;self.selected=selected;self.task=None;self.models_loaded=False
        self.setObjectName("modelManager")
        self.setWindowTitle(tr('모델 관리'));self.resize(380,400)
        self.setStyleSheet(stylesheet(MANAGER_STYLE))
        layout=QVBoxLayout(self)
        layout.setContentsMargins(18,18,18,16)
        layout.setSpacing(12)
        title=localized_label({'ollama':'Ollama · 로컬 모델','openai':'OpenAI · GPT','gemini':'Google · Gemini','anthropic':'Anthropic · Claude'}[provider]);layout.addWidget(title)
        if provider!='ollama':
            notice=localized_label('API 사용 시 대화와 첨부 내용이 선택한 제공자에게 전송되며 API 요금이 발생할 수 있습니다.');notice.setWordWrap(True);layout.addWidget(notice)
            self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText(tr('API 키 · 비워두면 기존 키 유지'));layout.addWidget(self.key)
            save=localized_button('키 저장');save.clicked.connect(self.save_key);layout.addWidget(save)
            remove=localized_button('저장된 키 삭제');remove.clicked.connect(self.remove_key);layout.addWidget(remove)
        title.setObjectName("managerTitle")
        self.list=QListWidget();self.list.setObjectName("managerList");layout.addWidget(self.list,1)
        self.name=QLineEdit();self.name.setPlaceholderText(tr('모델 이름을 입력하거나 목록에서 선택'));self.name.setText(selected);layout.addWidget(self.name)
        self.list.currentTextChanged.connect(self.name.setText)
        if provider=="ollama": self.name.hide()
        row=QHBoxLayout();layout.addLayout(row)
        refresh=localized_button('목록 새로고침');refresh.clicked.connect(self.refresh);row.addWidget(refresh)
        use=localized_button('모델 선택');use.setObjectName('modelUseButton');use.clicked.connect(self.use_model);row.addWidget(use)
        if provider=='ollama':
            row=QHBoxLayout();layout.addLayout(row)
            install=localized_button('모델 다운로드');install.clicked.connect(self.install);row.addWidget(install)
            delete=localized_button('모델 삭제');delete.setObjectName('modelDeleteButton');delete.clicked.connect(self.delete);row.addWidget(delete)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
        if provider=='ollama': self.refresh()

    def start(self,operation,on_result):
        if self.task and self.task.isRunning(): return
        self.status.setText(tr('작업 중...'))
        for button in self.findChildren(QPushButton): button.setEnabled(False)
        self.name.setEnabled(False)
        if hasattr(self,'key'): self.key.setEnabled(False)
        self.task=ModelTask(operation,self)
        self.task.result.connect(on_result)
        self.task.failure.connect(self.status.setText)
        self.task.progress.connect(self.status.setText)
        self.task.finished.connect(self.ready)
        self.task.start()

    def ready(self):
        for button in self.findChildren(QPushButton): button.setEnabled(True)
        self.name.setEnabled(True)
        if hasattr(self,'key'): self.key.setEnabled(True)

    def refresh(self):
        provider=self.provider;key=self.key.text().strip() if hasattr(self,'key') else ''
        def operation(progress):
            if provider=='ollama': return OllamaClient().list_models()
            return CloudClient(provider,key or None).list_models()
        def result(models):
            self.models_loaded=True
            self.list.clear();self.list.addItems(models)
            matches=self.list.findItems(self.selected,Qt.MatchFlag.MatchExactly)
            if matches:self.list.setCurrentItem(matches[0])
            self.status.setText(tr('모델 목록을 불러왔습니다.'))
        self.start(operation,result)

    def install(self):
        QDesktopServices.openUrl(QUrl('https://ollama.com/library'))

    def delete(self):
        name=self.list.currentItem().text() if self.list.currentItem() else ''
        if not name: return
        if name==self.selected:
            self.status.setText(tr('현재 선택한 모델은 삭제할 수 없습니다. 다른 모델을 먼저 선택해주세요.'));return
        if QMessageBox.question(self,tr('모델 삭제'),name+'\n'+tr('이 로컬 모델을 삭제할까요?'))!=QMessageBox.StandardButton.Yes: return
        def operation(progress):
            client=OllamaClient();client._client.delete(name);return client.list_models()
        def result(models):
            self.list.clear();self.list.addItems(models);self.status.setText(tr('모델 삭제 완료'))
        self.start(operation,result)

    def save_key(self):
        key=self.key.text().strip()
        if not key: self.status.setText(tr('API 키를 입력해주세요.'));return
        provider=self.provider
        def result(_): self.key.clear();self.status.setText(tr('API 키를 키체인에 저장했습니다.'))
        self.start(lambda progress:model_store.set_key(provider,key),result)

    def remove_key(self):
        provider=self.provider
        def result(_): self.key.clear();self.status.setText(tr('저장된 API 키를 삭제했습니다.'))
        self.start(lambda progress:model_store.set_key(provider,''),result)

    def use_model(self):
        name=self.name.text().strip()
        if not name: return
        if self.provider=='ollama' and not any(self.list.item(i).text()==name for i in range(self.list.count())):
            self.status.setText(tr('먼저 모델을 다운로드해주세요.'));return
        if self.provider!='ollama' and self.key.text().strip():
            self.status.setText(tr('입력한 API 키를 먼저 저장해주세요.'));return
        self.model_selected.emit(name);self.accept()

    def reject(self):
        if self.task and self.task.isRunning(): return
        super().reject()
    def closeEvent(self,event):
        if self.task and self.task.isRunning(): event.ignore()
        else: super().closeEvent(event)


MANAGER_STYLE = """
QDialog#modelManager { background: #f6f8fb; }
QDialog#modelManager QWidget { color: #20242c; font-size: 12px; }
QLabel#managerTitle { font-size: 15px; font-weight: 650; background: transparent; }
QListWidget#managerList { background: #ffffff; color: #20242c;
    border: 1px solid #dfe4ed; border-radius: 10px; padding: 6px; outline: none; }
QListWidget#managerList::item { padding: 8px 10px; min-height: 22px; margin: 2px 0; border-radius: 6px; }
QListWidget#managerList::item:selected { background: #e8f2ff; color: #2f80ff; }
QListWidget#managerList::item:hover { background: #f3f6fb; }
QDialog#modelManager QPushButton { background: #ffffff; color: #20242c;
    border: 1px solid #dfe4ed; border-radius: 8px; min-height: 32px; padding: 0 10px; }
QDialog#modelManager QPushButton:hover { background: #e8f2ff; border-color: #2f80ff; }
QDialog#modelManager QPushButton:disabled { color: #737b88; background: #f3f6fb; }
QDialog#modelManager QPushButton#modelUseButton { background: #2f80ff; color: rgb(255,255,255); border-color: #2f80ff; }
QDialog#modelManager QPushButton#modelDeleteButton { color: #f04452; }
QDialog#modelManager QLabel { background: transparent; }
QDialog#modelManager QLineEdit { background: #ffffff; color: #20242c; border: 1px solid #dfe4ed; border-radius: 8px; padding: 8px; }
"""

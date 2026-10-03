"""UI translation and colors; user-authored content is never translated."""
import re
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QPushButton, QWidget

_language = 'ko'
_theme = 'light'
TRANSLATIONS = {
'채팅':'Chat','할일':'Tasks','메모':'Notes','설정':'Settings','온라인':'Online','오프라인':'Offline',
'일반':'General','시작 시 Myorii 열기':'Open Myorii at startup','테마':'Appearance','라이트':'Light','다크':'Dark','언어':'Language','한국어':'Korean','영어':'English',
'로컬 모델':'Local model','기본 모델':'Default model','모델 관리':'Manage models',
'로컬에 설치된 모델 중 기본으로 사용할 모델을 선택하세요.':'Choose a default from your installed local models.',
'로컬 모델 추가, 삭제 및 정보를 확인할 수 있어요.':'Add, remove, and inspect local models.',
'MCP · 커넥터 · 플러그인':'MCP · Connectors · Plugins','모델에 외부 도구와 서비스를 연결하는 기능은 향후 구현 예정입니다.':'Connecting external tools and services to models is planned for a future update.','도움말 사이트는 추후 구현 예정입니다.':'A help website is planned for a future update.','문의 및 제안':'Contact & Suggestions','연동':'Integrations','Notion 연동':'Connect Notion','할일 목록을 Notion과 연동할 수 있어요.':'Connect your tasks to Notion.','연동하기':'Connect',
'정보':'About','버전':'Version','도움말':'Help','피드백 보내기':'Send feedback','피드백':'Feedback','앱 종료':'Quit Myorii',
'오늘':'Today','+ 할일 추가':'+ Add task','할 일을 입력하세요...':'Enter a task...', '할 일 삭제':'Delete task',
'새로운 메모':'New note','내 메모 {count}':'My notes {count}', '내 메모 0':'My notes 0',
'저장됨':'Saved','저장 중...':'Saving...', 'Markdown으로 메모를 작성하세요...':'Write a note in Markdown...',
'채팅 기록':'Chat history','대화 기록 저장':'Save history','저장된 채팅이 없습니다.':'No saved chats.',
'무엇을 도와줄까?':'How can I help?', '복사됨':'Copied','이전 화면으로':'Back',
}
TRANSLATIONS.update({
"AI 모델":"AI models", "제공자":"Provider", "모델 관리에서 설치 모델 또는 API 모델을 선택하세요.":"Choose an installed or API model in Manage models.",
"다운로드·삭제 또는 API 키와 모델을 관리해요.":"Manage downloads, API keys, and model choices.",
"Ollama · 로컬 모델":"Ollama · Local models", "API 사용 시 대화와 첨부 내용이 선택한 제공자에게 전송되며 API 요금이 발생할 수 있습니다.":"API mode sends your conversation and attachments to the selected provider. API charges may apply.",
"API 키 · 비워두면 기존 키 유지":"API key · leave blank to keep the saved key", "키 저장":"Save key", "저장된 키 삭제":"Remove saved key", "모델 이름을 입력하거나 목록에서 선택":"Enter a model name or choose from the list", "목록 새로고침":"Refresh list", "모델 선택":"Use model", "다운로드":"Download", "모델 삭제":"Delete model", "작업 중...":"Working...", "사용 가능한 채팅 모델이 없습니다.":"No chat models available.", "모델 목록을 불러왔습니다.":"Model list loaded.", "다운로드 완료":"Download complete", "현재 선택한 모델은 삭제할 수 없습니다. 다른 모델을 먼저 선택해주세요.":"Select another model before deleting the active model.", "이 로컬 모델을 삭제할까요?":"Delete this local model?", "모델 삭제 완료":"Model deleted", "API 키를 입력해주세요.":"Enter an API key.", "API 키를 키체인에 저장했습니다.":"API key saved to Keychain.", "저장된 API 키를 삭제했습니다.":"Saved API key removed.", "먼저 모델을 다운로드해주세요.":"Download the model first.", "입력한 API 키를 먼저 저장해주세요.":"Save the entered API key first.", "모델 작업에 실패했습니다. Ollama 실행 상태 또는 API 키체인 접근을 확인해주세요.":"Model operation failed. Check Ollama or Keychain access."
})
TRANSLATIONS.update({"Ollama 로컬 모델":"Ollama local","API 서비스":"API service","API 키":"API key","API 모델":"API model","보기":"Show","가리기":"Hide","모델 다운로드":"Download models"})
COLORS = {'#ffffff':'#202733','#11131a':'#f1f4f8','#171b22':'#e8edf4','#20242c':'#e4eaf2','#222833':'#e4eaf2','#344054':'#d9e3f0','#2d405a':'#d9e3f0','#565f6e':'#b1bdcd','#667085':'#a7b4c6','#737b88':'#a7b4c6','#eef3fa':'#293548','#e8eef7':'#293548','#f6f8fb':'#242e3d','#f3f6fb':'#293548','#f7fbff':'#263950','#cfd8e6':'#4b5c72','#2f80ff':'#65a6ff','#16845b':'#68cfa3','#7c8797':'#a7b4c6'}

COLORS.update({"#e8f2ff":"#263950","#2b3038":"#e4eaf2", "#626a76":"#a7b4c6", "#69707c":"#a7b4c6", "#555c68":"#a7b4c6", "#dfe4ed":"#435269", "#f7f9fc":"#263950", "#f9fbfe":"#263950"})

def configure(*, language=None, theme=None):
    global _language, _theme
    if language is not None: _language = language
    if theme is not None: _theme = theme

def language(): return _language
def theme(): return _theme

def tr(source, **values):
    return (TRANSLATIONS.get(source, source) if _language == 'en' else source).format(**values)

def localized_label(source):
    widget = QLabel(tr(source)); widget.setProperty('i18nSource',source); return widget

def localized_button(source):
    widget = QPushButton(tr(source)); widget.setProperty('i18nSource',source); return widget

def set_localized_text(widget, source, **values):
    widget.setProperty('i18nSource',source)
    widget.setProperty('i18nValues',values)
    widget.setText(tr(source, **values))

def set_localized_placeholder(widget, source):
    widget.setProperty('i18nPlaceholder',source);widget.setPlaceholderText(tr(source))

def retranslate(root):
    for widget in [root,*root.findChildren(QWidget)]:
        source=widget.property('i18nSource')
        if source: widget.setText(tr(source, **(widget.property('i18nValues') or {})))
        source=widget.property('i18nPlaceholder')
        if source: widget.setPlaceholderText(tr(source))

def color(source):
    return QColor(COLORS.get(source.lower(),source) if _theme=='dark' else source)

def stylesheet(source):
    if _theme=='light': return source
    source=re.sub(r'#[0-9a-fA-F]{6}',lambda m:COLORS.get(m.group().lower(),m.group()),source)
    source=re.sub(r'rgba\(246,\s*248,\s*252,\s*(\d+)\)',lambda m:'rgba(32, 39, 51, '+m.group(1)+')',source)
    source=re.sub(r'rgba\(255,\s*255,\s*255,\s*(\d+)\)',lambda m:'rgba(32, 39, 51, '+m.group(1)+')',source)
    source=re.sub(r'rgba\(232,\s*238,\s*247,\s*(\d+)\)',lambda m:'rgba(41, 53, 72, '+m.group(1)+')',source)
    source=re.sub(r'rgba\(222,\s*227,\s*235,\s*(\d+)\)',lambda m:'rgba(80, 95, 115, '+m.group(1)+')',source)
    return source

def apply_local_styles(root):
    for widget in root.findChildren(QWidget):
        if widget.objectName() == "statusDot": continue
        source=widget.property('lightStylesheet')
        current=widget.styleSheet()
        if source is None and current:
            source=current;widget.setProperty('lightStylesheet',source)
        if source: widget.setStyleSheet(stylesheet(source))


def set_local_style(widget, source):
    widget.setProperty('lightStylesheet',source)
    widget.setStyleSheet(stylesheet(source))

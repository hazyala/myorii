# 🏗️ Myorii Architecture

## 개요

Myorii는 macOS 메뉴바 및 Windows 시스템 트레이에 상주하는 로컬 LLM 기반 데스크톱 컴패니언 애플리케이션이다.

비즈니스 로직은 플랫폼에 독립적으로 설계하고, 운영체제별 기능만 별도로 분리하여 관리한다.

---

# 전체 구조

```text
┌─────────────────────┐
│      Menu Bar       │
│     System Tray     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│        UI           │
│      (PyQt6)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       Core          │
├─────────────────────┤
│ Request Router      │
│ LLM Client          │
│ Naming Engine       │
│ Image Analyzer      │
│ Clipboard Manager   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Storage        │
├─────────────────────┤
│ SQLite              │
│ Local Settings      │
│ Session History     │
└─────────────────────┘
```

---

# 계층 구조

## Platform Layer

운영체제 의존 기능을 담당한다.

### 역할

* 메뉴바 아이콘 생성
* 시스템 트레이 생성
* 창 위치 계산
* OS 이벤트 처리
* PyInstaller 번들 리소스 경로 처리

### 구성

```text
platform/
├── macos/
└── windows/
```

---

## UI Layer

사용자가 직접 보는 화면을 담당한다.

### 역할

* 채팅 화면
* 할일 화면
* 메모 화면
* 설정 화면
* 이미지 미리보기
* 온라인/오프라인 상태 표시

### 구성

```text
ui/
├── main_window.py
├── chat_worker.py
├── widgets/
│   ├── chat_view.py
│   ├── message_bubble.py
│   ├── todo_view.py
│   └── settings_view.py
└── styles/
```

---

## Core Layer

Myorii의 핵심 비즈니스 로직을 담당한다.

### 역할

* Ollama 호출
* 요청 라우팅
* 의도별 프롬프트 선택
* 단일 Ollama 모델 유지
* 네이밍 추천
* 이미지 분석
* 응답 생성
* 클립보드 복사

### 구성

```text
core/
├── paths.py
├── llm/
│   ├── ollama_client.py
│   ├── chat_service.py
│   ├── prompt_loader.py
│   └── router/
├── integrations/      # 예정: MCP·커넥터·플러그인 연동
├── sync/              # 예정: local-first 동기화 엔진
└── tools/
```

`core/`는 Qt를 import하지 않는 순수 Python 계층이다. UI는 Ollama를 직접 호출하지 않고 `ChatService`를 통해서만 모델 목록 조회와 채팅 스트리밍을 요청한다.

LLM 요청 라우팅, 의도별 프롬프트, 모델 선택, 첨부 처리, 응답 포맷터의 확장 설계는 [router-design.md](router-design.md)에서 관리한다. 라우터는 채팅 요청의 처리 경로만 결정하며, Notion API나 기기간 동기화 같은 외부 상태 변경은 `integrations/`와 `sync/` 계층에서 분리해 관리한다.

---

## Storage Layer

로컬 데이터 저장을 담당한다.

### 역할

* 채팅 세션 및 메시지 저장
* 할일 저장
* 메모 저장
* 파일 첨부 경로 저장

### 구성

```text
storage/
├── database.py       # DB 초기화, 스키마 생성, 연결 관리
├── chat_store.py     # ChatSession / ChatMessage / ChatAttachment CRUD
├── todo_store.py     # Todo CRUD
└── memo_store.py     # Memo CRUD
```

### 스키마

```text
myorii.db
├── chat_sessions     (id, title, ord, created_at, updated_at)
├── chat_messages     (id, session_id, role, content, created_at)
├── chat_attachments  (id, message_id, file_path, mime_type, created_at)
├── todos             (id, text, done, ord, created_at, updated_at)
└── memos             (id, title, body, ord, created_at, updated_at)
```

DB 파일은 `~/Library/Application Support/Myorii/myorii.db`에 저장된다.  
앱 재설치 후에도 데이터가 유지된다.  
`ord` 컬럼은 float으로 저장하고, 할 일/메모/채팅 기록 드래그 재정렬 완료 시 현재 UI 순서대로 다시 번호를 부여한다.  
V3 클라우드 동기화 시 `chat_attachments`에 `remote_url` 컬럼을 추가해 로컬 파일 없이 URL 접근을 지원한다.

채팅 세션은 대화 기록 저장 스위치가 켜진 대화만 생성한다. 기록 목록은 `chat_sessions.ord` 기준으로 정렬하며, 세션 삭제 시 `chat_messages`와 `chat_attachments`는 FK cascade로 함께 삭제된다.

# MVP 기능 흐름

## 네이밍

```text
사용자 입력

↓

Chat View

↓

Naming Engine

↓

LLM Client

↓

Ollama

↓

응답 반환
```

---

## 이미지 분석

```text
이미지 붙여넣기

↓

Chat View

↓

Image Analyzer

↓

LLM Client

↓

qwen3-vl

↓

분석 결과 반환
```

---

## 메모

```text
사용자 입력 / Markdown 단축키 / 드래그 / 삭제

↓

Memo View

↓

Memo Store

↓

SQLite 저장
```

메모 UI는 `ui/widgets/memo_view.py`에서 목록 카드와 편집 화면을 구성한다.

* 목록 카드는 SQLite `ord` 순서대로 표시하고, 드래그 완료 시 현재 UI 순서를 다시 저장한다.
* 새 메모 생성과 기존 메모 클릭은 편집 화면으로 전환한다.
* 편집 화면은 Markdown 원문을 저장하면서 제목, 목록, 체크박스, 인용, 인라인 코드, 코드 블럭을 즉시 시각화한다.
* 자동 저장은 짧은 타이머로 묶어 입력 중 저장 호출을 완화한다.
* 목록 미리보기는 카드 폭 기준으로 최대 2줄만 표시해 날짜와 겹치지 않도록 한다.

## 할 일

```text
사용자 입력 / 체크 / 드래그

↓

Todo View

↓

Todo Store

↓

SQLite 저장
```

---

# 플랫폼 분기

플랫폼별 구현은 Platform Layer에서만 처리한다.

```python
import sys

if sys.platform == "darwin":
    from platform.macos.menubar import MacMenuBar

elif sys.platform == "win32":
    from platform.windows.tray import WindowsTray
```

Core, UI, Storage는 플랫폼에 의존하지 않는다.

---

# 현재 macOS 실행 흐름

```text
main.py

↓

QApplication 생성

↓

MainWindow 생성

↓

MacMenuBar 생성

↓

메뉴바 아이콘 클릭

↓

MainWindow toggle_at(icon_geometry)
```

메인 창은 메뉴바 아이콘 위치를 기준으로 표시된다.

창 표시 시 현재 작업 화면을 강제로 활성화하지 않는다.

현재 `MainWindow`는 아래 UI 요소를 직접 구성한다.

* 글래스 팝오버 외곽과 상단 포인터
* Header의 Myorii 캐릭터, 설정 버튼, 창 닫기 버튼, 앱 이름 옆 온라인/오프라인 상태
* 채팅, 할일, 메모 탭과 탭별 컨텐츠 스택
* 기본 화면과 설정 화면을 전환하는 페이지 스택
* `ChatView` 기반 채팅 메시지 목록 전용 스크롤 영역
* 사용자/Assistant 메시지 버블과 Assistant Markdown 렌더링
* 코드블록/인라인 코드/기술 항목 클릭 복사와 `복사됨` 토스트
* 응답 생성 중 빨간 발바닥 바운스 인디케이터
* 채팅 기록 버튼/목록, 입력창 내부 `+` 파일 선택 액션, 대화 기록 저장 스위치
* 입력부 드래그 앤 드롭 파일 첨부와 첨부 파일 미리보기 카드
* 지원하지 않는 파일 형식에 대한 Assistant 오류 메시지 표시
* `Enter` 전송, `Shift+Enter` 줄바꿈을 처리하는 입력 위젯
* `ChatWorker`를 통한 워커 스레드 기반 토큰 스트리밍
* `ModelListWorker`를 통한 설정 모델 목록 비동기 로딩

채팅 메시지는 `ChatService`가 현재 세션 히스토리를 보관하고, 라우터 계층이 의도 분류, 프롬프트 프로필, 단일 모델 유지, 응답 포맷 보정을 처리한 뒤 선택 제공자에 따라 `OllamaClient` 또는 `CloudClient`에 스트리밍 요청을 보내는 방식으로 렌더링한다. 모든 응답은 사용자가 선택한 제공자·모델에서 생성한다. 앱 시작 시 `ModelWarmupWorker`가 백그라운드에서 선택한 로컬 모델 워밍업을 시도하고, 채팅 요청은 `keep_alive=30m`로 모델을 유지한다. 텍스트/이미지 요청을 별도 빠른 텍스트 모델과 비전 모델로 분기하지 않는다. Ollama가 실행 중이 아니면 워밍업 실패는 조용히 무시하고, 실제 채팅 요청에는 Ollama를 실행한 뒤 다시 시도해 달라는 사용자용 오류를 표시한다. 모델 목록은 워커 스레드에서 실제 설치 모델을 조회하여 메인 스레드의 Ollama 호출을 피한다. 응답 완료 후에는 파일명, 함수명, 변수명, 클래스명, 명령어, Python/Java/HTML/CSS/C 계열 코드, SQL, 정규식, 짧은 단어 번역처럼 복사 대상이 되는 개발 산출물을 별도 코드블록으로 렌더링해 개별 복사를 지원한다. 여러 후보는 후보별 코드블록으로 분리하고, 하나의 언어 코드 스니펫, SQL, 셸 스크립트는 줄바꿈과 들여쓰기를 유지한 하나의 코드블록으로 유지한다. 설명, 코드, 주의점이 함께 있는 응답은 실제 화면에서도 텍스트와 코드블록 위젯 순서를 유지한다. 요약, 분석, 문서 내용 설명, 일상 대화는 사용자가 코드나 명령어를 요청하지 않는 한 일반 문장으로 표시한다.

파일 첨부는 `ChatView`가 전송 전 로컬 파일 경로를 입력부 상태로 보관하고, 입력창 위 미리보기 카드로 표시한다. 전송 시 화면에는 첨부 파일을 사용자 메시지 버블 본문에 섞지 않고 버블 상단 바깥의 미리보기 카드로 렌더링한다. 전송 후 첨부 카드가 한 줄 폭을 넘으면 가로로 넘치지 않고 다음 줄로 재배치한다. LLM 요청 텍스트에는 첨부 파일명을 함께 전달한다. 이미지 첨부는 `ChatAttachmentPayload`로 `ChatWorker`, `ChatService`, `OllamaClient`까지 전달하고, `ImageHandler`가 base64로 변환해 Ollama 요청의 `messages[].images`에 포함한다. `AttachmentRouter`는 비이미지 첨부를 handler에 위임한다. `TextHandler`는 `txt`, `md`, `json`, `yaml`, `yml` 첨부 본문 일부를 `AttachmentContext`로 추출하고, `CsvHandler`는 `csv`, `tsv` 첨부의 컬럼명과 샘플 행을 `AttachmentContext`로 요약한다. `PdfHandler`는 `pdf` 첨부의 일부 페이지 텍스트를 추출하되 스캔/OCR/표 구조 분석은 지원하지 않는다. `DocxHandler`는 `docx` 첨부의 문단/표 텍스트 일부를 추출하되 서식, 이미지, 주석, 변경 추적, 매크로는 분석하지 않는다. `XlsxHandler`는 `xlsx` 첨부의 시트명, 컬럼명, 샘플 행을 요약하되 전체 행 분석, 수식 재계산, 피벗/차트/서식 분석은 지원하지 않는다. `PptxHandler`는 `pptx` 첨부의 슬라이드별 텍스트를 추출하되 PPT 제작, 디자인 생성, 이미지/차트/표 구조 분석, 발표자 노트, 수치 계산은 지원하지 않는다. `AttachmentContext`는 읽은 범위와 지원 한계를 `제한`, `주의` 문구로 포함한다. `ChatService`는 추출된 context를 user message 본문과 metadata에 추가해 모델 요청에 포함한다. 지원 파일은 이미지(`png`, `jpg`, `jpeg`, `gif`, `bmp`), 텍스트(`txt`, `md`, `json`, `yaml`, `yml`), 표 텍스트(`csv`, `tsv`), 문서/오피스(`pdf`, `docx`, `xlsx`, `pptx`)로 제한하고, 지원하지 않는 파일은 Assistant 메시지로 오류를 렌더링한다.

LLM 요청 계약은 `core/llm/contracts.py`의 `ChatRequest`를 기준으로 확장한다. `ChatRequest`는 모델명, 시스템 프롬프트, 히스토리, 사용자 메시지, 첨부 파일, 요청 ID를 하나의 경계로 묶는다. 첨부 파일은 `ChatAttachmentPayload`로 표현하고 이미지, 문서, 스프레드시트, 프레젠테이션 등 타입을 분리한다. 메시지와 첨부에는 `SyncMetadata`를 포함해 로컬 ID, 클라우드 ID, revision, 동기화 상태를 보관할 수 있게 한다. 요청에는 `DeviceContext`를 포함해 향후 로그인 계정, 사용자 ID, 디바이스 ID, 온라인 상태, 동기화 활성 여부를 전달할 수 있게 한다.

설정 화면은 `ui/settings_view.py`에서 구성한다.

현재 설정 화면은 메인 화면과 Header·캐릭터·탭을 공유한다. 설정 아이콘 또는 뒤로 버튼으로 돌아가며, 채팅·할일·메모 탭을 눌러도 해당 화면으로 이동한다.

* 라이트/다크 테마와 한국어/영어 언어는 실제 적용되고 SQLite `preferences`에 저장되어 재실행 후 복원된다. 사용자 작성 내용은 번역하지 않는다.
* ‘시작 시 Myorii 열기’ 스위치는 표시만 구현되어 있으며 운영체제 자동 시작 설정에는 아직 연결되지 않았다.
* 제공자는 **Ollama 로컬 모델 / API** 두 버튼 중 하나만 선택한다.
* 로컬 모드는 실제 설치 모델 드롭다운과 모델 관리 버튼을 나란히 표시한다. 모델 관리에서는 비동기 목록 조회, 선택, 삭제를 지원한다. 현재 선택 모델 삭제는 막으며 다운로드 버튼은 Ollama 라이브러리 웹페이지를 연다.
* API 모드는 OpenAI·Gemini·Claude 서비스 선택, 보기/가리기 가능한 키 입력, 키 저장·삭제, 채팅용 모델 드롭다운을 제공한다. 키 저장 후 목록을 자동 조회하고, 드롭다운 오른쪽의 ‘목록 새로고침’으로 다시 조회한다. 모델 이름 직접 입력은 허용하지 않는다.
* API 키는 macOS 키체인에 저장하고 모델·제공자 선택만 SQLite에 저장한다. 외부 API 사용 시 대화·첨부가 해당 제공자에게 전달된다.
* 드롭다운 화살표는 오른쪽 중앙에 위치하며, 목록은 입력칸 바로 아래에 둥근 테두리로 표시한다.
* 연동은 **MCP · 커넥터 · 플러그인**으로 모델에 외부 도구와 서비스를 연결하는 향후 구현 안내다. 현재 연결 기능이나 Notion 전용 연동 버튼은 없다.
* 정보에는 버전, 도움말 사이트 추후 구현 안내, 문의 및 제안을 표시한다. 도움말 안내와 `heamin0603@naver.com`은 제목 오른쪽의 작은 글자이며 버튼·메일 전송 기능은 없다.
* 앱 종료 버튼은 실제로 애플리케이션을 종료한다.

`storage/preferences_store.py`는 테마·언어, `storage/model_store.py`는 제공자·모델 선택을 SQLite에 저장한다. API 키는 `keyring.backends.macOS.Keyring`을 통해 저장한다. `ui/preferences.py`는 팔레트·스타일·UI 번역을 적용하고 `ui/model_controls.py`는 모델 드롭다운과 비밀번호 보기 전환을 구현한다. `ui/model_manager.py`의 `ModelTask`는 모델 목록 조회와 삭제 등 작업을 별도 스레드에서 실행한다.

`ChatService.set_backend()`는 Ollama 또는 `CloudClient` 스트리밍 경로를 선택한다. OpenAI Responses, Gemini streamGenerateContent, Claude Messages를 사용하며 API 경로에는 Ollama 워밍업·설치 모델 조회를 적용하지 않는다. `ModelRouter`는 선택한 모델을 유지한다. 계정별 실제 접근 권한과 요금은 외부 제공자에 따른다.

히스토리는 의도별로 제한하며 이전 내용을 지칭하지 않는 네이밍·번역은 독립 요청으로 처리한다. 시스템 프롬프트와 현재 입력을 포함한 문자열 예산은 12,000자다. 저장된 첨부 대화는 `model_content`에 모델 참고 내용을 보관해 복원 시 후속 질문을 지원한다. 파일 원본이 사라진 이미지의 재사용에는 제한이 있다.

# macOS 패키징

PyInstaller spec 파일은 아래 경로에서 관리한다.

```text
packaging/macos/Myorii.spec
```

앱 번들에는 메뉴바 아이콘, 탭 아이콘, 설정/전송 아이콘, Myorii 캐릭터 에셋, `prompts/`, `core/tools/`를 포함한다.

빌드 명령은 다음과 같다.

```bash
PYINSTALLER_CONFIG_DIR=/tmp/myorii_pyinstaller .venv/bin/pyinstaller packaging/macos/Myorii.spec --noconfirm --clean
```

---

# 향후 확장 계획

## V2

MCP·커넥터·플러그인 연동 (향후 구현)

```text
integrations/
└── notion/
```

---

## V3

클라우드 동기화

```text
sync/
├── api_client.py
└── sync_manager.py
```

---

## V4

Windows 배포

기존 Core / UI 재사용

Platform Layer만 추가 구현

---

# 설계 원칙

## 1. 플랫폼 독립성

비즈니스 로직은 운영체제에 의존하지 않는다.

---

## 2. 로컬 우선

채팅, 네이밍, 메모는 인터넷 없이 동작한다.

---

## 3. 경량성

항상 백그라운드에 상주하므로 최소 리소스를 사용한다.

---

## 4. 단순성

과도한 추상화보다 유지보수가 쉬운 구조를 우선한다.

## 채팅 할일·메모 도구

`core/tools/chat_tools.py`는 선택된 모델의 JSON 계획을 검증하고 `todo_store`, `memo_store`를 실행한다. `ChatService`의 공통 텍스트 호출을 사용하므로 Ollama, OpenAI, Gemini, Anthropic 모두 같은 경로로 동작한다. `/todo `, `/memo `가 저장소를 지정하며, 태그 없는 할일·메모 자연어 요청도 모델이 추가/조회/검색을 판단한다. 일반 요청은 기존 라우터로 돌아간다.

저장은 실제 SQLite 저장 성공 뒤 확인 응답을 만든다. 이전 대화 참조는 직전 사용자 원문 또는 답변을 선택하며, 사용자 발언을 찾을 때 도구 명령을 제외한다. 요약은 선택된 원문만 별도로 모델에 제공한다. 없는 이전 대화, 잘못된 JSON/대상/검색 ID는 저장하지 않는다. 삭제·완료 처리 도구는 제공하지 않는다.

할일 조회는 미완료 데이터만 출력한다. 오늘 조회는 기한 필드가 없으므로 전체 미완료 할일을 뜻한다. 메모 검색은 저장된 제목/본문을 제한된 크기로 나누어 모델이 관련 ID를 선택하고, 해당 발췌만 답변 모델에 전달한다. 관련 내용이 없으면 답변 모델을 호출하지 않고 찾지 못했다고 응답한다. 답변 끝의 참고 메모 제목은 실제 검색 결과에서 코드가 추가한다. 관련 내용이 답변 컨텍스트 한도를 넘으면 검색 범위를 좁히도록 안내한다.

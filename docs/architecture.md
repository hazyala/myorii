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
* 텍스트/비전 모델 선택
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
├── integrations/      # 예정: Notion 등 외부 서비스 연동
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
├── chat_sessions     (id, title, created_at, updated_at)
├── chat_messages     (id, session_id, role, content, created_at)
├── chat_attachments  (id, message_id, file_path, mime_type, created_at)
├── todos             (id, text, done, ord, created_at, updated_at)
└── memos             (id, title, body, ord, created_at, updated_at)
```

DB 파일은 `~/Library/Application Support/Myorii/myorii.db`에 저장된다.  
앱 재설치 후에도 데이터가 유지된다.  
`ord` 컬럼은 float으로 저장하고, 할 일 드래그 재정렬 완료 시 현재 UI 순서대로 다시 번호를 부여한다.  
V3 클라우드 동기화 시 `chat_attachments`에 `remote_url` 컬럼을 추가해 로컬 파일 없이 URL 접근을 지원한다.

### 역할

* 메모 저장
* 설정 저장
* 세션 저장

### 구성

```text
storage/
├── database.py
├── memo_repository.py
└── settings_repository.py
```

---

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
* 채팅 기록 버튼, 입력창 내부 `+` 파일 선택 액션, 대화 기록 저장 스위치
* 입력부 드래그 앤 드롭 파일 첨부와 첨부 파일 미리보기 카드
* 지원하지 않는 파일 형식에 대한 Assistant 오류 메시지 표시
* `Enter` 전송, `Shift+Enter` 줄바꿈을 처리하는 입력 위젯
* `ChatWorker`를 통한 워커 스레드 기반 토큰 스트리밍
* `ModelListWorker`를 통한 설정 모델 목록 비동기 로딩

채팅 메시지는 `ChatService`가 현재 세션 히스토리를 보관하고, 라우터 계층이 즉시 응답, 의도 분류, 프롬프트 프로필, 모델 선택, 응답 포맷 보정을 처리한 뒤 `OllamaClient`에 스트리밍 요청을 보내는 방식으로 렌더링한다. 모델 목록은 시작 시 기본 모델만 먼저 보여준 뒤 워커 스레드에서 설치 모델을 채워 메인 스레드의 Ollama 호출을 피한다. 응답 완료 후에는 파일명, 함수명, 변수명, 명령어처럼 복사 대상이 되는 기술 항목을 별도 코드블록으로 승격해 개별 복사를 지원한다. 여러 후보는 후보별 코드블록으로 분리하고, 하나의 코드 스니펫이나 셸 스크립트는 하나의 코드블록으로 유지한다.

파일 첨부는 `ChatView`가 전송 전 로컬 파일 경로를 입력부 상태로 보관하고, 입력창 위 미리보기 카드로 표시한다. 전송 시 화면에는 첨부 파일을 사용자 메시지 버블 본문에 섞지 않고 버블 상단 바깥의 미리보기 카드로 렌더링한다. 전송 후 첨부 카드가 한 줄 폭을 넘으면 가로로 넘치지 않고 다음 줄로 재배치한다. LLM 요청 텍스트에는 첨부 파일명을 함께 전달한다. 이미지 첨부는 `ChatAttachmentPayload`로 `ChatWorker`, `ChatService`, `OllamaClient`까지 전달하고, `ImageHandler`가 base64로 변환해 Ollama 요청의 `messages[].images`에 포함한다. `AttachmentRouter`는 비이미지 첨부를 handler에 위임한다. `TextHandler`는 `txt`, `md`, `json`, `yaml`, `yml` 첨부 본문 일부를 `AttachmentContext`로 추출하고, `CsvHandler`는 `csv`, `tsv` 첨부의 컬럼명과 샘플 행을 `AttachmentContext`로 요약한다. `PdfHandler`는 `pdf` 첨부의 일부 페이지 텍스트를 추출하되 스캔/OCR/표 구조 분석은 지원하지 않는다. `DocxHandler`는 `docx` 첨부의 문단/표 텍스트 일부를 추출하되 서식, 이미지, 주석, 변경 추적, 매크로는 분석하지 않는다. `AttachmentContext`는 읽은 범위와 지원 한계를 `제한`, `주의` 문구로 포함한다. `ChatService`는 추출된 context를 user message 본문과 metadata에 추가해 모델 요청에 포함한다. 지원 파일은 이미지(`png`, `jpg`, `jpeg`, `gif`, `bmp`), 텍스트(`txt`, `md`, `json`, `yaml`, `yml`), 표 텍스트(`csv`, `tsv`), 문서/오피스(`pdf`, `docx`, `xlsx`, `pptx`)로 제한하고, 지원하지 않는 파일은 Assistant 메시지로 오류를 렌더링한다. XLSX, PPTX 본문 파싱은 아직 구현되지 않았으며 `AttachmentRouter`의 후속 handler에서 처리한다.

LLM 요청 계약은 `core/llm/contracts.py`의 `ChatRequest`를 기준으로 확장한다. `ChatRequest`는 모델명, 시스템 프롬프트, 히스토리, 사용자 메시지, 첨부 파일, 요청 ID를 하나의 경계로 묶는다. 첨부 파일은 `ChatAttachmentPayload`로 표현하고 이미지, 문서, 스프레드시트, 프레젠테이션 등 타입을 분리한다. 메시지와 첨부에는 `SyncMetadata`를 포함해 로컬 ID, 클라우드 ID, revision, 동기화 상태를 보관할 수 있게 한다. 요청에는 `DeviceContext`를 포함해 향후 로그인 계정, 사용자 ID, 디바이스 ID, 온라인 상태, 동기화 활성 여부를 전달할 수 있게 한다.

설정 화면은 `ui/settings_view.py`에서 별도 구성한다.

* 일반 섹션: 시작 시 열기 스위치, 테마 토글, 언어 토글
* 로컬 모델 섹션: 설치된 Ollama 모델 드롭다운, 모델 관리 버튼
* 연동 섹션: Notion 연동 버튼
* 정보 섹션: 임시 버전, 도움말 버튼, 피드백 버튼
* 앱 종료 버튼: `QApplication.quit`으로 실제 종료

모델 관리, 외부 연동, 도움말, 피드백의 실제 기능 연결은 추후 구현한다. Notion API, 외부 API 서버, Apple 기기간 동기화는 현재 문서상 확장 경계만 정의되어 있으며 실제 호출/동기화 엔진은 아직 구현되지 않았다.
설정 화면의 폰트 크기, 배치, 버튼 형태, 아이콘과 텍스트 간격은 추후 UI 튜닝 범위로 남긴다.

---

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

Notion 연동

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

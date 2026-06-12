# Myorii Router Design

Myorii의 라우터는 무거운 에이전트 시스템이 아니라, 사용자의 요청을 가장 빠른 처리 경로로 보내는 얇은 판단 계층이다.

핵심 목표는 아래 다섯 가지다.

* 빠른 응답
* 개발 편의
* 실시간성
* 간편함
* 창 이동 없음

따라서 모든 요청을 하나의 긴 프롬프트와 하나의 모델로 처리하지 않는다. 먼저 로컬 규칙으로 즉시 처리 가능한 요청을 걸러내고, 필요한 경우에만 짧은 의도별 프롬프트와 적절한 모델을 사용한다.

---

# 전체 흐름

```text
ChatView
  -> ChatRequest
  -> InstantRouter
  -> IntentRouter
  -> AttachmentRouter
  -> PromptProfileResolver
  -> ModelRouter
  -> OllamaClient
  -> ResponseFormatter
```

`ChatRequest`는 모델명, 사용자 메시지, 히스토리, 첨부 파일, 요청 ID, 디바이스/동기화 메타데이터를 담는 요청 계약이다. 라우터 계층은 이 요청을 변경하기보다, 어떤 처리 경로를 사용할지 결정하는 역할에 집중한다.

---

# Router와 Node의 정의

## Router

Router는 요청의 다음 목적지를 결정한다.

```text
request -> route decision
```

예를 들어 이미지가 있으면 vision 모델로 보내고, `사과 영어로`처럼 단순한 요청은 모델 호출 없이 즉시 응답한다.

## Node

Node는 한 가지 일을 수행하는 작은 처리 단위다.

```text
request/context -> transformed context/result
```

초기에는 LangGraph 같은 외부 그래프 런타임을 사용하지 않는다. Myorii는 메뉴바 앱이므로, 복잡한 그래프보다 Python 클래스/함수 기반의 가벼운 파이프라인이 더 적합하다. 나중에 노드 수가 늘어나면 동일한 인터페이스를 유지한 채 그래프 실행기로 교체할 수 있게 한다.

---

# InstantRouter

목표 응답 시간은 0~100ms다. 모델 호출 없이 로컬 규칙, 사전, 템플릿으로 바로 답할 수 있는 요청을 처리한다.

대상 예시는 아래와 같다.

```text
사과 영어로
apple 뜻
오늘 저녁 뭐 먹을까
점심 추천
커피 마실까?
```

초기 구현은 작은 규칙 기반으로 시작한다.

```text
InstantRouter.match(request) -> InstantResponse | None
```

InstantRouter가 응답을 만들면 `ChatService`는 Ollama를 호출하지 않는다.

1차 구현에서는 첨부 파일이 없는 짧은 번역, 단어 뜻, 식사/커피 추천 요청만 처리한다. 그 외 요청은 기존 LLM 경로로 넘겨 브랜드 톤을 해치지 않는 범위에서 즉시 응답 경로를 확장한다.

---

# IntentRouter

InstantRouter가 처리하지 못한 요청은 IntentRouter가 의도를 분류한다. 초기 버전은 LLM 분류가 아니라 키워드/정규식 기반 규칙 라우팅을 사용한다. 라우팅 자체에 LLM을 호출하면 실시간성이 떨어지기 때문이다.

2차 구현에서는 `IntentRouter.route(request) -> IntentRoute` 계약을 추가한다. 이 단계는 아직 모델이나 프롬프트를 바꾸지 않고, 후속 `PromptProfileResolver`와 `ModelRouter`가 사용할 `intent`와 `reason`만 결정한다.

## 개발 네이밍 의도

개발 편의를 위해 자주 쓰는 이름 추천 대상을 의도로 분리한다.

```text
naming_function
naming_method
naming_variable
naming_constant
naming_class
naming_interface
naming_type
naming_file
naming_folder
naming_component
naming_hook
naming_event
naming_endpoint
naming_api
naming_table
naming_column
naming_branch
naming_commit
naming_pr
naming_test
naming_package
naming_env
naming_css_class
```

매칭 예시는 아래와 같다.

```text
함수명 3개 추천              -> naming_function
메서드명 뭐가 좋아?          -> naming_method
변수명 추천                  -> naming_variable
상수명으로 바꿔줘            -> naming_constant
클래스명 추천                -> naming_class
인터페이스명 추천            -> naming_interface
타입명 추천                  -> naming_type
파일명 추천                  -> naming_file
폴더명 추천                  -> naming_folder
React 컴포넌트명 추천        -> naming_component
커스텀 훅 이름 추천          -> naming_hook
이벤트명 추천                -> naming_event
API 엔드포인트명 추천        -> naming_endpoint
DB 테이블명 추천             -> naming_table
컬럼명 추천                  -> naming_column
브랜치명 만들어줘            -> naming_branch
커밋 메시지 추천             -> naming_commit
PR 제목 추천                 -> naming_pr
테스트명 추천                -> naming_test
패키지명 추천                -> naming_package
환경변수명 추천              -> naming_env
CSS 클래스명 추천            -> naming_css_class
```

## 기타 의도

```text
simple_chat
translate
command
commit_message
pr_description
code_explain
code_fix
image_question
image_code_transcription
document_question
spreadsheet_question
```

`image_code_transcription`은 코드 캡처 이미지를 복사 가능한 코드블록으로 복원하는 의도다. 이미지가 있고 사용자가 `코드`, `캡쳐`, `복사`, `텍스트로`, `옮겨줘` 같은 표현을 쓰면 이 의도로 분류한다.

---

# PromptProfileResolver

하나의 거대한 시스템 프롬프트로 모든 요청을 처리하지 않는다. 공통 시스템 프롬프트는 짧게 유지하고, 의도별 프로필 프롬프트를 조립한다.

```text
prompts/
  system.md
  profiles/
    simple_chat.md
    translate.md
    naming_common.md
    naming_function.md
    naming_variable.md
    naming_class.md
    naming_file.md
    command.md
    commit_message.md
    pr_description.md
    image_question.md
    image_code_transcription.md
    document_question.md
```

프롬프트 전략은 의도별로 다르게 사용한다.

```text
simple_chat                 -> zero-shot prompting
translate                   -> zero-shot prompting
naming_*                    -> few-shot prompting
command                     -> few-shot prompting
commit_message              -> few-shot prompting
pr_description              -> few-shot prompting
code_explain                -> zero-shot prompting + format instruction
image_question              -> zero-shot prompting + visual instruction
image_code_transcription    -> few-shot prompting
document_question           -> retrieval-augmented generation, RAG
spreadsheet_question        -> retrieval-augmented generation, RAG
```

단순 채팅과 번역은 예시가 많을수록 느려지므로 zero-shot prompting을 사용한다. 네이밍, 명령어, 커밋/PR, 코드 캡처 복원은 출력 형식이 중요하므로 few-shot prompting으로 예시를 제공한다. PDF/문서/스프레드시트는 본문 전체를 넣지 않고 필요한 일부만 추출해 RAG 방식으로 확장한다.

4차 구현에서는 `PromptProfileResolver`가 공통 `system.md`와 `prompts/profiles/`의 의도별 프로필을 조립한다. `system.md`는 Myorii의 정체성과 공통 응답 원칙만 담고, 네이밍/번역/명령어/커밋/이미지 규칙은 profile 파일로 분리한다.

---

# ModelRouter

모든 요청을 vision 모델로 보내지 않는다. 모델 선택은 속도와 입력 형식에 따라 나눈다.

```text
instant
  -> 모델 호출 없음

simple_chat / translate
  -> fast_text_model

naming_* / command / commit_message / pr_description
  -> fast_text_model

image_question / image_code_transcription
  -> vision_model

document_question / spreadsheet_question
  -> fast_text_model + attachment context
```

초기 설정은 최소 2개 모델로 시작한다.

```text
fast_text_model
vision_model
```

설정 화면에서 사용자가 모델을 고를 수 있게 하되, 라우터는 이미지가 없는 짧은 요청을 fast text 모델로 보내는 기본값을 유지한다.

3차 구현에서는 `ModelRouter.route(request, intent, available_models)`가 모델을 결정한다. 이미지 의도는 vision 모델을 유지하고, 텍스트 의도는 설치된 `MYORII_FAST_TEXT_MODEL` 또는 기본 `qwen3:1.7b`를 우선 사용한다. fast text 모델이 설치되어 있지 않으면 현재 선택 모델로 fallback한다. 모델 목록은 `ChatService`에서 캐시해 매 요청마다 `list_models()`를 호출하지 않는다.

---

# AttachmentRouter

첨부 파일은 모델에 바로 넣지 않는다. 파일 타입별 handler가 입력을 모델에 넣을 수 있는 context로 변환한다.

```text
AttachmentRouter
  -> ImageHandler
  -> TextHandler
  -> CsvHandler
  -> PdfHandler
  -> DocumentHandler
  -> SpreadsheetHandler
  -> PresentationHandler
```

초기 단계는 아래처럼 제한한다.

```text
image
  -> ImageHandler가 base64 images 생성

txt / md / json / yaml / yml
  -> TextHandler가 본문 일부 추출

csv / tsv
  -> CsvHandler가 컬럼명과 샘플 행 요약

pdf
  -> PdfHandler가 일부 페이지 텍스트 추출

docx
  -> DocumentHandler가 문단/표 텍스트 일부 추출

xlsx
  -> SpreadsheetHandler가 시트명, 컬럼명, 샘플 행 요약

pptx
  -> 파일명만 전달 또는 지원 예정 안내
```

현재 구현 기준으로 이미지는 Ollama `messages[].images`에 base64로 전달하고, 텍스트 계열, `csv`, `tsv`, `pdf`, `docx`, `xlsx` 첨부는 `AttachmentRouter`가 `AttachmentContext`로 변환해 user message 본문과 metadata에 추가한다. `AttachmentContext`는 읽은 범위와 지원 한계를 `제한`, `주의` 문구로 함께 전달해 사용자가 요청한 작업이 현재 첨부 파싱 범위를 넘을 때 모델이 이를 명확히 답하도록 한다. PDF는 일부 페이지 텍스트 추출만 지원하며 스캔/OCR/표 구조 분석은 지원하지 않는다. DOCX는 문단/표 텍스트 일부만 지원하며 서식, 이미지, 주석, 변경 추적, 매크로는 분석하지 않는다. XLSX는 시트명, 컬럼명, 샘플 행만 지원하며 전체 행 분석, 수식 재계산, 피벗/차트/서식 분석은 지원하지 않는다. PPTX의 본문 파싱과 요약 전달은 아직 구현되지 않았다.

고급화 단계에서는 다음을 추가한다.

```text
pdf
  -> 텍스트 추출, 페이지별 chunk, 필요 시 페이지 이미지화

docx
  -> 문단, 제목, 표 추출

xlsx
  -> 시트명, 컬럼명, 샘플 행, 간단 통계 요약

large file
  -> chunking + retrieval
```

---

# ResponseFormatter

개발 편의성은 응답 형식에서 결정된다. LLM이 포맷을 지키지 못하는 경우를 대비해 후처리 계층을 둔다.

네이밍 의도에서는 아래 규칙을 강제한다.

* 설명은 짧게 유지한다.
* 후보는 각각 별도 코드블록으로 출력한다.
* 사용자가 개수를 요청하면 가능한 한 정확히 맞춘다.
* 코드블록 안에는 주석이나 설명을 넣지 않는다.

5차 구현에서는 `ResponseFormatter`가 네이밍, 커밋 메시지, 명령어 의도를 후처리한다. 포맷 보정이 필요한 의도는 전체 응답을 버퍼링한 뒤 코드블록 중심으로 정규화하고, 일반 채팅은 기존 스트리밍을 유지한다.

사용자 편의 출력 계약은 아래를 기준으로 한다.

* 사용자가 하나를 선택해야 하는 여러 후보는 후보별 코드블록으로 분리한다.
* 여러 명령어가 독립 실행 단계라면 명령어별 `bash` 코드블록으로 분리한다.
* 하나의 코드 스니펫, 셸 스크립트, 줄 이어쓰기 명령은 하나의 코드블록으로 유지한다.
* 설명, 주의점, 적용 위치, 불확실성 표시는 코드블록 밖의 채팅 문장으로 둔다.
* 코드블록 안에는 복사할 내용만 둔다.

예시:

````markdown
가장 무난한 후보입니다.

```python
validate_user_input
```

```python
normalize_user_payload
```

```python
parse_user_request
```
````

파일명 예시:

````markdown
```text
chat_request_router.py
```

```text
prompt_profile_resolver.py
```

```text
attachment_router.py
```
````

명령어 예시:

````markdown
```bash
.venv/bin/python main.py
```
````

코드 캡처 복원 예시:

````markdown
```python
def validate_user_input(payload: dict) -> bool:
    return bool(payload.get("name") and payload.get("email"))
```
````

---

# 세션 저장과 동기화

채팅은 기본 저장하지 않는다. 사용자가 저장 스위치를 켠 세션만 저장한다.

```text
EphemeralSession
  앱 실행 중 메모리만 유지

SavedSession
  사용자가 저장한 세션만 SQLite 저장

SyncableSession
  로그인 + 저장 + 동기화 활성화된 세션만 서버 동기화
```

동기화는 local-first outbox 구조로 설계한다.

```text
LocalStore
  -> Outbox
  -> SyncEngine
  -> Server
  -> Inbox
  -> LocalStore
```

동작 규칙은 아래와 같다.

* A, B 둘 다 온라인이면 A의 변경을 서버에 즉시 업로드하고 B가 즉시 반영한다.
* A만 온라인이면 A가 서버에 업로드하고, B는 온라인이 되는 시점에 pull한다.
* 둘 다 오프라인이면 각자 local outbox에 보관하고, 먼저 온라인 된 기기가 서버에 업로드한다.
* 다른 기기가 온라인이 되면 서버에서 변경분을 받아 반영한다.
* 충돌은 `revision`, `device_id`, `updated_at`을 기준으로 자동 병합하거나 `conflicted` 상태로 표시한다.

라우터는 저장과 동기화를 직접 수행하지 않는다. 라우터의 책임은 `notion_save`, `sync_status`, `document_question`처럼 요청 의도를 분류하는 데서 끝난다. 실제 Notion API 호출은 `core/integrations/notion/`, Apple 기기간 동기화나 자체 서버 동기화는 `core/sync/`와 `storage/`가 담당한다.

```text
IntentRouter
  -> tool/integration intent

IntegrationService
  -> Notion / external API

LocalStore
  -> Outbox
  -> SyncEngine
  -> iCloud / CloudKit / Server
```

이 경계 덕분에 라우터를 빠르게 유지하면서도, 이후 Notion 연동이나 Apple 기기간 동기화를 local-first 구조로 확장할 수 있다.

---

# 구현 단계

## Phase 1: 라우터 골격

* `Intent` enum 추가
* 규칙 기반 `IntentRouter` 추가
* `simple_chat`, `translate`, `naming_*`, `command`, `image_question`, `image_code_transcription` 분류
* 기존 `ChatService` 앞단에 라우팅 결과를 전달

## Phase 2: 프롬프트 프로필

* `prompts/profiles/` 추가
* `system.md`는 공통 정체성과 짧은 응답 원칙만 유지
* `naming_common.md`, `command.md`, `commit_message.md`는 few-shot prompting 적용
* `simple_chat.md`, `translate.md`는 zero-shot prompting 적용

## Phase 3: 응답 포맷터

* `ResponseFormatter` 추가
* 네이밍 후보를 개별 코드블록으로 보정
* 명령어, 파일명, 환경변수, 코드 캡처 복원 결과의 fence language 보정

## Phase 4: 모델 라우터

* `ModelRouter` 추가
* 이미지 없는 짧은 요청은 `fast_text_model`
* 이미지 요청과 코드 캡처 복원은 `vision_model`
* 매 요청마다 모델 목록을 조회하지 않도록 캐싱

## Phase 5: Instant 응답

* `InstantRouter` 추가
* 단어 번역, 간단한 음식 추천, 짧은 잡담은 모델 호출 없이 처리
* 1초 이내가 아니라 즉시 응답을 목표로 한다.

## Phase 6: 첨부 라우터

* 현재 이미지 base64 변환은 `ImageHandler`가 담당
* `TextHandler`: `txt`, `md`, `json`, `yaml`, `yml` 본문 일부 추출
* `CsvHandler`: `csv`, `tsv` 컬럼명과 샘플 행 요약
* `ChatService`: 첨부 context를 user message 본문과 metadata에 추가
* `PdfHandler`: 일부 페이지 텍스트 추출, 스캔/OCR/표 구조 분석 제외
* `DocumentHandler`: `docx` 문단/표 텍스트 일부 추출
* `SpreadsheetHandler`: 시트명, 컬럼명, 샘플 행 요약
* `PresentationHandler`: 슬라이드 제목과 주요 텍스트 요약
* `TextHandler`로 txt/md/json/csv 일부 본문 전달
* 이후 pdf/docx/xlsx/pptx handler 확장

## Phase 7: 저장 세션

* 기본 비저장 세션 유지
* 저장 스위치 ON인 세션만 SQLite에 기록
* 저장 세션만 동기화 후보로 전환

## Phase 8: SyncEngine

* `Outbox`, `Inbox`, `SyncEngine` 추가
* `SyncMetadata`의 `local_id`, `cloud_id`, `revision`, `state`를 실제 저장소와 연결
* 온라인/오프라인 상태에 따라 push/pull 재시도

---

# 초기 구현 원칙

* 라우팅은 먼저 규칙 기반으로 구현한다.
* LLM 기반 intent classification은 마지막 fallback으로만 고려한다.
* 프롬프트는 짧게 유지하고 의도별로 조립한다.
* 출력 형식은 프롬프트와 `ResponseFormatter`가 함께 보장한다.
* 외부 그래프 런타임은 도입하지 않는다.
* 노드는 작고 순수 Python에 가깝게 유지한다.
* UI는 라우터 세부 구현을 알지 못하고 `ChatRequest`만 전달한다.

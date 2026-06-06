# 📖 Development Rules

Myorii 프로젝트의 개발 규칙 및 협업 기준을 정의한다.

---

# 브랜치 전략

## 구조

```text
main
 └── dev
      ├── feature/*
      ├── fix/*
      └── docs/*
```

---

## main

배포 가능한 안정 버전만 유지한다.

직접 개발하지 않는다.

모든 변경은 Pull Request를 통해 반영한다.

---

## dev

개발 통합 브랜치

모든 기능 개발의 기준 브랜치

---

## feature/*

기능 단위 개발

예시

```text
feature/menubar
feature/chat
feature/memo
feature/settings
feature/image-analysis
```

---

## fix/*

버그 수정

예시

```text
fix/window-position
fix/memory-leak
fix/clipboard
```

---

## docs/*

문서 작업

예시

```text
docs/readme
docs/architecture
docs/roadmap
```

---

# 커밋 규칙

## 형식

```text
type: 설명
```

---

## 타입

### feat

새로운 기능

예시

```text
feat: 메뉴바 아이콘 생성
feat: 메모 저장 기능 구현
```

---

### fix

버그 수정

예시

```text
fix: 창 위치 계산 오류 수정
```

---

### ui

UI 변경

예시

```text
ui: 설정 화면 레이아웃 수정
```

---

### refactor

리팩토링

예시

```text
refactor: LLM 호출 구조 개선
```

---

### docs

문서 수정

예시

```text
docs: 아키텍처 문서 추가
```

---

### chore

설정 및 환경 구성

예시

```text
chore: 프로젝트 초기 구조 생성
chore: 의존성 추가
```

---

# Pull Request 규칙

## Feature → Dev

기능 개발 완료 후 dev 브랜치로 병합

예시

```text
feature/chat
↓
dev
```

---

## Dev → Main

안정화 완료 후 main 브랜치로 병합

배포 가능한 상태에서만 진행

---

# 프로젝트 구조 규칙

## Core

비즈니스 로직만 포함

```text
core/
```

허용

```text
LLM
Naming
Image Analysis
Clipboard
```

금지

```text
PyQt UI 코드
OS 의존 코드
```

---

## Platform

운영체제 의존 코드만 포함

```text
platform/
```

허용

```text
Menu Bar
System Tray
Window Position
```

---

## UI

화면 표시만 담당

```text
ui/
```

허용

```text
Widget
Layout
Animation
```

금지

```text
LLM 호출
DB 저장
```

---

## Storage

데이터 저장 전용

```text
storage/
```

허용

```text
SQLite
Settings
Memo
```

---

# 코드 스타일

## Python

PEP8 준수

---

## 네이밍

### 클래스

```python
class ChatView:
```

PascalCase

---

### 함수

```python
def save_memo():
```

snake_case

---

### 상수

```python
APP_NAME = "Myorii"
```

UPPER_CASE

---

# Git Ignore 규칙

추적 금지

```text
.venv/
__pycache__/
.env

*.db
*.sqlite3

dist/
build/

.DS_Store
```

---

# 문서 관리 규칙

README

프로젝트 소개

---

architecture.md

시스템 구조

---

roadmap.md

버전 계획

---

ui-guide.md

UI 설계

---

development-rule.md

개발 규칙

---

# 설계 원칙

## 단순성

과도한 추상화 금지

---

## 유지보수성

읽기 쉬운 코드 우선

---

## 플랫폼 독립성

비즈니스 로직은 OS에 의존하지 않는다.

---

## 로컬 우선

핵심 기능은 인터넷 없이 동작해야 한다.

---

## 사용자 경험 우선

기술보다 사용 흐름을 우선 고려한다.

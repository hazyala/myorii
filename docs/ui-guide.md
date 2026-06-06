# 🎨 UI Guide

Myorii의 UI 설계 기준 및 화면 구성을 정의한다.

---

# 디자인 컨셉

## 키워드

* Apple Inspired
* Glassmorphism
* Minimal
* Lightweight
* Companion

---

## 디자인 목표

Myorii는 생산성 도구이지만 생산성 앱처럼 보이지 않는다.

작은 고양이 친구가 메뉴바에 살면서 사용자의 작업을 돕는 경험을 제공한다.

복잡한 기능보다 빠른 접근성과 직관성을 우선한다.

---

# 캐릭터 컨셉

## Myorii

검은 고양이

빨간 장화

동글동글한 실루엣

---

## 상태 표현

### Idle

* 눈 깜빡임

### Thinking

* 꼬리 흔들기

### Success

* 기뻐하는 반응


---

# 디자인 시스템

## Design Style

Apple Inspired Glassmorphism

---

## Color Strategy

화이트 기반

차분한 블루 포인트

---

## Background

#FFFFFF

---

## Accent

Myorii Blue

(개발 단계에서 최종 확정)

---

## Radius

20~24px

---

## Shadow

Soft Apple Style Shadow

---

## Typography

SF Pro (macOS)

Segoe UI (Windows)

Pretendard (Fallback)

---

# 화면 구조

## 메뉴바

### 목적

앱 진입점

### 기능

* 창 열기
* 창 닫기

### 캐릭터

Myorii 아이콘 사용

---

# 메인 창

### 구조

```text
┌────────────────────┐
│   Header           │
├────────────────────┤
│ Chat | Todo│ Memo  │
├────────────────────┤
│                    │
│ Content Area       │
│                    │
├────────────────────┤
│ Input Area         │
└────────────────────┘
```

---

# 채팅 화면

## 목업

![Chat](../assets/mockups/chat.png)

---

## 목적

기본 진입 화면

---

## 주요 기능

* 일반 채팅
* 네이밍
* 이미지 분석

---

## UI 구성

### Header

* Myorii 캐릭터
* 설정 버튼

### Chat Area

* 사용자 메시지
* AI 응답

### Input Area

* 텍스트 입력
* 이미지 붙여넣기
* 전송 버튼

---

## UX 원칙

* 앱 시작 시 기본 진입 화면
* 입력창 항상 하단 고정
* 코드 블록 원클릭 복사

---

# 메모 화면

## 목업

![Memo](../assets/mockups/memo.png)

---

## 목적

빠른 메모 저장

---

## 주요 기능

* 메모 작성
* 메모 수정
* 메모 삭제

---

## UI 구성

### 메모 목록

최근 작성 순 정렬

### 새 메모 버튼

하단 고정

---

## UX 원칙

* 한 번의 클릭으로 메모 생성
* 복잡한 폴더 구조 없음

---

# 할일 화면 (V2)

## 목업

![Todo](../assets/mockups/todo.png)

---

## 목적

Notion 할일 관리

---

## 주요 기능

* 오늘의 할일 표시
* 완료 체크
* Notion 동기화

---

## UI 구성

### Todo List

체크박스 기반

### 상태 표시

* 완료
* 진행 중

---

## UX 원칙

* Notion을 열 필요 없음
* 오늘 해야 할 일만 표시

---

# 설정 화면

## 목업

![Settings](../assets/mockups/settings.png)

---

## 목적

앱 환경 설정

---

## 주요 기능

### 모델 선택

```text
qwen3-vl:4b
```

---

### 언어 설정

```text
한국어
English
```

---

### 시작 시 실행

자동 실행 여부

---

### 앱 종료

Myorii 종료

---

# 창 동작 규칙

## macOS

메뉴바 아이콘 클릭

↓

아이콘 바로 아래 팝업

↓

다시 클릭 시 닫힘

---

## Windows

시스템 트레이 클릭

↓

아이콘 바로 위 팝업

↓

다시 클릭 시 닫힘

---

# 반응형 규칙

## 최소 크기

```text
400 × 650
```

---

## 최대 크기

고정 크기 사용

사용자 리사이즈 비활성화

---

# 에셋 구조

```text
assets/
├── icons/
│   └── myorii_menubar.png
│
├── characters/
│   └── myorii_idle.png
│
└── mockups/
    ├── myorii.png
    ├── chat.png
    ├── memo.png
    ├── todo.png
    └── settings.png
```

---

# UI 원칙

## 1. 빠른 접근

항상 1~2번의 클릭 안에 기능 도달

---

## 2. 단순성

설정보다 사용을 우선

---

## 3. 일관성

모든 화면 동일한 레이아웃 사용

---

## 4. 컴패니언 경험

AI 비서가 아닌 작은 고양이 친구처럼 느껴져야 한다.

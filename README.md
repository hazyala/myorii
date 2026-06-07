# 🐈 Myorii

> 메뉴바에 사는 작은 고양이 생산성 도우미

Myorii는 macOS 메뉴바 및 Windows 시스템 트레이에 상주하며, 사용자가 가장 자주 사용하는 생산성 기능을 창 이동 없이 즉시 사용할 수 있도록 돕는 로컬 LLM 기반 데스크톱 컴패니언 애플리케이션입니다.

---

# ✨ 프로젝트 소개

개발 작업이나 문서 작업 중에는 다음과 같은 불편함이 자주 발생합니다.

* 변수명, 함수명, 파일명을 정하기 위해 번역기나 AI를 반복적으로 열어야 함
* 간단한 질문을 하기 위해 새로운 브라우저 탭을 열어야 함
* 메모를 위해 별도 앱을 실행해야 함
* 여러 생산성 도구를 오가며 작업 흐름이 끊김

Myorii는 이러한 문제를 해결하기 위해 메뉴바에 항상 상주하며, 작은 팝업 창 하나로 네이밍, 채팅, 메모 기능을 제공합니다.

---

# 🎯 MVP 목표

## V1

### 네이밍 헬퍼

* 한국어 설명 입력
* 변수명 추천
* 함수명 추천
* 파일명 추천
* 클래스명 추천

### 간단한 채팅

* 로컬 LLM 기반 질의응답
* 문장 다듬기
* 커밋 메시지 생성
* 간단한 코드 관련 질문

### 이미지 분석

* 스크린샷 붙여넣기
* 에러 화면 분석
* 간단한 이미지 기반 질의응답

### 메모

* 간단한 메모 작성
* 수정
* 삭제
* 로컬 저장

---

# 🚀 로드맵

## V1

* 채팅
* 네이밍
* 이미지 분석
* 메모

## V2

* Notion 연동
* 오늘의 할 일 관리

## V3

* 클라우드 동기화
* myorii 캐릭터 움직임 구현 (눈 깜빡임, 꼬리 흔들림, 기뻐하기 등)

## V4

* Windows 지원

## V5

* 공식 홈페이지
* 설치 페이지
* 자동 업데이트

---

# 🛠 기술 스택

| 역할            | 기술               |
| ------------- | ---------------- |
| Language      | Python 3.12+     |
| UI            | PyQt6            |
| Menu Bar      | PyQt6 QSystemTrayIcon |
| LLM           | Ollama           |
| Model         | qwen3-vl:4b      |
| Database      | SQLite           |
| Clipboard     | PyQt6 QClipboard |
| Build         | PyInstaller      |
| macOS Package | create-dmg       |

---

# 📂 프로젝트 구조

```text
myorii/
├── assets/
│
├── app/
│
├── core/
│
├── storage/
│
├── ui/
│   ├── widgets/
│   └── styles/
│
├── platform/
│   ├── macos/
│   └── windows/
│
├── packaging/
│   └── macos/
│       └── Myorii.spec
│
├── docs/
│
├── main.py
├── requirements.txt
└── README.md
```

---

# 🧩 플랫폼 분기 전략

비즈니스 로직은 플랫폼과 독립적으로 작성한다.

```text
core/
```

플랫폼 의존 코드는 분리한다.

```text
platform/macos/
platform/windows/
```

운영체제에 따라 런타임에서 자동 선택한다.

```python
import sys

if sys.platform == "darwin":
    ...
elif sys.platform == "win32":
    ...
```

---

# 🌱 브랜치 전략

```text
main
 └── dev
      ├── feature/*
      ├── fix/*
      └── docs/*
```

## main

배포 가능한 안정 버전만 유지

## dev

개발 통합 브랜치

## feature/*

기능 개발

## fix/*

버그 수정

## docs/*

문서 작업

---

# 📌 커밋 규칙

형식

```text
type: 설명
```

예시

```text
feat: 네이밍 추천 기능 구현
fix: 메뉴바 위치 계산 오류 수정
ui: 메모 화면 디자인 수정
refactor: LLM 호출 구조 개선
docs: 개발 문서 추가
chore: 의존성 업데이트
```

---

# ▶ 실행 방법

## 가상환경 생성

```bash
python3 -m venv .venv
```

## 활성화

```bash
source .venv/bin/activate
```

## 패키지 설치

```bash
pip install -r requirements.txt
```

## Ollama 실행

```bash
ollama serve
```

## 모델 다운로드

```bash
ollama pull qwen3-vl:4b
```

## 실행

개발 중에는 아래 명령으로 실행한다.

```bash
python main.py
```

현재 구현 기준으로 Myorii 메뉴바 아이콘을 클릭하면 메인 창이 바로 토글된다.

* 첫 번째 클릭: 아이콘 위치 근처에 메인 창 표시
* 두 번째 클릭: 메인 창 닫기

메뉴바 아이콘은 현재 36px 기준으로 렌더링한다.

## 현재 UI 구현 범위

현재 메인 창은 채팅, 할일, 메모 탭이 포함된 PyQt6 팝오버 화면이다.

* 채팅, 할일, 메모 탭은 하나만 선택된다.
* 선택된 탭에 맞춰 중앙 컨텐츠 영역이 전환된다.
* 채팅 내용은 Ollama 연동 이후 실제 메시지를 표시할 예정이므로 현재는 비워 둔다.
* Header에는 인터넷 연결 상태에 따라 `온라인` 또는 `오프라인`이 표시된다.
* 채팅 입력 영역에는 실제 클릭 가능한 대화 기록 저장 스위치가 포함된다.

## 현재 Python 의존성

현재 구현 기준 추가 패키지는 필요하지 않다.

```text
PyQt6>=6.7
pyinstaller>=6.0,<7.0
```

## macOS 앱 빌드 실행

PyInstaller로 macOS 앱 번들을 생성 후 실행한다.

```bash
PYINSTALLER_CONFIG_DIR=/tmp/myorii_pyinstaller pyinstaller packaging/macos/Myorii.spec --noconfirm --clean
open -n dist/Myorii.app
```

## 실행 종료

현재는 앱 종료 버튼을 설정 화면에서 추후 구현할 예정이므로, 개발 중 종료는 프로세스를 직접 종료한다.

```bash
pkill -f Myorii
```

터미널에서 `python main.py`로 실행한 경우에는 `Ctrl+C`로 종료할 수 있다.

---

# 🐾 브랜드 컨셉

Myorii는 AI 비서가 아닙니다.

사용자 옆에서 함께 일하는 작은 고양이 친구입니다.

* 대기 → 눈 깜빡임
* 생각 → 꼬리 흔들림
* 응답 완료 → 기뻐하기

작고 귀엽지만,
가장 빠르게 도움을 주는 데스크톱 컴패니언을 목표로 합니다.

# 수동 테스트 케이스

이 문서는 사용자가 직접 수행할 테스트 목록이다. AI가 수행한 테스트 결과를 기록하는 문서가 아니며, 기능별 구현 상태를 확인하고 이후 디버깅과 오류 수정을 추적하기 위한 기준 목록으로 사용한다.

테스트 상태는 `미실행`, `성공`, `실패`, `이슈 발견` 중 하나를 우선 사용한다. 첨부 handler 자체 문제가 아닌 응답 중복, 스트리밍, 메시지 렌더링, LLM 응답 포맷 문제도 이 문서에 함께 기록한다.

## 첨부파일 정상 케이스

| ID | 파일 | Handler | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-NORMAL-001 | `normal/sample.txt` | TextHandler | 성공 | 첨부한 텍스트 파일 내용을 읽고, 핵심 내용을 3줄로 요약해줘. | 첨부 본문 인식 및 내용 기반 응답 확인 |
| ATTACH-NORMAL-002 | `normal/sample.md` | TextHandler | 성공 | 첨부한 마크다운 파일 내용을 읽고, 문서의 제목과 주요 항목을 요약해줘. | Markdown 제목, 주요 항목, 코드 블록, 표 구조 기반 응답 확인 |
| ATTACH-NORMAL-003 | `normal/sample.json` | TextHandler | 성공 | 첨부한 JSON 파일을 읽고, 최상위 필드와 주요 값을 요약해줘. | JSON 제목, 설명, 상품 3개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-004 | `normal/sample.yaml` | TextHandler | 성공 | 첨부한 YAML 파일을 읽고, 주요 키와 값을 요약해줘. | YAML 제목, 설명, 상품 2개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-005 | `normal/sample.yml` | TextHandler | 성공 | 첨부한 YML 파일을 읽고, 주요 키와 값을 요약해줘. | YML 제목, 설명, 상품 2개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-006 | `normal/sample.csv` | CsvHandler | 성공 | 첨부한 CSV 파일의 컬럼명과 샘플 행을 요약해줘. | CSV 컬럼명과 샘플 행 요약이 하나의 Assistant 응답으로 정상 표시됨 |
| ATTACH-NORMAL-007 | `normal/sample.tsv` | CsvHandler | 성공 | 첨부한 TSV 파일의 컬럼명과 샘플 행을 요약해줘. | 컬럼명 5개와 샘플 데이터 행 인식 확인 |
| ATTACH-NORMAL-008 | `normal/sample.png` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 이미지 라벨 `sample.png - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-009 | `normal/sample.jpg` | ImageHandler | 성공 | 첨부한 이미지 3줄로 설명해줘. | JPG 이미지 라벨과 ImageHandler 테스트 목적 인식 확인 |
| ATTACH-NORMAL-010 | `normal/sample.jpeg` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 새 세션에서 이미지 라벨 `sample.jpeg - ImageHandler test` 인식 확인. 응답 용량 초과 시 대화 누적/첨부 용량 초과를 구분한 사용자용 메시지 표시 확인 |
| ATTACH-NORMAL-011 | `normal/sample.gif` | ImageHandler | 성공 | 첨부한 이미지 분석해서 어떤건지 요약해줘. | 이미지 설명 요청에서는 이미지 요약만 답하고 요청하지 않은 코드 예시를 만들지 않음 |
| ATTACH-NORMAL-012 | `normal/sample.bmp` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 이미지 라벨 `sample.bmp - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-013 | `normal/sample.pdf` | PdfHandler | 성공 | 첨부한 PDF의 페이지별 핵심 내용을 요약해줘. | `pypdf` 누락/fallback 오진 없이 PDF 텍스트 추출 경로가 동작함 |
| ATTACH-NORMAL-014 | `normal/sample.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서의 제목, 문단, 표 내용을 요약해줘. | 제목, 문단, 마지막 문단, 표 텍스트 인식 확인 |
| ATTACH-NORMAL-015 | `normal/sample.xlsx` | XlsxHandler | 성공 | 첨부한 XLSX 파일의 시트별 컬럼과 샘플 데이터를 요약해줘. | 재고/매출 시트명, 컬럼명, 샘플 데이터를 읽는 것을 확인 |
| ATTACH-NORMAL-016 | `normal/sample.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드별 텍스트를 요약해줘. | 3개 슬라이드의 제목/본문 텍스트 인식 확인 |

## 첨부파일 에러/엣지 케이스

| ID | 파일 | Handler | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-EDGE-001 | `edge_cases/empty.txt` | TextHandler | 성공 | 첨부한 텍스트 파일 내용을 요약해줘. | 빈 파일이라 요약할 내용이 없음을 안전하게 안내 |
| ATTACH-EDGE-002 | `edge_cases/large_context_limit.txt` | TextHandler | 성공 | 첨부한 큰 텍스트 파일의 앞부분 기준으로 핵심 내용을 요약해줘. | 앞부분 더미 텍스트를 요약하고 본문 끝부분이 잘렸음을 안내 |
| ATTACH-EDGE-003 | `edge_cases/malformed.json` | TextHandler | 성공 | 첨부한 JSON 파일을 읽고 주요 내용을 요약해줘. | 잘못된 JSON 구조와 파싱 실패 가능성을 안전하게 안내 |
| ATTACH-EDGE-004 | `edge_cases/invalid.yaml` | TextHandler | 성공 | 첨부한 YAML 파일을 읽고 주요 내용을 요약해줘. | YAML 오류 내용을 안전하게 안내하고 목록/들여쓰기/코드블록 경계를 안정적으로 유지 |
| ATTACH-EDGE-005 | `edge_cases/empty_rows.csv` | CsvHandler | 성공 | 첨부한 CSV 파일의 컬럼명과 데이터 행을 요약해줘. | 컬럼명 5개와 데이터 행 없음 상태를 안내 |
| ATTACH-EDGE-006 | `edge_cases/corrupted.png` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 손상 이미지 전송 시 원시 API 오류 대신 이미지 파일을 읽을 수 없다는 사용자용 메시지 표시 확인 |
| ATTACH-EDGE-007 | `edge_cases/empty.pdf` | PdfHandler | 성공 | 첨부한 PDF 내용을 요약해줘. | `pypdf` 누락 안내 없이 추출 가능한 텍스트가 없음을 안전하게 안내 |
| ATTACH-EDGE-008 | `edge_cases/empty.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서 내용을 요약해줘. | 추출 가능한 문서 텍스트가 없음을 안전하게 안내 |
| ATTACH-EDGE-009 | `edge_cases/empty_sheet.xlsx` | XlsxHandler | 성공 | 첨부한 XLSX 파일의 시트 내용을 요약해줘. | 빈 시트를 읽고 분석 가능 데이터가 없음을 안내하는 것을 확인 |
| ATTACH-EDGE-010 | `edge_cases/empty.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드 내용을 요약해줘. | 전체 슬라이드 1개와 텍스트 없음 상태를 안전하게 안내 |
| ATTACH-EDGE-011 | `edge_cases/unsupported.exe` | Unsupported | 성공 | 첨부한 파일 내용을 확인해줘. | 드래그 중에는 오류 메시지를 만들지 않고, 드롭 완료 시점에 미지원 형식 오류를 1회만 표시함 |
| ATTACH-EDGE-012 | `edge_cases/unsupported.zip` | Unsupported | 성공 | 첨부한 파일 내용을 확인해줘. | 드래그 중에는 오류 메시지를 만들지 않고, 드롭 완료 시점에 미지원 형식 오류를 1회만 표시함 |

## 응답 품질 정상 케이스

| ID | 영역 | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- |
| RESPONSE-NORMAL-001 | 일반 대화 | 성공 | 안녕 | 짧은 일상 대화는 코드블록 없이 일반 문장으로 응답 |
| RESPONSE-NORMAL-002 | 일반 요약 | 성공 | 이 내용 요약해줘 | 요약/분석류 읽기 답변은 사용자가 코드 산출물을 요청하지 않는 한 일반 문장으로 표시 |
| RESPONSE-NORMAL-003 | 네이밍 | 성공 | 자바 덧셈 변수명 3개만 추천해줘봐 | `think=False` 적용 후 빈 응답 실패 없이 Java 관례에 맞는 `camelCase` 후보만 코드블록으로 표시 |
| RESPONSE-NORMAL-004 | 네이밍 | 성공 | 자바 사용자 프로필 클래스명 3개 추천해줘 | 클래스명 후보를 `PascalCase` 후보별 코드블록으로 표시 |
| RESPONSE-NORMAL-005 | 짧은 단어 번역 | 성공 | 단어 사과 영어로 뭐야? | 짧은 단어/용어 번역은 복사 가능한 `text` 코드블록으로 표시 |
| RESPONSE-NORMAL-006 | 문장 번역 | 성공 | 처음 뵙겠습니다 영어로 번역해줘 | 문장 번역은 일반 문장으로 표시하고 불필요한 코드블록을 만들지 않음 |
| RESPONSE-NORMAL-007 | 코드 생성 | 성공 | 파이썬 코드 줘 리스트 중복 제거 | Python 코드는 `python` 코드블록 하나로 표시하고 줄바꿈/들여쓰기를 유지 |
| RESPONSE-NORMAL-008 | 코드 생성 | 성공 | 자바 코드 줘 사용자 클래스 | Java 코드는 `java` 코드블록 하나로 표시하고 줄바꿈/들여쓰기를 유지 |
| RESPONSE-NORMAL-009 | 코드 생성 | 성공 | HTML 코드 줘 로그인 폼 | HTML 코드는 `html` 코드블록 하나로 표시하고 태그 줄바꿈을 유지 |
| RESPONSE-NORMAL-010 | 코드 생성 | 성공 | CSS 코드 줘 버튼 스타일 | CSS 코드는 `css` 코드블록 하나로 표시하고 들여쓰기를 유지 |
| RESPONSE-NORMAL-011 | 코드 생성 | 성공 | C언어 코드 줘 hello world | C 코드는 `c` 코드블록 하나로 표시하고 탭/스페이스 들여쓰기를 유지 |
| RESPONSE-NORMAL-012 | SQL 생성 | 성공 | 활성 사용자 조회 SQL문 줘 | SQL은 `sql` 코드블록 하나로 표시하고 줄바꿈을 유지 |
| RESPONSE-NORMAL-013 | 명령어 | 성공 | 터미널에서 실행 명령어 알려줘 | 실행 명령어는 `bash` 코드블록으로 표시하고 독립 명령은 분리 |

## 응답 품질 에러/엣지 케이스

| ID | 영역 | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- |
| RESPONSE-EDGE-001 | Thinking 모델 | 성공 | 자바 덧셈 변수명 3개만 추천해줘봐 | Ollama 호출에 `think=False`를 전달해 thinking-only 스트림으로 인한 빈 Assistant 응답을 방지 |
| RESPONSE-EDGE-002 | 코드블록 과잉 방지 | 성공 | 분석해줘 | 코드 맥락 없는 일반 분석 요청은 `simple_chat`으로 라우팅하고 코드블록을 만들지 않음 |
| RESPONSE-EDGE-003 | 코드 생성 모델 선택 | 성공 | 자바 코드 줘 사용자 클래스 | 코드 생성 요청은 fast text 모델이 설치되어 있어도 현재 선택 모델을 사용 |
| RESPONSE-EDGE-004 | 첨부 요약 포맷 | 미실행 | CSV/XLSX 첨부 후 컬럼과 샘플 데이터를 요약해줘 | 컬럼명/샘플 값이 과도한 인라인 백틱이나 복사 카드로 승격되지 않는지 확인 |
| RESPONSE-EDGE-005 | Markdown 렌더링 순서 | 성공 | 설명, 코드, 주의점이 함께 있는 응답 생성 | 텍스트와 코드블록이 원래 응답 순서대로 표시되는지 확인 |
| RESPONSE-EDGE-006 | 실제 빈 모델 응답 | 성공 | 임의의 짧은 네이밍/번역 요청 | 모델이 content 없이 종료하면 빈 Assistant history를 저장하지 않고 "모델 응답이 비어 있습니다" 사용자용 오류를 표시 |

## 향후 기능 테스트 작성 규칙

새 기능 테스트는 기능 영역별 섹션을 추가하고, 첨부 테스트는 `ID`, `파일`, `Handler`, `테스트 상태`, `테스트 프롬프트`, `확인 내용` 형식을 유지한다. 첨부 없는 응답 품질 테스트는 `ID`, `영역`, `테스트 상태`, `테스트 프롬프트`, `확인 내용` 형식을 사용한다. 실제 샘플 파일이 있는 테스트는 파일 1개당 테스트 1개로 기록한다.

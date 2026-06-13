# 수동 테스트 케이스

이 문서는 사용자가 직접 수행할 테스트 목록이다. AI가 수행한 테스트 결과를 기록하는 문서가 아니며, 기능별 구현 상태를 확인하고 이후 디버깅과 오류 수정을 추적하기 위한 기준 목록으로 사용한다.

테스트 상태는 `미실행`, `성공`, `실패`, `이슈 발견` 중 하나를 우선 사용한다. 첨부 handler 자체 문제가 아닌 응답 중복, 스트리밍, 메시지 렌더링, LLM 응답 포맷 문제도 이 문서에 함께 기록한다. AI가 로컬에서 수행한 코드 검증 결과는 이 문서의 `성공` 상태로 기록하지 않고, 사용자가 직접 확인한 결과만 반영한다.

## 첨부파일 정상 케이스

| ID | 파일 | Handler | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-NORMAL-001 | `normal/sample.txt` | TextHandler | 성공 | 첨부한 텍스트 파일 내용을 읽고, 핵심 내용을 3줄로 요약해줘. | 첨부 본문 인식 및 내용 기반 응답 확인 |
| ATTACH-NORMAL-002 | `normal/sample.md` | TextHandler | 성공 | 첨부한 마크다운 파일 내용을 읽고, 문서의 제목과 주요 항목을 요약해줘. | Markdown 제목, 주요 항목, 코드 블록, 표 구조 기반 응답 확인 |
| ATTACH-NORMAL-003 | `normal/sample.json` | TextHandler | 성공 | 첨부한 JSON 파일을 읽고, 최상위 필드와 주요 값을 요약해줘. | JSON 제목, 설명, 상품 3개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-004 | `normal/sample.yaml` | TextHandler | 성공 | 첨부한 YAML 파일을 읽고, 주요 키와 값을 요약해줘. | YAML 제목, 설명, 상품 2개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-005 | `normal/sample.yml` | TextHandler | 성공 | 첨부한 YML 파일을 읽고, 주요 키와 값을 요약해줘. | YML 제목, 설명, 상품 2개, 메타 정보 기반 응답 확인 |
| ATTACH-NORMAL-006 | `normal/sample.csv` | CsvHandler | 이슈 발견 | 첨부한 CSV 파일의 컬럼명과 샘플 행을 요약해줘. | 응답이 CSV 컬럼/샘플 행 요약으로 이어지지 않고 무관한 문장과 부분 코드블록처럼 표시됨. 후속 질문에서도 첨부 데이터를 직접 읽지 못했다는 답변과 출력 깨짐 발생 |
| ATTACH-NORMAL-007 | `normal/sample.tsv` | CsvHandler | 성공 | 첨부한 TSV 파일의 컬럼명과 샘플 행을 요약해줘. | 컬럼명 5개와 샘플 데이터 행 인식 확인 |
| ATTACH-NORMAL-008 | `normal/sample.png` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 이미지 라벨 `sample.png - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-009 | `normal/sample.jpg` | ImageHandler | 성공 | 첨부한 이미지 3줄로 설명해줘. | JPG 이미지 라벨과 ImageHandler 테스트 목적 인식 확인 |
| ATTACH-NORMAL-010 | `normal/sample.jpeg` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 새 세션에서 이미지 라벨 `sample.jpeg - ImageHandler test` 인식 확인. 응답 용량 초과 시 대화 누적/첨부 용량 초과를 구분한 사용자용 메시지 표시 확인 |
| ATTACH-NORMAL-011 | `normal/sample.gif` | ImageHandler | 이슈 발견 | 첨부한 이미지 분석해서 어떤건지 요약해줘. | GIF 이미지 라벨과 테스트 목적은 인식했으나, 요청하지 않은 코드 예시와 분리된 코드블록이 함께 출력됨 |
| ATTACH-NORMAL-012 | `normal/sample.bmp` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 이미지 라벨 `sample.bmp - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-013 | `normal/sample.pdf` | PdfHandler | 성공 | 첨부한 PDF의 페이지별 핵심 내용을 요약해줘. | `pypdf` 누락/fallback 오진 없이 PDF 텍스트 추출 경로가 동작함. 동일 답변 반복, 추출 텍스트 과해석, 코드블록 카드 분리 렌더링은 응답/렌더링 안정성 항목에서 별도 처리 |
| ATTACH-NORMAL-014 | `normal/sample.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서의 제목, 문단, 표 내용을 요약해줘. | 제목, 문단, 마지막 문단, 표 텍스트 인식 확인 |
| ATTACH-NORMAL-015 | `normal/sample.xlsx` | XlsxHandler | 성공 | 첨부한 XLSX 파일의 시트별 컬럼과 샘플 데이터를 요약해줘. | 재고/매출 시트명, 컬럼명, 샘플 데이터를 읽는 것을 확인. 동일 문구 반복 출력은 응답 안정성 항목에서 별도 처리 |
| ATTACH-NORMAL-016 | `normal/sample.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드별 텍스트를 요약해줘. | 3개 슬라이드의 제목/본문 텍스트 인식 확인 |

## 첨부파일 에러/엣지 케이스

| ID | 파일 | Handler | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-EDGE-001 | `edge_cases/empty.txt` | TextHandler | 성공 | 첨부한 텍스트 파일 내용을 요약해줘. | 빈 파일이라 요약할 내용이 없음을 안전하게 안내 |
| ATTACH-EDGE-002 | `edge_cases/large_context_limit.txt` | TextHandler | 성공 | 첨부한 큰 텍스트 파일의 앞부분 기준으로 핵심 내용을 요약해줘. | 앞부분 더미 텍스트를 요약하고 본문 끝부분이 잘렸음을 안내 |
| ATTACH-EDGE-003 | `edge_cases/malformed.json` | TextHandler | 성공 | 첨부한 JSON 파일을 읽고 주요 내용을 요약해줘. | 잘못된 JSON 구조와 파싱 실패 가능성을 안전하게 안내 |
| ATTACH-EDGE-004 | `edge_cases/invalid.yaml` | TextHandler | 이슈 발견 | 첨부한 YAML 파일을 읽고 주요 내용을 요약해줘. | YAML 오류 내용은 안내했으나 마크다운 목록/들여쓰기와 코드블록 렌더링이 여러 조각으로 깨짐 |
| ATTACH-EDGE-005 | `edge_cases/empty_rows.csv` | CsvHandler | 성공 | 첨부한 CSV 파일의 컬럼명과 데이터 행을 요약해줘. | 컬럼명 5개와 데이터 행 없음 상태를 안내 |
| ATTACH-EDGE-006 | `edge_cases/corrupted.png` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 손상 이미지 전송 시 원시 API 오류 대신 이미지 파일을 읽을 수 없다는 사용자용 메시지 표시 확인 |
| ATTACH-EDGE-007 | `edge_cases/empty.pdf` | PdfHandler | 성공 | 첨부한 PDF 내용을 요약해줘. | `pypdf` 누락 안내 없이 추출 가능한 텍스트가 없음을 안전하게 안내. 동일 답변 반복은 응답 안정성 항목에서 별도 처리 |
| ATTACH-EDGE-008 | `edge_cases/empty.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서 내용을 요약해줘. | 추출 가능한 문서 텍스트가 없음을 안전하게 안내 |
| ATTACH-EDGE-009 | `edge_cases/empty_sheet.xlsx` | XlsxHandler | 성공 | 첨부한 XLSX 파일의 시트 내용을 요약해줘. | 빈 시트를 읽고 분석 가능 데이터가 없음을 안내하는 것을 확인. 동일 문구 반복 출력은 응답 안정성 항목에서 별도 처리 |
| ATTACH-EDGE-010 | `edge_cases/empty.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드 내용을 요약해줘. | 전체 슬라이드 1개와 텍스트 없음 상태를 안전하게 안내 |
| ATTACH-EDGE-011 | `edge_cases/unsupported.exe` | Unsupported | 성공 | 첨부한 파일 내용을 확인해줘. | 드래그 중에는 오류 메시지를 만들지 않고, 드롭 완료 시점에 미지원 형식 오류를 1회만 표시함 |
| ATTACH-EDGE-012 | `edge_cases/unsupported.zip` | Unsupported | 성공 | 첨부한 파일 내용을 확인해줘. | 드래그 중에는 오류 메시지를 만들지 않고, 드롭 완료 시점에 미지원 형식 오류를 1회만 표시함 |

## 응답 품질 정상 케이스

| ID | 영역 | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- |
| RESPONSE-NORMAL-001 | 일반 대화 | 성공 | 안녕 | 코드블록 없이 일반 문장으로 짧은 인사 응답 표시 확인 |
| RESPONSE-NORMAL-002 | 일반 요약 | 성공 | 이 내용 요약해줘 | 코드블록 없이 일반 문장으로 요약 응답 표시 확인 |
| RESPONSE-NORMAL-003 | 네이밍 | 성공 | 자바 덧셈 변수명 3개만 추천해줘봐 | 빈 응답 실패 없이 Java 관례에 맞는 `camelCase` 후보 3개가 후보별 복사 블록으로 표시됨 |
| RESPONSE-NORMAL-004 | 네이밍 | 성공 | 자바 사용자 프로필 클래스명 3개 추천해줘 | `PascalCase` 클래스명 후보 3개가 후보별 복사 블록으로 표시됨 |
| RESPONSE-NORMAL-005 | 짧은 단어 번역 | 성공 | 단어 사과 영어로 뭐야? | 짧은 단어 번역 결과가 복사 가능한 단일 블록으로 표시됨 |
| RESPONSE-NORMAL-006 | 문장 번역 | 성공 | 처음 뵙겠습니다 영어로 번역해줘 | 새 세션에서 `Nice to meet you.` 일반 문장 응답 확인. 같은 세션 연속 테스트 중 빈 응답 오류가 1회 발생해 세션/입력 용량 안정화는 로드맵에서 별도 추적 |
| RESPONSE-NORMAL-007 | 짧은 단어 번역 코드펜스 보정 | 성공 | 토끼 영어로 | 모델이 `text` 코드펜스나 `English:` 라벨을 포함해도 UI에는 실제 번역어만 단일 복사 블록으로 표시됨 |
| RESPONSE-NORMAL-008 | 코드 생성 | 성공 | 파이썬 코드 줘 리스트 중복 제거 | Python 함수 코드가 단일 복사 블록으로 표시되고 들여쓰기 유지 확인 |
| RESPONSE-NORMAL-009 | 코드 생성 | 성공 | 자바 코드 줘 사용자 클래스 | Java 클래스 코드가 단일 복사 블록으로 표시되고 줄바꿈/들여쓰기 유지 확인 |
| RESPONSE-NORMAL-010 | 코드 생성 | 성공 | HTML 코드 줘 로그인 폼 | HTML 문서 코드가 단일 복사 블록으로 표시되고 태그 줄바꿈/들여쓰기 유지 확인 |
| RESPONSE-NORMAL-011 | 코드 생성 | 성공 | CSS 코드 줘 버튼 스타일 | CSS 버튼 스타일 코드가 단일 복사 블록으로 표시되고 줄바꿈/들여쓰기 유지 확인 |
| RESPONSE-NORMAL-012 | 코드 생성 | 성공 | C언어 코드 줘 hello world | C hello world 코드가 단일 복사 블록으로 표시되고 줄바꿈/들여쓰기 유지 확인 |
| RESPONSE-NORMAL-013 | SQL 생성 | 성공 | 활성 사용자 조회 SQL문 줘 | SQL 조회문이 복사 가능한 블록으로 표시됨 |
| RESPONSE-NORMAL-014 | 명령어 | 성공 | 터미널에서 현재 폴더 파일 목록 보는 명령어 알려줘 | `bash` 문자열 오분리 없이 실제 명령어 `ls`, `ls -a`가 후보별 복사 블록으로 표시됨 |

## 응답 품질 에러/엣지 케이스

| ID | 영역 | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- |
| RESPONSE-EDGE-001 | Thinking 모델 | 성공 | 자바 곱셈 변수명 3개만 추천해줘봐 | 같은 세션에서 빈 응답 오류 없이 Java 변수명 후보 3개가 복사 블록으로 표시됨 |
| RESPONSE-EDGE-002 | 코드블록 과잉 방지 | 성공 | 이미지 첨부 후 분석해줘 | 이미지 분석 응답이 불필요한 코드블록 없이 일반 분석 문장/목록으로 표시됨. 중첩 목록 들여쓰기 가독성은 로드맵에서 별도 추적 |
| RESPONSE-EDGE-003 | 코드 생성 모델 선택 | 성공 | 자바 코드 줘 사용자 클래스 | 사용자 클래스 Java 코드가 충분한 필드/생성자/메서드를 포함한 단일 복사 블록으로 표시됨 |
| RESPONSE-EDGE-004 | 첨부 요약 포맷 | 성공 | CSV 첨부 후 컬럼명과 샘플 행을 요약해줘 | CSV 컬럼명과 샘플 행이 과도한 복사 카드 없이 일반 요약 문장/목록으로 표시됨 |
| RESPONSE-EDGE-005 | Markdown 렌더링 순서 | 성공 | 설명, 코드, 주의점이 함께 있는 응답 생성 | 설명-코드블록-주의점 순서로 렌더링되고 Python 코드가 복사 가능한 코드블록으로 표시됨 |
| RESPONSE-EDGE-006 | 실제 빈 모델 응답 | 성공 | 나눗셈 후 나머지에 쓸 짧은 변수명 3개만 추천해줘 | 새 세션에서 빈 응답 오류 없이 후보별 복사 블록으로 정상 표시됨. 같은 세션에서는 직전 Markdown 테스트 맥락이 섞여 부적절한 후보가 나와 세션 맥락 오염 방지는 로드맵에서 별도 추적 |

## 채팅 기록 정상/엣지 케이스

| ID | 영역 | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- |
| CHAT-HISTORY-001 | 저장 스위치 | 성공 | 대화 기록 저장 스위치를 켠 뒤 메시지 전송 | 첫 사용자 메시지 기반 제목으로 채팅 기록 목록에 세션이 생성되는지 확인 |
| CHAT-HISTORY-002 | 임시 대화 폐기 | 성공 | 저장 스위치를 끄고 메시지 전송 후 메뉴바 아이콘 재클릭 | 창을 다시 열었을 때 이전 임시 대화가 사라지고 새 대화로 시작하는지 확인 |
| CHAT-HISTORY-003 | 대화 이어가기 | 성공 | 저장된 기록 항목 클릭 후 추가 메시지 전송 | 이전 메시지가 렌더링되고 같은 세션에 새 메시지가 이어서 저장되는지 확인 |
| CHAT-HISTORY-004 | 기록 삭제 | 성공 | 채팅 기록 목록에서 `x` 클릭 | 해당 세션이 목록에서 제거되고 다시 열리지 않는지 확인 |
| CHAT-HISTORY-005 | 기록 재정렬 | 성공 | 채팅 기록 목록 좌측 핸들 드래그 | 드래그한 순서가 목록을 닫았다 다시 열어도 유지되는지 확인 |
| CHAT-HISTORY-006 | 닫기 후 새 대화 | 성공 | 저장된 기록을 열어 확인한 뒤 메뉴바 아이콘 재클릭 | 창을 다시 열었을 때 이전 세션이 이어지지 않고 빈 새 대화로 시작하는지 확인 |

## 향후 기능 테스트 작성 규칙

새 기능 테스트는 기능 영역별 섹션을 추가하고, 첨부 테스트는 `ID`, `파일`, `Handler`, `테스트 상태`, `테스트 프롬프트`, `확인 내용` 형식을 유지한다. 첨부 없는 응답 품질 테스트는 `ID`, `영역`, `테스트 상태`, `테스트 프롬프트`, `확인 내용` 형식을 사용한다. 실제 샘플 파일이 있는 테스트는 파일 1개당 테스트 1개로 기록한다.

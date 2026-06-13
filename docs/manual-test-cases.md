# 수동 테스트 케이스

이 문서는 사용자가 직접 수행할 테스트 목록이다. AI가 수행한 테스트 결과를 기록하는 문서가 아니며, 기능별 구현 상태를 확인하고 이후 디버깅과 오류 수정을 추적하기 위한 기준 목록으로 사용한다.

테스트 상태는 `미실행`, `성공`, `실패`, `이슈 발견` 중 하나를 우선 사용한다. 첨부 handler 자체 문제가 아닌 응답 중복, 스트리밍, 메시지 렌더링 문제는 [attachment-test-fixes.md](attachment-test-fixes.md)에 별도 기록한다.

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
| ATTACH-NORMAL-010 | `normal/sample.jpeg` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 새 세션에서 이미지 라벨 `sample.jpeg - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-011 | `normal/sample.gif` | ImageHandler | 이슈 발견 | 첨부한 이미지 분석해서 어떤건지 요약해줘. | GIF 이미지 라벨과 테스트 목적은 인식했으나, 요청하지 않은 코드 예시와 분리된 코드블록이 함께 출력됨 |
| ATTACH-NORMAL-012 | `normal/sample.bmp` | ImageHandler | 성공 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 이미지 라벨 `sample.bmp - ImageHandler test` 인식 확인 |
| ATTACH-NORMAL-013 | `normal/sample.pdf` | PdfHandler | 이슈 발견 | 첨부한 PDF의 페이지별 핵심 내용을 요약해줘. | 앱 런타임에서 `pypdf`가 없어 fallback 추출로 처리되고, 실제 텍스트 PDF를 스캔 PDF처럼 안내함 |
| ATTACH-NORMAL-014 | `normal/sample.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서의 제목, 문단, 표 내용을 요약해줘. | 제목, 문단, 마지막 문단, 표 텍스트 인식 확인 |
| ATTACH-NORMAL-015 | `normal/sample.xlsx` | XlsxHandler | 이슈 발견 | 첨부한 XLSX 파일의 시트별 컬럼과 샘플 데이터를 요약해줘. | "XLSX 파일을 읽을 수 없어요: sample.xlsx" 오류 발생. sheet target 경로가 `/xl/...`일 때 handler가 `xl/`을 중복으로 붙이는 구현 문제 가능성 |
| ATTACH-NORMAL-016 | `normal/sample.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드별 텍스트를 요약해줘. | 3개 슬라이드의 제목/본문 텍스트 인식 확인 |

## 첨부파일 에러/엣지 케이스

| ID | 파일 | Handler | 테스트 상태 | 테스트 프롬프트 | 확인 내용 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-EDGE-001 | `edge_cases/empty.txt` | TextHandler | 성공 | 첨부한 텍스트 파일 내용을 요약해줘. | 빈 파일이라 요약할 내용이 없음을 안전하게 안내 |
| ATTACH-EDGE-002 | `edge_cases/large_context_limit.txt` | TextHandler | 성공 | 첨부한 큰 텍스트 파일의 앞부분 기준으로 핵심 내용을 요약해줘. | 앞부분 더미 텍스트를 요약하고 본문 끝부분이 잘렸음을 안내 |
| ATTACH-EDGE-003 | `edge_cases/malformed.json` | TextHandler | 성공 | 첨부한 JSON 파일을 읽고 주요 내용을 요약해줘. | 잘못된 JSON 구조와 파싱 실패 가능성을 안전하게 안내 |
| ATTACH-EDGE-004 | `edge_cases/invalid.yaml` | TextHandler | 이슈 발견 | 첨부한 YAML 파일을 읽고 주요 내용을 요약해줘. | YAML 오류 내용은 안내했으나 마크다운 목록/들여쓰기와 코드블록 렌더링이 여러 조각으로 깨짐 |
| ATTACH-EDGE-005 | `edge_cases/empty_rows.csv` | CsvHandler | 성공 | 첨부한 CSV 파일의 컬럼명과 데이터 행을 요약해줘. | 컬럼명 5개와 데이터 행 없음 상태를 안내 |
| ATTACH-EDGE-006 | `edge_cases/corrupted.png` | ImageHandler | 이슈 발견 | 첨부한 이미지에 적힌 텍스트를 읽어줘. | 손상 이미지 전송 시 400 `Failed to load image or audio file` 원시 API 오류가 노출됨 |
| ATTACH-EDGE-007 | `edge_cases/empty.pdf` | PdfHandler | 성공 | 첨부한 PDF 내용을 요약해줘. | 추출 가능한 텍스트가 없음을 안전하게 안내 |
| ATTACH-EDGE-008 | `edge_cases/empty.docx` | DocxHandler | 성공 | 첨부한 DOCX 문서 내용을 요약해줘. | 추출 가능한 문서 텍스트가 없음을 안전하게 안내 |
| ATTACH-EDGE-009 | `edge_cases/empty_sheet.xlsx` | XlsxHandler | 이슈 발견 | 첨부한 XLSX 파일의 시트 내용을 요약해줘. | 정상 XLSX와 동일하게 "XLSX 파일을 읽을 수 없어요" 오류 발생. `ATTACH-FIX-006` 경로 파싱 이슈 범위 |
| ATTACH-EDGE-010 | `edge_cases/empty.pptx` | PptxHandler | 성공 | 첨부한 PPTX 파일의 슬라이드 내용을 요약해줘. | 전체 슬라이드 1개와 텍스트 없음 상태를 안전하게 안내 |
| ATTACH-EDGE-011 | `edge_cases/unsupported.exe` | Unsupported | 이슈 발견 | 첨부한 파일 내용을 확인해줘. | 파일을 정확히 드롭하지 않았는데 드래그 중 미지원 형식 오류 채팅이 20회 이상 반복 생성됨 |
| ATTACH-EDGE-012 | `edge_cases/unsupported.zip` | Unsupported | 이슈 발견 | 첨부한 파일 내용을 확인해줘. | `unsupported.exe`와 동일하게 드래그 중 미지원 형식 오류 채팅이 반복 생성됨 |

## 향후 기능 테스트 작성 규칙

새 기능 테스트는 기능 영역별 섹션을 추가하고, `ID`, `파일`, `Handler`, `테스트 상태`, `테스트 프롬프트`, `확인 내용` 형식을 유지한다. 실제 샘플 파일이 있는 테스트는 파일 1개당 테스트 1개로 기록한다.

# 첨부파일 테스트 수정 사항

이 문서는 첨부파일 수동 테스트 중 발견한 문제와 예상 오류 범위를 함께 기록한다. 첨부 handler 자체 문제, 응답 생성, 스트리밍, 메시지 렌더링 문제를 한곳에서 추적하되 `영역`으로 구분한다.

## 발견한 문제

| ID | 영역 | 관련 테스트 | 증상 | 기대 동작 | 상태 |
| --- | --- | --- | --- | --- | --- |
| ATTACH-FIX-001 | 응답 출력 | ATTACH-NORMAL-001 | `sample.txt` 첨부 응답이 동일 내용으로 2회 중복 출력됨 | 최종 응답은 1회만 출력되어야 함 | 미수정 |
| ATTACH-FIX-002 | 응답 상태 | ATTACH-NORMAL-006 | `sample.csv` 첨부 후 응답이 CSV 요약이 아니라 무관한 문장과 `id`만 담긴 부분 코드블록처럼 표시됨. 후속 질문에서도 "커널이 첨부된 데이터를 직접 읽지 못했다"고 답하며 컬럼 리스트와 `id` 주변 출력이 깨짐 | CSV 컬럼명과 샘플 행 요약이 하나의 Assistant 응답으로 정상 렌더링되어야 하며, 실패 시 실제 실패 지점을 명확히 안내해야 함 | 미수정 |
| ATTACH-FIX-003 | context 한도 | ATTACH-NORMAL-010 | `sample.jpeg` 첨부 요청에서 `request (4921 tokens) exceeds the available context size (4096 tokens)` 원시 API 오류가 노출됨 | 원시 오류 대신 메시지 버블에 "대화가 길어져 응답 용량이 초과되었습니다. 새로운 대화를 시작해주세요."처럼 사용자가 이해할 수 있는 안내를 표시해야 함. 이후 히스토리 축약 또는 첨부 context 제한도 검토 필요 | 미수정 |
| ATTACH-FIX-004 | 응답 포맷 | ATTACH-NORMAL-011 | `sample.gif` 분석 응답에서 요청하지 않은 코드 예시가 생성되고, `sample.gif` 단독 코드블록과 Python 코드블록이 분리되어 표시됨 | 이미지 설명 요청에는 이미지 요약만 답하고, 사용자가 요청하지 않은 코드 예시는 생성하지 않아야 함 | 미수정 |
| ATTACH-FIX-005 | PDF 의존성/추출 | ATTACH-NORMAL-013 | `sample.pdf`는 5페이지 텍스트 PDF이지만 앱 런타임에 `pypdf`가 없어 fallback 추출로 내려가고, 결과적으로 "스캔된 이미지 기반 PDF"처럼 잘못 안내함 | 런타임/패키징에 `pypdf`를 포함하고, 의존성 누락과 실제 텍스트 없음/OCR 미지원 상황을 구분해 안내해야 함 | 미수정 |
| ATTACH-FIX-006 | XLSX 경로 파싱 | ATTACH-NORMAL-015 | `sample.xlsx`에서 "XLSX 파일을 읽을 수 없어요: sample.xlsx" 오류 발생. workbook relationship target이 `/xl/worksheets/sheet1.xml`인데 `XlsxHandler`가 `xl/`을 중복으로 붙여 존재하지 않는 경로를 읽으려 함 | relationship target이 `/xl/...`, `worksheets/...`, `../...` 등 어떤 형태여도 zip 내부 실제 경로로 정규화해야 함 | 미수정 |

## 예상 오류 범위

| 범위 | 관련 테스트 | 예상 동작 |
| --- | --- | --- |
| 빈 텍스트 파일 | ATTACH-EDGE-001 | 첨부는 허용하되 읽을 내용이 없음을 안내 |
| 큰 텍스트 파일 | ATTACH-EDGE-002 | 일부 내용만 context로 전달하고 길이 제한 또는 일부 추출 사실을 안내 |
| 깨진 구조화 텍스트 | ATTACH-EDGE-003, ATTACH-EDGE-004 | JSON/YAML 파싱 실패를 앱 오류로 터뜨리지 않고 사용자에게 읽기 실패를 안내 |
| 데이터 행 없는 CSV | ATTACH-EDGE-005 | 컬럼명은 인식하고 데이터 행이 없음을 안내 |
| 손상된 이미지 | ATTACH-EDGE-006 | 이미지 디코딩 실패를 안전하게 처리하고 사용자에게 오류를 안내 |
| context 한도 초과 | ATTACH-NORMAL-010, ATTACH-EDGE-002 | 요청 생성 전 토큰 예산을 확인하고, 초과 시 원시 API 오류 대신 메시지 버블에 새 대화 시작 안내를 표시 |
| PDF 추출 의존성 누락 | ATTACH-NORMAL-013 | `pypdf` 누락 시 스캔 PDF로 오진하지 않고 PDF 추출 라이브러리 누락 또는 제한적 추출 상태를 구분해 안내 |
| XLSX relationship 경로 차이 | ATTACH-NORMAL-015, ATTACH-EDGE-009 | workbook relationship target을 표준 OOXML 경로 규칙에 맞게 정규화하고, 실패 시 어떤 sheet 경로를 읽지 못했는지 내부 로그로 확인 가능해야 함 |
| 텍스트 없는 문서 | ATTACH-EDGE-007, ATTACH-EDGE-008, ATTACH-EDGE-010 | 파일은 열리지만 추출 가능한 텍스트가 없음을 안내 |
| 빈 스프레드시트 | ATTACH-EDGE-009 | 시트는 인식하되 분석할 데이터가 없음을 안내 |
| 미지원 확장자 | ATTACH-EDGE-011, ATTACH-EDGE-012 | 첨부 선택 또는 전송 시 지원하지 않는 파일 형식 오류를 표시 |

## 완료

아직 완료된 수정 사항 없음.

# Attachment Test Sample Files

첨부파일 핸들러(`ImageHandler`, `TextHandler`, `CsvHandler`, `PdfHandler`, `DocxHandler`, `XlsxHandler`, `PptxHandler`) 동작 및 에러처리 테스트용 샘플 파일 목록입니다.

## normal/ - 정상 동작 확인용

| 파일 | 대상 핸들러 | 내용 | 확인 목적 |
|------|------------|------|-----------|
| sample.txt | TextHandler | 한글/영어 혼합 4줄 텍스트 | 텍스트 본문 일부 context 추출 |
| sample.md | TextHandler | 제목, 목록, 코드블록, 표가 포함된 마크다운 | 마크다운 구조 포함 텍스트 추출 |
| sample.json | TextHandler | 상품 목록(items 배열) + meta 정보를 담은 JSON | 정상 JSON 파싱/본문 추출 |
| sample.yaml / sample.yml | TextHandler | sample.json과 동일한 구조의 YAML | YAML 파싱/본문 추출, yaml·yml 확장자 둘 다 처리되는지 |
| sample.csv | CsvHandler | id/name/category/price/stock 컬럼, 상품 8행 | 컬럼명 + 샘플 행 추출 |
| sample.tsv | CsvHandler | sample.csv와 동일 데이터, 탭 구분 | TSV 구분자(tab) 처리 확인 |
| sample.png | ImageHandler | "sample.png - ImageHandler test" 텍스트가 박힌 400x300 이미지 | PNG → base64 → Ollama images 필드 전달 |
| sample.jpg / sample.jpeg | ImageHandler | 위와 동일 형식의 JPEG 이미지(라벨만 다름) | JPEG 인코딩, jpg·jpeg 확장자 둘 다 처리되는지 |
| sample.gif | ImageHandler | 위와 동일 형식의 GIF 이미지 | GIF 인코딩 처리 확인 |
| sample.bmp | ImageHandler | 위와 동일 형식의 BMP 이미지 | BMP 인코딩(상대적으로 큰 파일) 처리 확인 |
| sample.pdf | PdfHandler | A4, 5페이지, 페이지별로 다른 한글 문장(Page 1~5) | 일부 페이지 텍스트만 추출되는지 |
| sample.docx | DocxHandler | 제목(Heading1) + 본문 2문단 + 표(3행x3열, 헤더 포함) + 마지막 문단 | 문단 텍스트 + 표 텍스트 함께 추출되는지 |
| sample.xlsx | XlsxHandler | 시트1 "재고"(id/상품명/카테고리/가격/재고수량, 8행), 시트2 "매출"(월별 매출/비용/순이익, 3행) | 여러 시트의 시트명/컬럼명/샘플 행 추출 |
| sample.pptx | PptxHandler | 3개 슬라이드, 각각 제목+본문(한글/영어 혼합) | 슬라이드별 텍스트 분리 추출 |

## edge_cases/ - 에러처리 및 제약 확인용

| 파일 | 대상 핸들러 | 내용 | 확인 목적 |
|------|------------|------|-----------|
| empty.txt | TextHandler | 빈 파일(0 byte) | 내용 없는 파일 처리 시 에러/빈 context 처리 |
| large_context_limit.txt | TextHandler | 약 2MB, 2만 줄의 더미 한글/영어 텍스트 | context 길이 제한 초과 시 잘림/처리 동작 확인 |
| malformed.json | TextHandler | trailing comma, 닫히지 않은 키 등 문법 오류가 있는 JSON | JSON 파싱 실패 시 에러처리 |
| invalid.yaml | TextHandler | 들여쓰기 불일치 및 잘못된 key:value 구조 | YAML 파싱 실패 시 에러처리 |
| empty_rows.csv | CsvHandler | 헤더(id/name/category/price/stock)만 있고 데이터 행 없음 | 샘플 행이 없을 때 처리 동작 확인 |
| corrupted.png | ImageHandler | png 확장자지만 실제로는 일반 텍스트 바이트 | 이미지 디코딩 실패 시 에러처리 |
| empty.pdf | PdfHandler | 빈 페이지 1장(텍스트 없음) | 추출 가능한 텍스트가 없을 때 처리 동작 확인 |
| empty.docx | DocxHandler | 빈 문단 1개만 존재 | 본문 내용이 없을 때 처리 동작 확인 |
| empty_sheet.xlsx | XlsxHandler | 빈 시트 1개(컬럼/데이터 없음) | 컬럼/행이 없는 시트 처리 동작 확인 |
| empty.pptx | PptxHandler | 텍스트가 전혀 없는 빈 레이아웃 슬라이드 1개 | 슬라이드에 텍스트가 없을 때 처리 동작 확인 |
| unsupported.exe | - | "MZ..."로 시작하는 가짜 실행파일 바이너리 | 지원하지 않는 확장자에 대한 거부/에러처리 |
| unsupported.zip | - | "PK..."로 시작하는 가짜 zip 바이너리 | 지원하지 않는 확장자에 대한 거부/에러처리 |

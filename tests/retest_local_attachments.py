import sys,json,time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.llm.chat_service import ChatService
from core.llm.contracts import ChatAttachmentPayload
out = ROOT / 'tests/results/attachment-responses-latest.json'
out.parent.mkdir(parents=True, exist_ok=True)
results=[]
cases=[('CSV','normal/sample.csv','첨부한 CSV 파일의 컬럼명과 샘플 행을 요약해줘.','첨부 데이터에서 사과의 가격과 재고가 얼마인지 알려줘.'),('GIF','normal/sample.gif','첨부한 이미지 분석해서 어떤건지 요약해줘.','방금 이미지에 실제로 보이는 글자를 알려줘. 코드는 쓰지 마.'),('YAML','edge_cases/invalid.yaml','첨부한 YAML 파일을 읽고 주요 내용을 요약해줘.','방금 파일에서 문법이 잘못된 부분을 설명해줘. 수정 코드는 필요 없어.')]
for label,file,prompt,followup in cases:
    service=ChatService()
    for stage,text,attachments in [('initial',prompt,(ChatAttachmentPayload.from_path(ROOT/'attachment_test'/file),)),('followup',followup,())]:
        start=time.monotonic()
        try:
            answer=''.join(service.send(text,attachments))
            row=dict(case=label,stage=stage,prompt=text,answer=answer,seconds=round(time.monotonic()-start,2),intent=service.history[-1].metadata.get('intent'))
        except Exception as e:
            row=dict(case=label,stage=stage,error=f'{type(e).__name__}: {e}',seconds=round(time.monotonic()-start,2))
        results.append(row);out.write_text(json.dumps(results,ensure_ascii=False,indent=2))
        print(json.dumps(row,ensure_ascii=False),flush=True)

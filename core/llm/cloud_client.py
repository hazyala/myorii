"""Native provider APIs using HTTPS; no keys or provider response bodies in errors."""
import base64
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from PyQt6.QtGui import QImage
from PyQt6.QtCore import QBuffer, QByteArray, QIODevice
from storage.model_store import get_key

class CloudAPIError(RuntimeError): pass

class CloudClient:
    def __init__(self, provider, key=None):
        self.provider=provider
        self._key=key

    def _headers(self):
        key=self._key if self._key is not None else get_key(self.provider)
        if not key: raise CloudAPIError('API 키를 모델 관리에서 등록해주세요. / Add an API key in model settings.')
        if self.provider=='openai': return {'Authorization':'Bearer '+key,'Content-Type':'application/json'}
        if self.provider=='anthropic': return {'x-api-key':key,'anthropic-version':'2023-06-01','Content-Type':'application/json'}
        return {'x-goog-api-key':key,'Content-Type':'application/json'}

    def _request(self,url,payload=None):
        request=Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers=self._headers())
        try: return urlopen(request,timeout=90)
        except HTTPError as exc:
            messages={400:'요청 형식 또는 모델의 이미지 지원 여부를 확인해주세요.',401:'API 키가 올바르지 않습니다.',403:'이 모델을 사용할 권한이 없습니다.',404:'모델 이름을 확인해주세요.',429:'API 사용 한도 또는 잔액을 확인해주세요.'}
            raise CloudAPIError(f'{self.provider}: '+messages.get(exc.code,f'API 오류 ({exc.code})')) from None
        except (URLError,TimeoutError,OSError): raise CloudAPIError('API에 연결할 수 없습니다. 인터넷 연결을 확인해주세요.') from None

    @staticmethod
    def _chat_model(provider,model):
        name=model.get('id',model.get('name','')).removeprefix('models/')
        if provider=='anthropic':return name.startswith('claude-')
        if provider=='gemini':
            return ('generateContent' in model.get('supportedGenerationMethods',[]) and name.startswith('gemini-')
                    and not any(part in name for part in ('image','tts','audio','robotics','computer-use')))
        # The Models endpoint has no modality metadata. Exclude specialized
        # image/audio/tool models that our text Responses stream cannot display.
        base=name.split(':')[1] if name.startswith('ft:') else name
        return (base.startswith(('gpt-','o1','o3','o4'))
                and not any(part in base for part in ('image','audio','realtime','transcribe','tts','search','deep-research','codex'))
                and not base.startswith(('gpt-3.5','gpt-4-turbo')) and base not in ('gpt-4','o1-mini','o1-preview'))

    def list_models(self):
        urls={'openai':'https://api.openai.com/v1/models','anthropic':'https://api.anthropic.com/v1/models?limit=100','gemini':'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000'}
        url=urls[self.provider];models=set();seen=set()
        while url and url not in seen:
            seen.add(url)
            with self._request(url) as response:data=json.load(response)
            rows=data.get('models',[]) if self.provider=='gemini' else data.get('data',[])
            models.update(m.get('id',m.get('name','')).removeprefix('models/') for m in rows if self._chat_model(self.provider,m))
            url=None
            if self.provider=='gemini' and data.get('nextPageToken'):
                url=urls[self.provider]+'&pageToken='+quote(data['nextPageToken'],safe='')
            elif self.provider=='anthropic' and data.get('has_more') and data.get('last_id'):
                url=urls[self.provider]+'&after_id='+quote(data['last_id'],safe='')
        return sorted(models)

    @staticmethod
    def _images(message):
        images=[]
        for attachment in message.attachments:
            if not attachment.is_image: continue
            # Normalize GIF/BMP and other images to a provider-supported PNG.
            image=QImage(attachment.path)
            if image.isNull(): raise CloudAPIError('이미지를 읽을 수 없습니다. / Cannot read image.')
            data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image.save(buffer,'PNG');buffer.close()
            images.append(base64.b64encode(bytes(data)).decode())
        return images

    def build_request(self,model,messages):
        if not model: raise CloudAPIError('사용할 API 모델을 선택해주세요. / Select an API model.')
        system='\n\n'.join(m.content for m in messages if m.role=='system')
        turns=[m for m in messages if m.role!='system']
        if self.provider=='openai':
            items=[]
            for m in turns:
                parts=[{'type':'input_text' if m.role=='user' else 'output_text','text':m.content}]
                parts.extend({'type':'input_image','image_url':'data:image/png;base64,'+image} for image in self._images(m))
                items.append({'role':m.role,'content':parts})
            return 'https://api.openai.com/v1/responses',{'model':model,'instructions':system,'input':items,'stream':True,'store':False}
        if self.provider=='anthropic':
            items=[]
            for m in turns:
                parts=[{'type':'text','text':m.content or '첨부 이미지'}]
                parts.extend({'type':'image','source':{'type':'base64','media_type':'image/png','data':image}} for image in self._images(m))
                items.append({'role':m.role,'content':parts})
            return 'https://api.anthropic.com/v1/messages',{'model':model,'system':system,'messages':items,'max_tokens':4096,'stream':True}
        contents=[]
        for m in turns:
            parts=[{'text':m.content}]
            parts.extend({'inlineData':{'mimeType':'image/png','data':image}} for image in self._images(m))
            contents.append({'role':'model' if m.role=='assistant' else 'user','parts':parts})
        payload={'contents':contents}
        if system: payload['systemInstruction']={'parts':[{'text':system}]}
        return 'https://generativelanguage.googleapis.com/v1beta/models/'+quote(model.removeprefix('models/'),safe='')+':streamGenerateContent?alt=sse',payload

    def stream_chat(self,model,messages):
        url,payload=self.build_request(model,messages)
        with self._request(url,payload) as response:
            for raw in response:
                line=raw.decode('utf-8').strip()
                if not line.startswith('data:'): continue
                content=line[5:].strip()
                if content=='[DONE]': break
                try: event=json.loads(content)
                except ValueError: raise CloudAPIError('API 응답 형식을 읽을 수 없습니다.') from None
                if 'error' in event or event.get('type') in ('error','response.failed','response.incomplete'):
                    raise CloudAPIError('API 응답이 중단되었습니다. 모델과 사용 한도를 확인해주세요.')
                if self.provider=='openai':
                    if event.get('type')=='response.output_text.delta': yield event.get('delta','')
                elif self.provider=='anthropic':
                    if event.get('delta',{}).get('type')=='text_delta': yield event['delta'].get('text','')
                else:
                    for candidate in event.get('candidates',[]):
                        for part in candidate.get('content',{}).get('parts',[]):
                            if not part.get('thought'): yield part.get('text','')

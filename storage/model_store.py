"""Model choices in SQLite; credentials in macOS Keychain only."""
import json
from storage.database import get_connection

PROVIDERS = ('ollama','openai','gemini','anthropic')

def load():
    result = {'provider':'ollama','models':{'ollama':'qwen3-vl:4b-instruct','openai':'','gemini':'','anthropic':''}}
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM preferences WHERE key='models'").fetchone()
    if row:
        try:
            saved = json.loads(row['value'])
            if saved.get('provider') in PROVIDERS: result['provider']=saved['provider']
            for provider, model in saved.get('models',{}).items():
                if provider in PROVIDERS and isinstance(model,str): result['models'][provider]=model
        except (ValueError, TypeError, AttributeError): pass
    return result

def save(config):
    if config['provider'] not in PROVIDERS: raise ValueError('Invalid provider')
    config = {"provider": config["provider"], "models": {provider: str(config["models"].get(provider,"")) for provider in PROVIDERS}}
    with get_connection() as conn:
        conn.execute("INSERT INTO preferences(key,value) VALUES('models',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(config),))

def get_key(provider):
    from keyring.backends.macOS import Keyring
    return Keyring().get_password('Myorii API',provider) or ''

def set_key(provider,key):
    from keyring.backends.macOS import Keyring
    backend=Keyring()
    if key: backend.set_password('Myorii API',provider,key)
    elif backend.get_password('Myorii API',provider): backend.delete_password('Myorii API',provider)

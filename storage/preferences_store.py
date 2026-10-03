"""Persistent, validated UI preferences in the existing local database."""
from storage.database import get_connection

DEFAULTS = {"theme": "light", "language": "ko"}
CHOICES = {"theme": {"light", "dark"}, "language": {"ko", "en"}}

def load() -> dict[str, str]:
    result = dict(DEFAULTS)
    with get_connection() as conn:
        for row in conn.execute("SELECT key, value FROM preferences"):
            if row['key'] in CHOICES and row['value'] in CHOICES[row['key']]:
                result[row['key']] = row['value']
    return result

def save(key: str, value: str) -> None:
    if key not in CHOICES or value not in CHOICES[key]:
        raise ValueError('Invalid UI preference')
    with get_connection() as conn:
        conn.execute('INSERT INTO preferences (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))

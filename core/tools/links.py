"""Stable local memo references for Markdown chat transcripts."""
import re


def memo_reference(memo_id: int, title: str) -> str:
    label = title.strip().replace('\n', ' ') or '제목 없는 메모'
    label = re.sub(r'([\\\[\]`*_<>])', r'\\\1', label)
    return f'[{label}](myorii://memo/{memo_id})'

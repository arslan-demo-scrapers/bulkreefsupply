import re
from html import unescape


def clean(text):
    if not text:
        return ''
    text = unescape(text or '')

    if text and isinstance(text, str):
        for c in ['\r\n', '\n\r', u'\n', u'\r', u'\t', u'\xa0']:
            text = text.replace(c, ' ')
        return re.sub(' +', ' ', text).strip()

    return text

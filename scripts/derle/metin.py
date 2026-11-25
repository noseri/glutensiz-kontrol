# -*- coding: utf-8 -*-
"""Metin yardımcıları: Türkçe küçük harf, aksansız karşılaştırma anahtarı, kök."""
import re
import unicodedata


# ---------------------------------------------------------------- metin ----
_TR_UP = {'I': 'ı', 'İ': 'i'}
_FOLD = str.maketrans({'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u',
                       'â': 'a', 'î': 'i', 'û': 'u', 'ª': 's'})
_APOS = "’'`´‘ʼ"
_SUFFIX_AFTER_APOS = re.compile(
    "[" + _APOS + "](?:nın|nin|nun|nün|ın|in|un|ün|ı|i|u|ü|a|e|da|de|ta|te|dan|den|tan|ten|yla|yle|la|le)\\b")


def clean(s):
    """Görünen metni sadeleştir (boşluk, görünmez karakter)."""
    s = unicodedata.normalize('NFC', s or '')
    s = s.replace('\u200d', '').replace('\u200b', '').replace('\xa0', ' ').replace('\ufeff', '')
    s = re.sub(r'[ \t\r\f\v]+', ' ', s)
    return s.strip()


def norm(s):
    """Arama/eşleştirme için: Türkçe küçük harf, aksan yok, noktalama yok."""
    s = clean(s)
    s = ''.join(_TR_UP.get(c, c) for c in s).lower()
    s = _SUFFIX_AFTER_APOS.sub('', s)
    s = re.sub('[' + _APOS + ']', '', s)
    s = s.translate(_FOLD)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('&', ' & ')
    s = re.sub(r'[^a-z0-9%&+]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    # "i r m i k" -> "irmik", "a o c" -> "aoc"
    s = re.sub(r'\b(?:[a-z0-9] ){2,}[a-z0-9]\b', lambda m: m.group(0).replace(' ', ''), s)
    return s


def tr_lower(s):
    return ''.join(_TR_UP.get(c, c) for c in s).lower()


def tr_title(w):
    if not w:
        return w
    first = {'i': 'İ', 'ı': 'I'}.get(w[0], w[0].upper())
    return first + tr_lower(w[1:])


def compact(s):
    return norm(s).replace(' ', '')


def fuzzkey(k):
    return re.sub(r'(.)\1+', r'\1', k)


def stem(t):
    for suf in ('lari', 'leri', 'lar', 'ler', 'lik', 'luk', 'li', 'lu', 'si', 'su', 'i', 'u', 'a', 'e'):
        if t.endswith(suf):
            rest = t[:-len(suf)]
            if len(rest) >= 4 or (len(rest) == 3 and suf in ('lari', 'leri', 'lar', 'ler', 'li', 'lu', 'i', 'u')):
                return rest
    return t

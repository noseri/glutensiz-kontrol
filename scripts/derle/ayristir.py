# -*- coding: utf-8 -*-
"""Dernek sayfalarını satırlara ayırma: HTML, İstanbul (gıda, ilaç, kozmetik, takviye) ve Ankara."""
import re

from bs4 import BeautifulSoup

from .metin import clean, compact, norm
from .kategoriler import WARN_RX
from .markalar import detect_brand, find_alias
from .ortak import (
    NOTE_START, camel_split, canon_cat, canon_cat_strict, is_upperish, make_line,
    merge_continuations,
)


# ---------------------------------------------------------------- HTML ----
_BLOCK = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th', 'blockquote', 'pre'}
_SHORTCODE = re.compile(r'\[/?vc_[^\]]*\]')


def html_rows(html):
    """Sayfa içeriğini satırlara çevir: [{'text', 'tag', 'bold'}]"""
    html = _SHORTCODE.sub('', html or '')
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.I)
    soup = BeautifulSoup(html, 'lxml')
    rows = []
    for el in soup.find_all(True):
        if el.name not in _BLOCK:
            continue
        if any(c.name in _BLOCK for c in el.find_all(True)):
            # içinde blok varsa: yalnızca doğrudan metin parçalarını al
            direct = ''.join(str(c) for c in el.children if getattr(c, 'name', None) not in _BLOCK)
            if not clean(BeautifulSoup(direct, 'lxml').get_text()):
                continue
            frag_soup = BeautifulSoup(direct, 'lxml')
        else:
            frag_soup = el
        full = frag_soup.get_text()
        strong = ''.join(s.get_text() for s in frag_soup.find_all(['strong', 'b']))
        letters = len(re.sub(r'\s', '', full)) or 1
        bold = min(1.0, len(re.sub(r'\s', '', strong)) / letters)
        for line in full.split('\n'):
            line = clean(line)
            if line:
                rows.append({'text': line, 'tag': el.name, 'bold': round(bold, 2)})
    return rows

# ---------------------------------------------------- İstanbul: gıda ----
IST_BRAND_HEADINGS = {
    'starbucks': ('Starbucks', None), 'nestle nespresso': ('Nespresso', None),
    'tukas konserveler': ('Tukaş', 'konserve'), 'peyman bahceden': ('Peyman Bahçeden', None),
    'peyman dorleo': ('Peyman Dorleo', None), 'peyman citliyo': ('Peyman Çitliyo', None),
    'saray muhallebicisi': ('Saray Muhallebicisi', None),
    'saray muhallebicisi subeleri': ('Saray Muhallebicisi', None, 'info'),
}
IST_SKIP_HEADINGS = {'dikkat onemli', '', 'kolay menu'}


def inline_subheading(line, domain):
    """Paragraf içindeki ara başlıklar: 'PROFİTEROL :', 'YOGURT', 'HiNDi : (...)'"""
    n = norm(line)
    words = n.split()
    if not words or len(words) > 8:
        return None
    looks = line.rstrip().endswith(':') or re.search(r'\s:\s*\(', line) or is_upperish(line) or \
        (len(words) <= 3 and detect_brand(n)[0] is None) or n in ('raki votka cin',)
    if not looks:
        return None
    cid = canon_cat_strict(line, domain)
    if cid:
        return cid
    return None


def parse_ist_gida(page):
    rows = html_rows(page['content']['rendered'])
    lines, cat, heading, ctx, section = [], None, '', None, 'ok'
    force = False
    for i, r in enumerate(rows):
        t = r['text']
        n = norm(t)
        if r['tag'] in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            nn = re.sub(r'\s+', ' ', n.replace(':', ' ')).strip()
            if nn in IST_SKIP_HEADINGS or not nn:
                section = 'skip' if nn == 'dikkat onemli' else section
                continue
            heading = t
            force = False
            if nn.startswith('mabel firmasinin aciklamasi'):
                section, ctx = 'warn', compact('Mabel')
                continue
            cid = canon_cat(t, 'gida')
            if cid == 'etiket-oku':
                cat, section = 'etiket-oku', 'read'
                ctx = None
                for k, b in (('unilever', 'unilever'), ('kent', 'mondelezkent'), ('nestle', 'nestle')):
                    if k in nn:
                        ctx = b
                continue
            bh = IST_BRAND_HEADINGS.get(nn)
            if bh:
                ctx = compact(bh[0])
                if bh[1]:
                    cat = bh[1]
                force = len(bh) > 2 and bool(bh[2])
                section = 'info' if (len(bh) > 2 and bh[2] == 'info') else 'ok'
                continue
            if cid:
                cat, ctx, section = cid, None, 'ok'
            else:
                # tanınmayan başlık: marka başlığı say
                ctx, section = detect_brand(n)[0], 'ok'
            continue
        if section == 'skip' or cat is None:
            continue
        t2 = re.sub(r'^[·•\-–]\s*', '', t).strip()
        if not t2:
            continue
        sub = inline_subheading(t2, 'gida')
        if sub and section != 'read':
            cat, heading, ctx = sub, t2, None
            continue
        kind = None
        n2 = norm(t2)
        if section == 'warn':
            kind = 'warn' if re.search(r'kodlu|cesit numarasi', n2) else 'note'
        elif section == 'read':
            kind = 'note' if (len(n2.split()) > 8 or NOTE_START.match(n2)) else 'read'
        elif section == 'info':
            kind = 'info'
        lines.append(make_line('ist', 'gida', cat, t2, heading, ctx, kind, i, force))
    return merge_continuations(lines)


def parse_ist_simple(page, domain, default_cat):
    rows = html_rows(page['content']['rendered'])
    lines, cat, heading, ctx, section = [], default_cat, '', None, 'ok'
    started = domain == 'kozmetik'
    for i, r in enumerate(rows):
        t = r['text']
        n = norm(t)
        if r['tag'] in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            nn = n.replace(':', ' ').strip()
            if nn in IST_SKIP_HEADINGS:
                started = False
                continue
            heading = t
            started = True
            if domain == 'kozmetik':
                cid = canon_cat(t, 'kozmetik')
                if cid:
                    cat = cid
                    section = 'read' if cid == 'kozmetik-oku' else 'ok'
            continue
        if not started:
            if domain == 'takviye' and n.startswith('glutensiz tibbi gida destekleri'):
                started, heading = True, t
            continue
        if domain == 'kozmetik':
            cid = canon_cat(t, 'kozmetik') if (r['bold'] > 0.6 or t.rstrip().endswith(':')) else None
            if cid:
                cat, heading = cid, t
                section = 'read' if cid == 'kozmetik-oku' else 'ok'
                continue
            if r['bold'] > 0.6 and len(n.split()) > 4:
                lines.append(make_line('ist', domain, cat, t, heading, None, 'note', i))
                continue
            lines.append(make_line('ist', domain, cat, t, heading, None, 'read' if section == 'read' else None, i))
            continue
        if domain == 'ilac':
            if n.startswith('onemli not') or n.startswith('glutensiz ilaclar'):
                if n.startswith('onemli not'):
                    lines.append(make_line('ist', domain, 'ilac', t, 'Glutensiz İlaçlar', None, 'note', i))
                continue
            cat_i = 'ilac-firma' if is_company_statement(n) else 'ilac'
            lines.append(make_line('ist', domain, cat_i, t, 'Glutensiz İlaçlar', None, None, i))
            continue
        # takviye
        if n.startswith('glutensiz tibbi gida destekleri'):
            heading = t
            continue
        m = re.match(r'^([A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜa-zçğıöşü\- ]{1,30}):\s*$', t)
        if m and is_upperish(m.group(1)):
            ctx = compact(m.group(1))
            heading = t
            continue
        lines.append(make_line('ist', domain, 'takviye', t, heading or 'Tıbbi Gıda Destekleri', ctx, None, i))
    if domain == 'ilac':
        lines = merge_ilac_company_rows(lines)
    else:
        merged = []
        for ln in lines:
            if merged and re.match(r'^ve\s', ln['text']) and len(ln['text'].split()) <= 6 and \
                    not merged[-1]['text'].rstrip().endswith('.'):
                merged[-1]['text'] = clean(merged[-1]['text'] + ' ' + ln['text'])
                continue
            merged.append(ln)
        lines = merged
    return lines


def is_company_statement(n):
    return bool(re.search(r'\bfirma\w*\b', n) and re.search(
        r'glutensiz|gluten icermemektedir|icermemektedir|tum ilaclari|hicbir urunu', n))


def merge_ilac_company_rows(lines):
    """'ADEKA' + ': Firmanın tüm ilaçları glutensizdir.' satırlarını birleştir, firma kategorisine al."""
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        t = ln['text']
        nxt = lines[i + 1]['text'] if i + 1 < len(lines) else ''
        cont = re.match(r'^\s*[:I]?\s*:', nxt) or re.match(r'^(firma|firmanin|firmasinin)\b', norm(nxt))
        if is_upperish(t) and len(t) < 45 and nxt and cont and not re.search(r'\d', t):
            merged = clean(t + ' ' + nxt)
            merged = re.sub(r'\s+:', ':', merged)
            nl = dict(ln, text=merged, cat='ilac-firma')
            out.append(nl)
            i += 2
            continue
        out.append(ln)
        i += 1
    return out

# ------------------------------------------------------------- Ankara ----
ANK_GROUP_BRANDS = {compact('Peyman Bahçeden'), compact('Peyman Dorleo'), compact('Peyman Çitliyo')}
ANK_BRAND_HEADINGS = {
    'bolulu hasan usta': 'Bolulu Hasan Usta', 'mado': 'Mado', 'saray muhallebicisi': 'Saray Muhallebicisi',
    'ikea': 'İKEA', 'nescafe': None,
}


def parse_ank(page):
    rows = html_rows(page['content']['rendered'])
    lines, extras = [], {'mekan': [], 'otel': [], 'universite': []}
    section, domain, cat, heading, ctx = 'intro', 'gida', None, '', None
    cur_venue = None
    for i, r in enumerate(rows):
        t = camel_split(r['text'])
        n = norm(t)
        if not n or re.fullmatch(r'[*\-—–_x ]+', n) or re.fullmatch(r'[*\-—–_xX ]+', t):
            continue
        bold = r['bold'] > 0.6
        semibold = r['bold'] >= 0.3
        nz = n.replace(' ', '')
        # ---- bölüm sınırları
        if section == 'intro' and n.startswith('atistirmalik'):
            section, domain, cat, heading, ctx = 'food', 'gida', 'atistirmalik', t, None
            continue
        if section == 'intro':
            continue
        if n.startswith('okunarak alinmasi gereken'):
            section, domain, cat, heading, ctx = 'read', 'gida', 'etiket-oku', t, None
            continue
        if n.startswith('bazi colyaklilara ciltte'):
            section, domain, cat, heading, ctx = 'kozmetik', 'kozmetik', 'sampuan', t, None
            lines.append(make_line('ank', 'kozmetik', 'sampuan', t, t, None, 'note', i))
            continue
        if n.startswith('ambalaj uzerinde allerjen uyarisi'):
            section, domain, cat, heading, ctx = 'read', 'gida', 'etiket-oku', t, None
            continue
        if n.startswith('glutensiz urun hizmeti veren isletmeler'):
            section = 'mekan'
            continue
        if n.startswith('ilaclar'):
            section, domain, cat, heading, ctx = 'ilac', 'ilac', 'ilac-firma', 'Glutensiz İlaçlar', None
            rest = re.sub(r'^\s*İ\s*L\s*A\s*Ç\s*L\s*A\s*R\s*', '', t)
            for part in split_company_statements(rest):
                lines.append(make_line('ank', 'ilac', 'ilac-firma', part, heading, None, None, i))
            continue
        if n == 'glutensiz' and section in ('mekan', 'read', 'kozmetik', 'food'):
            continue
        if n.startswith('glutensiz tibbi gida destekleri'):
            section, domain, cat, heading, ctx = 'takviye', 'takviye', 'takviye', t, None
            continue
        if nz.startswith('glutensizoteller'):
            section = 'otel'
            continue
        if n.startswith('glutensiz menusu olan universiteler'):
            section = 'universite'
            continue

        # ---- bölüm içerikleri
        if section == 'mekan':
            if n in ('ankara',):
                continue
            head2 = ' '.join(re.split(r'\s*-\s*Sadece|\(', t)[0].split()[:3])
            is_detail = (not bold) or n.startswith('tel') or re.match(r'^[\d(]', n) or \
                re.search(r'\b(cad|sok|mah|no|bulvar|avm|sube|www)\b', norm(head2)) or not is_upperish(head2)
            if bold and not is_detail:
                cur_venue = {'name': t, 'details': []}
                extras['mekan'].append(cur_venue)
            elif cur_venue:
                cur_venue['details'].append(t)
            continue
        if section == 'otel':
            if n.startswith('otel ekipmanlari'):
                extras['otel_note'] = t
                continue
            if bold and is_upperish(t) and not n.startswith('tel'):
                cur_venue = {'name': t, 'details': []}
                extras['otel'].append(cur_venue)
            elif cur_venue:
                cur_venue['details'].append(t)
            continue
        if section == 'universite':
            extras['universite'].append(t)
            continue
        if section == 'ilac':
            if re.match(r'^[A-ZÇĞİÖŞÜ .\-]+(?:İLAÇ|FARMA|FİRMASI)?\s*:', t) and \
                    re.search(r'firma|ilac', n) and len(t) < 260 and not canon_ilac_heading(t):
                for part in split_company_statements(t):
                    lines.append(make_line('ank', 'ilac', 'ilac-firma', part, heading, None, None, i))
                continue
            th = canon_ilac_heading(t)
            if th:
                label, rest = th
                heading = label
                if rest:
                    for item in split_drug_list(rest):
                        lines.append(make_line('ank', 'ilac', 'ilac', item, label, None, None, i))
                continue
            for item in split_drug_list(t):
                lines.append(make_line('ank', 'ilac', 'ilac', item, heading, None, None, i))
            continue
        if section == 'takviye':
            lines.append(make_line('ank', 'takviye', 'takviye', t, heading, None, None, i))
            continue
        if section == 'kozmetik':
            cid = canon_cat(t, 'kozmetik') if bold else None
            if cid:
                cat, heading, ctx = cid, t, None
                continue
            lines.append(make_line('ank', 'kozmetik', cat, t, heading, None, None, i))
            continue
        if section == 'read':
            if bold:
                cid = canon_cat(t, 'gida')
                nn = n
                if cid == 'etiket-oku':
                    heading = t
                    ctx = 'unilever' if 'unilever' in nn else ('mondelezkent' if 'kent' in nn else (
                        'nestle' if 'nestle' in nn else ctx))
                    continue
            kind = 'read'
            if WARN_RX.search(n) and n.startswith('dikkat'):
                kind = 'warn'
            elif NOTE_START.match(n) or (len(n.split()) > 22 and camel_split(r['text']) == r['text']):
                kind = 'note'
            force_c = bool(ctx) and camel_split(r['text']) != r['text']
            lines.append(make_line('ank', 'gida', 'etiket-oku', t, heading, ctx, kind, i, force_c))
            continue
        # ---- gıda
        if bold and len(nz) <= 2:
            continue  # alfabe ayırıcı: B, C-Ç, S- Ş
        nn = n.replace(':', ' ').strip()
        if bold and nn in ANK_BRAND_HEADINGS:
            b = ANK_BRAND_HEADINGS[nn]
            if b:
                ctx, heading = compact(b), t
            else:
                heading = t
            continue
        head_part = re.split(r'[(\-–]', t)[0]
        short_head = len(norm(head_part).split()) <= 7 or ':' in head_part
        if ':' not in t[:40] and t.rstrip().endswith(('.', '…', '!')) and len(norm(t).split()) >= 3:
            short_head = False   # cümle: başlık değil, not satırı ("YOĞURT : (...)." gibi başlıklar hariç)
        if short_head and (bold or semibold or (is_upperish(head_part) and len(norm(head_part).split()) <= 6)):
            cid = canon_cat_strict(t, 'gida')
            if cid and cid != 'etiket-oku' and (bold or semibold or head_part.rstrip().endswith(':')
                                                 or len(norm(head_part).split()) <= 3):
                cat, ctx = cid, None
                heading = t
                # başlıktaki koşul/açıklama: parantez içi
                m = re.search(r'\((.+)', t)
                if m:
                    lines.append(make_line('ank', 'gida', cat, clean(m.group(1).rstrip(')')), t, None, 'note', i))
                continue
        # marka grubu satırı: "Peyman Bahçeden" ardından ürünler
        key_g, k_g = find_alias(n.split(), 0)
        if key_g in ANK_GROUP_BRANDS and k_g == len(n.split()):
            ctx = key_g
            continue
        if key_g in ANK_GROUP_BRANDS:
            ctx = key_g
        lines.append(make_line('ank', 'gida', cat, t, heading, ctx, None, i))
    return merge_continuations(lines), extras


ILAC_HEADINGS = ['ANALJEZİK', 'ÜST-ALT SOLUNUM', 'ANTİHİSTAMİNİK', 'DAHİLİYE', 'TANSİYON', 'KALP DAMAR',
                 'KANSIZLIK', 'VİT. D3', 'ENDOKRİNOLOJİ', 'DERMOTOLOJİ', 'GÖZ', 'DİABET', 'JİNEKOLOJİ', 'ASTIM',
                 'PSİKOLOJİK', 'EPİLEPSİ', 'ORAL VE DİŞETİ', 'ALZHEİMER', 'PARKİNSON', 'KANSER', 'ANESTEZİ',
                 'ÇEŞİTLİ İLAÇLAR']


def canon_ilac_heading(t):
    for h in ILAC_HEADINGS:
        if t.upper().startswith(h) or t.startswith(h):
            m = re.match(r'^([^:]+):?\s*(.*)$', t)
            label, rest = clean(m.group(1)), clean(m.group(2))
            if rest and ':' not in t:
                # "TANSİYON Hyzaar, ..." biçimi
                parts = t.split(' ', 1)
                label, rest = parts[0], parts[1] if len(parts) > 1 else ''
            return label.title(), rest
    return None


def split_drug_list(t):
    if t.count(',') >= 2:
        return [clean(x) for x in re.split(r'[,;]', t) if clean(x) and len(clean(x)) > 1]
    return [t]


def split_company_statements(t):
    """'BİLİM İLAÇ : ... PFİZER : ...' -> ayrı ifadeler"""
    t = clean(t)
    parts = re.split(r'(?<=[.…])\s+(?=[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ .\-]{2,}\s*:)', t)
    return [clean(p) for p in parts if clean(p)]

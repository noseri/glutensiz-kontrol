#!/usr/bin/env bash
# Glutensiz Kontrol — bütün testler. Yerelde ve GitHub Actions'ta (her yayından önce) aynı şekilde çalışır.
#   bash tests/calistir.sh            hepsi
#   bash tests/calistir.sh test_api   yalnızca adı geçenler
# Gerekenler: python3 + playwright, Chrome (GK_CHROME ile yolu verilebilir), node ve tests/ altında `npm ci`.
# Arayüz testleri sabit bir test verisiyle (tests/veri/data.json) çalışır; haftalık liste güncellemesi
# onları bozmaz. Gerçek liste ayrıca kısa bir duman testinden geçer (duman.py).
set -uo pipefail
secilen=" $* "   # adı verilen testler (boşsa hepsi)
KOK=$(cd "$(dirname "$0")/.." && pwd)
T=$(mktemp -d)
export GK_KOK="$KOK" WRANGLER_SEND_METRICS=false CI=true PYTHONDONTWRITEBYTECODE=1
WR="${GK_WRANGLER:-$KOK/tests/node_modules/.bin/wrangler}"
[ -x "$WR" ] || { echo "wrangler yok: önce  npm ci --prefix tests"; exit 1; }
if [ -z "${GK_CHROME:-}" ] && [ -x /usr/bin/google-chrome ]; then export GK_CHROME=/usr/bin/google-chrome; fi
SIFRE_1='deneme-adem-1234'; SIFRE_2='Mor kedi sabah çayı ğüşİı'   # yalnızca yerel test sunucusu için

temizle() {
  [ -n "${WPID:-}" ] && kill -- -"$WPID" 2>/dev/null
  for p in "${SPIDS[@]:-}"; do [ -n "$p" ] && kill "$p" 2>/dev/null; done
  rm -rf "$T"
}
trap temizle EXIT

# portlar boş olmalı (eski bir yerel sunucu kalmışsa kapatılır)
pkill -f "http.server 876[5-7]" 2>/dev/null; pkill -f "wrangler.*dev.*--port 8787" 2>/dev/null; pkill -f workerd 2>/dev/null; sleep 1

# site kopyaları: 8765 test verisiyle, 8766 service worker testi için ayrı kopya, 8767 gerçek liste (duman testi)
mkdir -p "$T/site" "$T/site_sw" "$T/site_sw_ham" "$T/site_gercek"
cp -r "$KOK/site/." "$T/site_gercek/"
cp -r "$KOK/site/." "$T/site/"; cp "$KOK/tests/veri/data.json" "$T/site/data.json"
cp -r "$T/site/." "$T/site_sw_ham/"                       # damgasız kopya: sürüm güncellemesini denemek için
cp -r "$T/site/." "$T/site_sw/"; bash "$KOK/scripts/surum.sh" "$T/site_sw" test1 > /dev/null   # yayındaki gibi damgalı
export GK_SW_KOPYA="$T/site_sw" GK_SW_HAM="$T/site_sw_ham" GK_SW_VERI="$KOK/tests/veri/data.json"
SPIDS=()
for x in "8765 site" "8766 site_sw" "8767 site_gercek"; do
  port=${x% *}; dizin=${x#* }
  python3 -m http.server "$port" --bind 127.0.0.1 --directory "$T/$dizin" > "$T/$dizin.log" 2>&1 & SPIDS+=($!)
done

# yerel sunucu (Worker + D1); her test dosyası boş bir veritabanıyla başlar
WPID=""
sunucu() {
  if [ -n "$WPID" ]; then kill -- -"$WPID" 2>/dev/null; sleep 1; fi
  rm -rf "$T/d1"
  (cd "$KOK/worker" && "$WR" d1 execute glutensiz-liste --local --persist-to "$T/d1" --file schema.sql > "$T/d1.log" 2>&1) || { cat "$T/d1.log"; return 1; }
  (cd "$KOK/worker" && exec setsid "$WR" dev --local --port 8787 --ip 127.0.0.1 --persist-to "$T/d1" \
      --var "IZINLI_KOKENLER:http://localhost:8765,http://localhost:8766" --var "ANAHTAR_1:$SIFRE_1" --var "ANAHTAR_2:$SIFRE_2" \
      > "$T/wrangler.log" 2>&1) &
  WPID=$!
  for i in $(seq 1 60); do curl -s -o /dev/null http://127.0.0.1:8787/ && return 0; sleep 1; done
  echo "yerel sunucu açılmadı:"; tail -20 "$T/wrangler.log"; return 1
}
for i in $(seq 1 20); do curl -s -o /dev/null http://localhost:8765/index.html && break; sleep 0.5; done

sonuc=0; ozet=()
calistir() {   # calistir <dosya> [sunucu] [tohum]
  local ad="${1%.py}"
  if [ "$secilen" != "  " ] && [[ "$secilen" != *" $ad "* ]]; then return; fi
  echo; echo "== $ad"
  if [ "${2:-}" = sunucu ]; then sunucu || { sonuc=1; ozet+=("✗ $ad (sunucu açılmadı)"); return; }; fi
  if [ "${3:-}" = tohum ]; then python3 -c "import sys; sys.path.insert(0, '$KOK/tests'); import ortak; ortak.tohum()" || { sonuc=1; ozet+=("✗ $ad (tohum)"); return; }; fi
  if python3 "$KOK/tests/$1"; then ozet+=("✓ $ad"); else sonuc=1; ozet+=("✗ $ad"); fi
}
calistir test_kimlik.py
calistir test_api.py sunucu
calistir test_yedek.py sunucu
calistir test_giris.py sunucu tohum
calistir test_ux.py sunucu tohum
calistir test_kat.py sunucu tohum
calistir test_duzelt.py sunucu tohum
calistir test_tepki.py sunucu tohum
calistir test_kontrol.py sunucu tohum
calistir test_sw.py
calistir duman.py

echo; echo "== Özet"; printf '%s\n' "${ozet[@]}"
exit $sonuc

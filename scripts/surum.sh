#!/usr/bin/env bash
# Yayın sürüm damgası: index.html ve sw.js içindeki __SURUM__ yerine verilen sürüm yazılır.
# Her yayının stil ve betik adresleri (…?v=<sürüm>) ve çevrimdışı önbelleği böylece kendine özgü olur:
# telefonda eski ve yeni sürümün dosyaları karışmaz. Sayfa yayını (pages.yml) ve testler kullanır.
#   bash scripts/surum.sh <site_klasörü> <sürüm>
set -euo pipefail
d="$1"; v="$2"
[[ "$v" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "geçersiz sürüm: $v"; exit 1; }
sed -i "s/__SURUM__/$v/g" "$d/index.html" "$d/sw.js"
if grep -q "__SURUM__" "$d/index.html" "$d/sw.js"; then echo "damgasız yer kaldı"; exit 1; fi
grep -q "?v=$v" "$d/index.html" && grep -q "SURUM = '$v'" "$d/sw.js" || { echo "damga uygulanamadı"; exit 1; }
echo "sürüm damgası: $v"

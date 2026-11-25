#!/usr/bin/env bash
# Haftalık kontrol sonucunu uygular: dosyaları kaydeder, gerekirse bildirim (issue) açar,
# sayfanın yeniden yayınlanıp yayınlanmayacağını GITHUB_OUTPUT'a yazar.
# GitHub Actions içinde çalışır (GH_TOKEN, GITHUB_OUTPUT ortamda olmalı).
set -euo pipefail
B=out/build
SITE_URL="${SITE_URL:-}"
action=$(python3 -I -c "import json;print(json.load(open('$B/summary.json'))['action'])")
missing=$(python3 -I -c "import json;print(len(json.load(open('$B/summary.json')).get('missing', [])))")
python3 -I scripts/report.py "$B" "$SITE_URL"
kind=$(cat "$B/kind.txt")
deploy=false
today=$(TZ=Europe/Istanbul date +%Y-%m-%d)

push() { git push origin HEAD:main || { git pull --rebase origin main && git push origin HEAD:main; }; }

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

case "$action" in
  publish)
    cp "$B/data.json" site/data.json
    cp "$B/pages.json" raw/pages.json
    git add site/data.json raw/pages.json
    if [ "$kind" = "degisiklik" ]; then msg="Listeler güncellendi ($today)"; else msg="Kaynak sayfa düzenlendi, ürün satırları aynı ($today)"; fi
    if git commit -m "$msg"; then push; deploy=true; fi
    ;;
  checked_only)
    cp "$B/data.json" site/data.json
    git add site/data.json
    if git commit -m "Son kontrol: $today (değişiklik yok)"; then push; deploy=true; fi
    ;;
  *)
    echo "Yayın yok: $action"
    ;;
esac

if [ "$kind" != "sessiz" ]; then
  color=b60205; [ "$kind" = "degisiklik" ] && color=0b7a42
  gh label create "$kind" --color "$color" --force >/dev/null 2>&1 || true
  title=$(cat "$B/issue_title.txt")
  open_no=""
  if [ "$kind" != "degisiklik" ]; then   # aynı sorun için açık bildirim varsa altına yaz
    open_no=$(gh issue list --label "$kind" --state open --json number --jq '.[].number' | head -n1 || true)
  fi
  if [ -n "$open_no" ]; then
    gh issue comment "$open_no" --body-file "$B/issue.md"
  else
    gh issue create --title "$title" --body-file "$B/issue.md" --label "$kind"
  fi
fi

# isteğe bağlı Telegram / web kancası bildirimi
if [ "$kind" != "sessiz" ]; then
  bash scripts/notify.sh "$(cat "$B/issue_title.txt")" "$B/issue.md"
fi

# tüm kaynaklar yeniden alınabildiyse açık "kaynak-hatasi" bildirimlerini kapat
if { [ "$action" = "checked_only" ] || [ "$action" = "publish" ]; } && [ "$missing" = "0" ]; then
  for n in $(gh issue list --label kaynak-hatasi --state open --json number --jq '.[].number' 2>/dev/null || true); do
    gh issue close "$n" --comment "Kaynaklar $today tarihinde yeniden alındı." || true
  done
fi

echo "deploy=$deploy" >> "$GITHUB_OUTPUT"
echo "Sonuç: $action / $kind / yayın=$deploy"

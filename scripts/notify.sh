#!/usr/bin/env bash
# İsteğe bağlı anlık bildirim: Telegram ve/veya basit bir web kancası (webhook).
# Kullanım: bash scripts/notify.sh "<başlık>" <metin_dosyası>
# Depo ayarlarında (Settings → Secrets and variables → Actions) tanımlıysa çalışır, yoksa sessizce geçer:
#   TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID  → Telegram mesajı
#   NOTIFY_WEBHOOK_URL                     → düz metin POST (ör. ntfy.sh konusu, Make/Zapier kancası)
set -uo pipefail
title="$1"; file="$2"
msg="$title"$'\n\n'"$(head -c 3500 "$file")"
sent=0
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
  if curl -fsS -m 30 -o /dev/null "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
       --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" --data-urlencode "text=${msg}" \
       --data-urlencode "disable_web_page_preview=true"; then
    echo "Telegram bildirimi gönderildi."; sent=1
  else
    echo "::warning::Telegram bildirimi gönderilemedi (jeton ya da sohbet kimliği yanlış olabilir)."
  fi
fi
if [ -n "${NOTIFY_WEBHOOK_URL:-}" ]; then
  if curl -fsS -m 30 -o /dev/null -X POST -H "Content-Type: text/plain; charset=utf-8" --data-binary "$msg" "$NOTIFY_WEBHOOK_URL"; then
    echo "Web kancası bildirimi gönderildi."; sent=1
  else
    echo "::warning::Web kancası bildirimi gönderilemedi."
  fi
fi
[ "$sent" = 0 ] && echo "Anlık bildirim ayarlı değil (yalnızca GitHub e-postası)."
exit 0

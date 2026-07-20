#!/bin/bash
# φ-lang v3 — v5_notify_tg.sh
# Send φ-coded message to Telegram via bot API
# Usage: bash v5_notify_tg.sh "<phi_message>" 
# φ-code: v5 (notify), v5p7=tg  (p7 = telegram key shortcut)
# Requires: TG_BOT_TOKEN and TG_CHAT_ID in environment

TG_TOKEN="${TG_BOT_TOKEN:-}"
TG_CHAT="${TG_CHAT_ID:--5355627054}"

# Auto-load token from .env if not set
if [ -z "$TG_TOKEN" ] && [ -f "$HOME/.hermes/.env" ]; then
    TG_TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$HOME/.hermes/.env" | head -1 | cut -d'=' -f2-)
fi
MSG="${1:-c0na0_s7}"

if [ -z "$TG_TOKEN" ]; then
    echo "φerror:no_tg_token,set_TG_BOT_TOKEN"
    exit 1
fi

# Build φ-format message
NOW=$(date -u +"%H:%M")
PHI_MSG="φ-${PHI_NODE:-unknown}:v5,$MSG,ts=${NOW}Z,s7"

# Send via Telegram API
RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
    -d "chat_id=${TG_CHAT}" \
    -d "text=${PHI_MSG}" \
    -d "parse_mode=HTML" 2>&1)

if echo "$RESPONSE" | grep -q '"ok":true'; then
    echo "φv5:tg=sent,$MSG,s7"
else
    echo "φerror:tg_send_failed,response=$(echo $RESPONSE | head -c 100)"
    exit 1
fi

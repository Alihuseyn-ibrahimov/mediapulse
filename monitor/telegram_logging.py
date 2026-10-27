"""
Django 500 (server) xətası baş verəndə dərhal Telegram-a bildiriş göndərir.
Beləliklə sayt xarab olanda əl ilə aşkar etməyi gözləmirsən — anında xəbər gəlir.

Konfiqurasiya: settings.py LOGGING → django.request loggeri bu handler-ə bağlanır.
Açarlar .env-dən oxunur (TELEGRAM_TOKEN, TELEGRAM_ALERT_CHAT_ID / TELEGRAM_CHAT_ID).
"""
import os
import time
import logging
import json
import urllib.request
import urllib.parse

# Eyni xətanı təkrar-təkrar göndərməmək üçün sadə soyuma (per-process)
_last_sent = {}
_COOLDOWN = 600   # eyni xəta imzası üçün 10 dəqiqədə bir dəfə


class TelegramErrorHandler(logging.Handler):
    def emit(self, record):
        try:
            token = os.environ.get("TELEGRAM_TOKEN", "")
            chat_id = (os.environ.get("TELEGRAM_ALERT_CHAT_ID")
                       or os.environ.get("TELEGRAM_CHAT_ID", ""))
            if not token or not chat_id:
                return

            # Spam qarşısı — eyni fayl+sətir imzası üçün soyuma
            sig = f"{record.pathname}:{record.lineno}"
            now = time.time()
            if now - _last_sent.get(sig, 0) < _COOLDOWN:
                return
            _last_sent[sig] = now

            body = self.format(record)          # traceback daxil (exc_info varsa)
            path = getattr(getattr(record, "request", None), "path", "")
            text = (
                "🚨 <b>MediaPulse — SERVER XƏTASI</b>\n"
                f"📍 {path}\n\n"
                f"<pre>{_esc(body)[:3200]}</pre>"
            )
            data = urllib.parse.urlencode({
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage", data=data)
            urllib.request.urlopen(req, timeout=8)
        except Exception:
            # Logging handler heç vaxt öz-özünə exception atmamalıdır
            pass


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

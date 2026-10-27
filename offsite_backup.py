"""
Off-site backup: db.sqlite3 → sıxıl → AES-256 şifrələ → e-poçtla göndər (SendGrid).
Şifrə açarı və hədəf e-poçt .env-dən oxunur (BACKUP_PASSPHRASE, BACKUP_EMAIL).
Bərpa:  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass pass:AÇAR -in fayl.enc | gunzip > db.sqlite3
Cron ilə gündəlik işlədilir.
"""
import os
import django
import subprocess
import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saas_core.settings")
django.setup()

from django.core.mail import EmailMessage
from django.conf import settings

DB   = "/opt/saas_core/db.sqlite3"
PASS = os.environ.get("BACKUP_PASSPHRASE", "")
TO   = os.environ.get("BACKUP_EMAIL", "")

if not PASS or not TO:
    raise SystemExit("BACKUP_PASSPHRASE və ya BACKUP_EMAIL .env-də yoxdur")

ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
enc = f"/tmp/db_{ts}.sqlite3.gz.enc"

# sıxıl + şifrələ (açar əmr sətrində görünmür — env:-dən oxunur)
subprocess.run(
    f"gzip -c '{DB}' | openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt "
    f"-pass env:BACKUP_PASSPHRASE -out '{enc}'",
    shell=True, check=True, env={**os.environ},
)

with open(enc, "rb") as f:
    data = f.read()

msg = EmailMessage(
    subject=f"MediaPulse — DB backup ({ts})",
    body=(
        "Şifrələnmiş baza ehtiyat nüsxəsi əlavədədir (AES-256).\n"
        "Bərpa üçün BACKUP_PASSPHRASE lazımdır:\n"
        "  openssl enc -d -aes-256-cbc -pbkdf2 -iter 100000 -pass pass:AÇAR "
        "-in db_*.gz.enc | gunzip > db.sqlite3\n"
    ),
    from_email=settings.DEFAULT_FROM_EMAIL,
    to=[TO],
)
msg.attach(f"db_{ts}.sqlite3.gz.enc", data, "application/octet-stream")
msg.send()

os.remove(enc)
print(f"Off-site backup göndərildi → {TO}  ({len(data)} bayt)")

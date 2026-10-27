"""
SendGrid HTTP API email backend — requests ilə, SDK olmadan.
"""
import base64
import json
import urllib.request
import urllib.error
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings


class SendGridBackend(BaseEmailBackend):

    def send_messages(self, email_messages):
        api_key = getattr(settings, 'SENDGRID_API_KEY', '')
        sent = 0

        for msg in email_messages:
            try:
                payload = {
                    "personalizations": [{"to": [{"email": addr} for addr in msg.to]}],
                    "from": {"email": self._parse_email(msg.from_email or settings.DEFAULT_FROM_EMAIL),
                             "name": self._parse_name(msg.from_email or settings.DEFAULT_FROM_EMAIL)},
                    "subject": msg.subject,
                    "content": [{"type": "text/plain", "value": msg.body}],
                }

                attachments = getattr(msg, 'attachments', [])
                if attachments:
                    payload["attachments"] = []
                    for filename, content, mimetype in attachments:
                        if isinstance(content, bytes):
                            encoded = base64.b64encode(content).decode()
                        else:
                            encoded = base64.b64encode(content.encode()).decode()
                        payload["attachments"].append({
                            "content": encoded,
                            "filename": filename,
                            "type": mimetype,
                            "disposition": "attachment",
                        })

                data = json.dumps(payload).encode('utf-8')
                req = urllib.request.Request(
                    'https://api.sendgrid.com/v3/mail/send',
                    data=data,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                    },
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    if resp.status in (200, 201, 202):
                        sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return sent

    def _parse_email(self, from_email):
        if '<' in from_email:
            return from_email.split('<')[1].rstrip('>')
        return from_email

    def _parse_name(self, from_email):
        if '<' in from_email:
            return from_email.split('<')[0].strip()
        return ''

import os, django, json, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_core.settings')
django.setup()

from monitor.models import Organization, NewsResult

org = Organization.objects.get(slug='eesmn')

with open('/opt/pr-agent/repo/results.json', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for item in data:
    link = item.get('link', '#')
    if NewsResult.objects.filter(link=link, organization=org).exists():
        continue
    try:
        saved_at = datetime.datetime.fromisoformat(item.get('saved_at', ''))
        saved_at = saved_at.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        saved_at = datetime.datetime.now(datetime.timezone.utc)
    NewsResult.objects.create(
        organization=org,
        keyword=item.get('keyword', ''),
        title=item.get('title', ''),
        summary=item.get('summary', ''),
        link=link,
        source=item.get('source', ''),
        sentiment=item.get('sentiment', 'MÜSBƏT'),
        saved_at=saved_at,
    )
    count += 1

print(f'{count} xəbər import edildi')

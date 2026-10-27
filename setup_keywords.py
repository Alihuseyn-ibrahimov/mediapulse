import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_core.settings')
django.setup()

from monitor.models import Organization, Keyword, KeywordAlias

org = Organization.objects.get(slug='eesmn')

keywords = [
    ("Əmək və Əhalinin Sosial Müdafiəsi Nazirliyi", ["ƏƏSMN", "əəsmn", "Əmək Nazirliyi", "Sosial Nazirlik"]),
    ("Dövlət Sosial Müdafiə Fondu", ["DSMF", "dsmf", "Sosial Müdafiə Fondu", "Sosial Sığorta", "pensiya", "sosial müavinət", "sosial ödənişlər"]),
    ("Dövlət Əmək Müfəttişliyi Xidməti", ["DƏMX", "dəmx", "Əmək Müfəttişliyi"]),
    ("Sosial Xidmətlər Agentliyi", ["SXA", "günərzi", "ahıllar evi", "uşaqlar evi", "övladlığa götürmə"]),
    ("DOST Agentliyi", ["DOST mərkəzi", "Qarabağ DOST"]),
    ("Anar Əliyev", ["Nazir Anar Əliyev"]),
    ("Əlillik", ["DTSERA", "əlillik kəsildi", "əlillik müavinəti"]),
    ("İşsizlik", ["işsizlikdən sığorta", "məşğulluq", "özünüməşğulluq"]),
    ("Dövlət Tibbi Sosial Ekspertiza və Reabilitasiya Agentliyi", ["DTSERA", "Tibbi Sosial Ekspertiza", "Reabilitasiya Agentliyi"]),
    ("Minimum əmək haqqı", ["minimum maaş", "əməkhaqqılar artdı"]),
]

for kw_word, aliases in keywords:
    kw, _ = Keyword.objects.get_or_create(organization=org, word=kw_word)
    for alias in aliases:
        KeywordAlias.objects.get_or_create(keyword=kw, word=alias)

print(f"{Keyword.objects.filter(organization=org).count()} açar söz, aliaslarla birlikdə əlavə edildi")

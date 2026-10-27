# MediaPulse (saas_core) — Claude üçün iş təlimatı

Bu fayl `saas_core/` daxilində işləyəndə avtomatik yüklənir. Repo-səviyyəli
`../CLAUDE.md` qaydaları (Azərbaycan dili, `py`/`.venv`, təhlükəsizlik) burada da
qüvvədədir — aşağıda yalnız MediaPulse-a xas detallar var.

## Nədir

**mediapulse.az** — Azərbaycan dilli media monitorinq SaaS-ı (Django 6.0.6).
Multi-tenant: hər müştəri bir `Organization`. Aktiv pilot: **ƏƏSMN** (Əmək və
Əhalinin Sosial Müdafiəsi Nazirliyi, slug `eesmn`). Açar sözlərə uyğun xəbərləri
onlarla mənbədən toplayır, AI ilə sentiment (MÜSBƏT/MƏNFİ) təyin edir, dashboard-da
göstərir, Telegram bildirişi + gündəlik PDF e-poçt hesabatı göndərir.

## Struktur

| Qovluq/fayl | Nədir |
|---|---|
| `monitor/` | Əsas Django app: models, views, admin, PDF hesabat, SendGrid backend |
| `accounts/` | İstifadəçi/giriş |
| `saas_core/` | Django konfiqurasiyası (settings, urls, wsgi) |
| `templates/`, `static/` | Şablonlar (dashboard.html, landing), statik fayllar |
| `../agent.py` | **PR monitorinq mühərriki** (repo kökündə, aşağıya bax) |
| `../weekly_report.py` | Gündəlik PDF hesabat cron skripti (repo kökündə) |
| `../load_missed_links.py` | Qaçırılan linkləri DOCX-dən bazaya yükləyən skript |
| `../deploy.ps1` | Deploy skripti (repo kökündə) |

## Data model (`monitor/models.py`)

- `Organization` — tenant. Vacib sahələr: `slug`, `weekly_report_enabled`,
  `report_email` (TextField, çoxlu ünvan — vergül/sətirlə ayrılır),
  `notif_daily_summary`, `notif_daily_hour` (0-23, **gündəlik xülasə + e-poçt
  hesabatının saatı**, Bakı vaxtı), `notif_on_negative/positive`.
- `OrganizationMember` — user↔org, rol (admin/viewer).
- `Keyword` / `KeywordAlias` — dashboard-dan idarə olunan açar sözlər.
- `NewsResult` — tapılan xəbər (title, link, source, sentiment, saved_at). **Əsas
  nəticə cədvəli.**
- `TvClip` — TV monitorinqdən gələn kliplər (bax TV-monitor bölməsi).
- `MissedLink` — istifadəçinin manual tapdığı, sistemin qaçırdığı linklər
  (category: facebook/youtube/news/other; report_date). Apify müqayisəsi üçün.
- `AuditLog` — admin dəyişikliklərinin izi (`AuditMixin`).

## agent.py — PR monitorinq mühərriki (KRİTİK)

`../agent.py` (repo kökü, serverdə `/opt/pr-agent/agent.py`, systemd `pr-agent`,
venv `/opt/pr-agent/bin/python3`). Django-dan AYRI proses; nəticələri `NewsResult`-a
yazır + Telegram alert göndərir.

- **`.gitignore`-dadır** (içində API açarları var — Groq/Gemini, Telegram token).
  **Heç vaxt commit etmə.** Deploy: `scp` + `systemctl restart pr-agent`. Dəyişəndən
  sonra lokal↔prod `md5sum` ilə sinxronluğu yoxla.
- **Mənbələr:** Google News axtarışı, `AZ_RSS_FEEDS` (~140 RSS), `DIRECT_SCRAPE_SITES`
  (RSS-siz saytlar → homepage skrape), `TG_CHANNELS` (açıq Telegram `t.me/s/`),
  `AZ_TV_CHANNELS` (YouTube RSS), DuckDuckGo. **Facebook SÖNDÜRÜLÜB**
  (`ENABLE_FACEBOOK=False`), Instagram dəstəyi YOX — hər ikisi Apify gözləyir
  (`FB_APIFY_PAGES`, `INSTAGRAM_APIFY_ACCOUNTS` siyahılarında hazır saxlanılır).
- **Açar sözlər** (`KEYWORDS` dict): kanonik ad → alias siyahısı. AZ + rus dili
  (rus AZ media versiyaları üçün). **QAYDA: yeni açar söz = ən qısa dəyişməz KÖK**
  (tam cümlə yox). `_ai_analyze` (Gemini) aidiyyət+sentiment filtridir —
  false-positive-ləri süzdüyü üçün geniş kök təhlükəsizdir.
- **Matcher** (`keyword_matches`→`_phrase_matches`→`_word_present`): söz-sərhədi +
  0-6 son şəkilçi, `[a-zЀ-ӿ]` (latın+kiril). q→ğ yumşalması kimi hallarda konkret
  forma da əlavə etmək lazım ola bilər.
- **Gündəlik boşluq döngəsi:** istifadəçi hər gün qaçırılan xəbərləri (DOCX)
  göndərir → `load_missed_links.py` bazaya yükləyir → başlıqlar canlı
  `keyword_matches` ilə test olunur → boşluq açar sözlə bağlanır → deploy.
  Metod və tarixçə: repo kökündə `task_plan.md`/`findings.md`.

## İnfrastruktur

- **Server:** DigitalOcean droplet `root@<SERVER_IP>` (SSH açar `~/.ssh/id_rsa`).
  Django kodu `/opt/saas_core/`. TIME_ZONE `Asia/Baku`, amma server saatı UTC.
- **Servislər (systemd):** `gunicorn` (Django web), `pr-agent` (agent.py). nginx
  reverse proxy, Cloudflare (DNS + edge). Sirlər `/opt/saas_core/.env`.
- **Baza:** **SQLite** — `/opt/saas_core/db.sqlite3` (tək fayl, deploy TOXUNMUR).
  Yük artsa PostgreSQL-ə keçid düşünülməlidir (hazırda `database is locked` yoxdur).
- **Cron-lar:** `weekly_report.py` (SAATLIQ `0 * * * *`, hər org öz `notif_daily_hour`
  saatında), `telegram_channels_check.py` (`*/5`, TG kanallarının sağlamlığı),
  `backup_db.sh` (03:30), `uptime_check.sh` (`*/5`), `offsite_backup.py` (həftəlik).

## E-poçt / hesabatlar

- **SendGrid** (`monitor/sendgrid_backend.py`, HTTP API). `DEFAULT_FROM_EMAIL =
  MediaPulse <noreply@mediapulse.az>`. Domen autentifikasiyası tam: DKIM + **SPF +
  DMARC** Cloudflare-də (mail.ru kimi sərt provayderlər üçün şərtdir).
- **PDF hesabat** (`monitor/views.py::_build_report_pdf_bytes`, reportlab, əlavə
  asılılıq yox). Üç yer eyni funksiyanı çağırır: dashboard export, test göndər,
  cron. **`for_email=True`** olanda üçüncü-tərəf xəbər linkləri PDF-dən ÇIXARILIR —
  yoxsa antivirus (Gmail/mail.ru) onlarla scrape-linki görüb bütün faylı "virus"
  kimi bloklayır. Yüklənən versiya linkləri saxlayır.
- **Çoxlu alıcı:** `report_email` bir neçə ünvan saxlayır; `parse_report_emails()`
  ayırır/doğrulayır.
- Font: `/usr/share/fonts/truetype/dejavu/DejaVuSans*.ttf` (serverdə mövcud;
  Windows-da lokal test üçün yoxdur → Helvetica fallback, AZ hərfləri görünməz —
  bu yalnız lokal test artefaktıdır).

## TV monitorinq inteqrasiyası

Ayrı **Hetzner VPS** (`<SERVER_IP>`, açar `~/.ssh/hetzner_tvmonitor`,
`/root/tv-monitor/`) 11 AZ TV kanalını izləyir, açar sözə uyğun süjet tapanda klip
kəsir. `watcher.py` klipi HƏM n8n-ə (Telegram təsdiq→YouTube), HƏM Django-ya
(`/landing-admin/tv-clips/ingest/`, header `X-Ingest-Secret`) göndərir → `TvClip` +
`NewsResult` (`source="TV: <kanal>"`) yaranır. Detallar: yaddaş
`tv_monitor_infrastructure`.

## Deploy (`../deploy.ps1`)

Ardıcıllıq: (1) lokal `manage.py test monitor` — **keçməsə deploy DAYANIR**;
(2) `scp` ilə agent.py + Django qovluqları + `weekly_report.py` +
`telegram_channels_check.py` + `load_missed_links.py`; (3) `migrate`; (4) `check`;
(5) `gunicorn`+`pr-agent` restart; (6) `https://mediapulse.az/` healthcheck (200).

- `db.sqlite3` **heç vaxt** köçürülmür (kopyalanan qovluqlarda deyil).
- **agent.py** deploy.ps1-də scp olunur, amma git-də İZLƏNMİR — dəyişikliyi ayrıca
  `scp` + restart ilə də etmək olar; hər iki halda `md5sum` ilə yoxla.
- Testlər: `monitor/tests.py` (smoke + regresiya). Yeni model/view/PDF dəyişikliyində
  test əlavə et; deploy qapısı testdən keçir.

## Konvensiyalar və təhlükəsizlik

- **Azərbaycan dili** hər yerdə (istifadəçi mətni, commit, şərh). Kod adları ingiliscə.
- **`.env` heç vaxt commit olunmur.** Açar/token dəyərlərini cavabda təkrarlama.
- **Nəticəni mənbədən yoxla** — DB/log/test çıxışından, "cavab gəldi" mətnindən yox.
  Keçmişdə fallback mesajı uğur kimi elan olunub; təkrarlanmasın.
- Django test-client bare skriptlərdə: `ALLOWED_HOSTS`-a `testserver` əlavə et,
  `SECURE_SSL_REDIRECT=False` override et (prod-da redirect var).
- Windows: konsola AZ hərf çap edəndə `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` işlət
  (cp1252 xətası kodun deyil, konsolun problemidir).

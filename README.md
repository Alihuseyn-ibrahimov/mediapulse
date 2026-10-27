# MediaPulse — Media Monitoring SaaS

A media monitoring platform for the Azerbaijani market. It collects news matching each client's keywords from dozens of sources, uses AI to classify the sentiment of every article (positive / negative) and presents the results on a dashboard.

## Key features
- **Multi-tenant** — each client is a separate organisation with role-based access (admin / viewer)
- **Keyword management** — with synonyms and aliases, editable from the dashboard
- **AI sentiment analysis** for every article
- **Alerts** — instant Telegram notifications for negative or positive coverage, plus a daily summary
- **Daily PDF report** delivered by email
- **TV monitoring** integration (broadcast clips)
- **Audit log** of all admin changes

## Tech stack
Python · Django · LLM (Groq) · Telegram Bot API · SendGrid · PDF generation

## Getting started
```bash
python -m venv .venv && .venv/Scripts/activate
pip install django  # plus the other dependencies
python manage.py migrate
python manage.py runserver
```

---

## Azərbaycan dilində

# MediaPulse — media monitorinq SaaS

Azərbaycan dilli media monitorinq platforması. Müştərinin açar sözlərinə uyğun
xəbərləri onlarla mənbədən toplayır, AI ilə tonallığı (müsbət/mənfi) təyin edir
və nəticələri dashboard-da göstərir.

## Əsas imkanlar
- **Multi-tenant:** hər müştəri ayrıca təşkilat, rol əsaslı giriş (admin/viewer)
- **Açar söz idarəetməsi:** sinonim/alias dəstəyi ilə, dashboard-dan
- **AI sentiment analizi** hər xəbər üçün
- **Bildirişlər:** Telegram (mənfi/müsbət xəbər anında), gündəlik xülasə
- **Gündəlik PDF hesabat** e-poçt ilə
- **TV monitorinq** klipləri ilə inteqrasiya
- Audit log — admin dəyişikliklərinin izi

## Texnologiyalar
Python · Django · LLM (Groq) · Telegram Bot API · SendGrid · PDF generasiyası

## Quraşdırma
```bash
python -m venv .venv && .venv/Scripts/activate
pip install django  # və digər asılılıqlar
python manage.py migrate
python manage.py runserver
```

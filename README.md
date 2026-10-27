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

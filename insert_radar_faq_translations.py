#!/usr/bin/env python3
"""Canlı nümunə lenti + FAQ bölmələrinin RU/EN/ES/TR tərcümələrini əlavə edir."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_core.settings')
sys.path.insert(0, '/opt/saas_core')
django.setup()

from monitor.models import LandingContent

TRANSLATIONS = {
    "ru": {
        "radar_label": "Живой пример",
        "radar_title": "Так ИИ оценивает новости",
        "radar_sub":   "Иллюстративные примеры типов новостей, ежедневно встречающихся в медиа",
        "radar1_text": "Представлена новая программа социальной поддержки",
        "radar2_text": "Жалоба на задержку в предоставлении услуги",
        "radar3_text": "Официально объявлено повышение заработной платы",
        "radar4_text": "Общественности стало известно об инфраструктурном недостатке",
        "radar5_text": "Подписано новое соглашение о партнёрстве",
        "radar6_text": "Заявление о защите персональных данных пользователей",
        "faq_label": "Вопросы",
        "faq_title": "Часто задаваемые вопросы",
        "faq_sub":   "Есть что-то непонятное? Ответ можно найти ниже",
        "faq1_q": "Сколько времени занимает настройка системы?",
        "faq1_a": "После заявки на демо ваш аккаунт будет готов в течение 24 часов. Мониторинг начинается автоматически сразу после добавления ключевых слов.",
        "faq2_q": "Какие источники отслеживаются?",
        "faq2_a": "Одновременно сканируются более 300 новостных порталов, Telegram-каналы, страницы Facebook, Instagram и YouTube. При необходимости можно добавить и индивидуальные источники.",
        "faq3_q": "Как проводится анализ тональности?",
        "faq3_a": "Каждая новость считывается искусственным интеллектом (Gemini AI) и оценивается как позитивная или негативная в зависимости от содержания. Вмешательство человека не требуется.",
        "faq4_q": "Как я получаю уведомления?",
        "faq4_a": "После подключения Telegram-бота уведомление приходит мгновенно при обнаружении новости. Для негативных новостей используется отдельный выделенный формат.",
        "faq5_q": "Каковы условия оплаты и договора?",
        "faq5_a": "Все планы оплачиваются ежемесячно, долгосрочных обязательств не требуется. Вы можете изменить или отменить свой план в любое время.",
    },
    "en": {
        "radar_label": "Live sample",
        "radar_title": "How the AI rates this",
        "radar_sub":   "Illustrative examples of the news types encountered daily in the media",
        "radar1_text": "New social support program launched",
        "radar2_text": "Complaint about delay in service delivery",
        "radar3_text": "Salary increase officially announced",
        "radar4_text": "Infrastructure flaw made public",
        "radar5_text": "New partnership agreement signed",
        "radar6_text": "Claim raised over protection of user data",
        "faq_label": "FAQ",
        "faq_title": "Frequently asked questions",
        "faq_sub":   "Something unclear? You may find the answer below",
        "faq1_q": "How long does setup take?",
        "faq1_a": "After your demo request, your account is ready within 24 hours. Monitoring starts automatically as soon as keywords are added.",
        "faq2_q": "Which sources are monitored?",
        "faq2_a": "Over 300 news portals, Telegram channels, Facebook, Instagram and YouTube pages are scanned simultaneously. Custom sources can also be added on request.",
        "faq3_q": "How is sentiment analysis performed?",
        "faq3_a": "Every news item is read by AI (Gemini AI) and rated as positive or negative based on its content. No human intervention is required.",
        "faq4_q": "How do I receive notifications?",
        "faq4_a": "Once the Telegram bot is connected, you get an instant notification as soon as a new item is found. Negative news uses a separately highlighted format.",
        "faq5_q": "What are the payment and contract terms?",
        "faq5_a": "All plans are billed monthly with no long-term commitment required. You can change or cancel your plan at any time.",
    },
    "es": {
        "radar_label": "Muestra en vivo",
        "radar_title": "Así lo evalúa la IA",
        "radar_sub":   "Ejemplos ilustrativos de los tipos de noticias que aparecen a diario en los medios",
        "radar1_text": "Se presentó un nuevo programa de apoyo social",
        "radar2_text": "Queja por retraso en la prestación de un servicio",
        "radar3_text": "Se anunció oficialmente un aumento salarial",
        "radar4_text": "Se hizo pública una deficiencia de infraestructura",
        "radar5_text": "Se firmó un nuevo acuerdo de colaboración",
        "radar6_text": "Reclamo sobre la protección de datos de los usuarios",
        "faq_label": "Preguntas",
        "faq_title": "Preguntas frecuentes",
        "faq_sub":   "¿Algo no está claro? Encuentre la respuesta a continuación",
        "faq1_q": "¿Cuánto tiempo tarda la configuración?",
        "faq1_a": "Tras solicitar la demo, su cuenta estará lista en 24 horas. El monitoreo comienza automáticamente en cuanto se agregan las palabras clave.",
        "faq2_q": "¿Qué fuentes se monitorean?",
        "faq2_a": "Se escanean simultáneamente más de 300 portales de noticias, canales de Telegram, páginas de Facebook, Instagram y YouTube. También se pueden agregar fuentes personalizadas a pedido.",
        "faq3_q": "¿Cómo se realiza el análisis de sentimiento?",
        "faq3_a": "Cada noticia es leída por la IA (Gemini AI) y evaluada como positiva o negativa según su contenido. No se requiere intervención humana.",
        "faq4_q": "¿Cómo recibo las notificaciones?",
        "faq4_a": "Una vez conectado el bot de Telegram, recibirá una notificación instantánea en cuanto se detecte una noticia. Las noticias negativas usan un formato destacado aparte.",
        "faq5_q": "¿Cuáles son las condiciones de pago y contrato?",
        "faq5_a": "Todos los planes se facturan mensualmente, sin compromiso a largo plazo. Puede cambiar o cancelar su plan en cualquier momento.",
    },
    "tr": {
        "radar_label": "Canlı örnek",
        "radar_title": "Yapay zeka bunu böyle değerlendiriyor",
        "radar_sub":   "Medyada günlük karşılaşılan haber türlerinin örnekleyici örnekleri",
        "radar1_text": "Yeni sosyal destek programı tanıtıldı",
        "radar2_text": "Hizmet sunumunda gecikme şikayeti",
        "radar3_text": "Maaş artışı resmen açıklandı",
        "radar4_text": "Altyapı eksikliği kamuoyuna duyuruldu",
        "radar5_text": "Yeni ortaklık anlaşması imzalandı",
        "radar6_text": "Kullanıcı verilerinin korunmasıyla ilgili iddia",
        "faq_label": "Sorular",
        "faq_title": "Sıkça sorulan sorular",
        "faq_sub":   "Belirsiz bir şey mi var? Yanıtı aşağıda bulabilirsiniz",
        "faq1_q": "Sistemin kurulumu ne kadar sürer?",
        "faq1_a": "Demo talebinizden sonra hesabınız 24 saat içinde hazır olur. Anahtar kelimeler eklendikten hemen sonra izleme otomatik olarak başlar.",
        "faq2_q": "Hangi kaynaklar izleniyor?",
        "faq2_a": "300'den fazla haber portalı, Telegram kanalları, Facebook, Instagram ve YouTube sayfaları aynı anda taranır. Talep üzerine özel kaynaklar da eklenebilir.",
        "faq3_q": "Duygu analizi nasıl yapılıyor?",
        "faq3_a": "Her haber yapay zeka (Gemini AI) tarafından okunur ve içeriğine göre pozitif veya negatif olarak değerlendirilir. İnsan müdahalesi gerekmez.",
        "faq4_q": "Bildirimleri nasıl alırım?",
        "faq4_a": "Telegram botu bağlandıktan sonra yeni bir haber bulunduğunda anında bildirim gelir. Negatif haberler için ayrı, vurgulanmış bir format kullanılır.",
        "faq5_q": "Ödeme ve sözleşme şartları nasıldır?",
        "faq5_a": "Tüm planlar aylık ödemelidir, uzun vadeli taahhüt gerekmez. Planınızı istediğiniz zaman değiştirebilir veya iptal edebilirsiniz.",
    },
}

count = 0
for lang, values in TRANSLATIONS.items():
    for key, value in values.items():
        obj, created = LandingContent.objects.get_or_create(key=key, lang=lang)
        if created or obj.value != value:
            obj.value = value
            obj.save()
            count += 1

print(f"Tərcümələr əlavə edildi: {count} dəyər")

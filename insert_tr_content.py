#!/usr/bin/env python3
"""Landing məzmununu Türkcə əlavə edir."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'saas_core.settings')
sys.path.insert(0, '/opt/saas_core')
django.setup()

from monitor.models import LandingContent

TR = {
    "hero_title":         "Medya haberlerinizi",
    "hero_title_hl":      "gerçek zamanlı izleyin",
    "hero_desc":          "Kurumunuz hakkında çevrimiçi medyada, sosyal ağlarda ve Telegram kanallarında neler yazıldığını anında öğrenin. Yapay zeka her haberi analiz eder.",
    "stat1_num": "300+",  "stat1_lbl": "İzlenen haber kaynağı",
    "stat2_num": "15 dk", "stat2_lbl": "Güncelleme aralığı",
    "stat3_num": "AI",    "stat3_lbl": "Duygu analizi",
    "stat4_num": "24/7",  "stat4_lbl": "Kesintisiz izleme",
    "feat_title": "Ne sunuyoruz?",
    "feat_sub":   "MediaPulse — devlet kurumları ve şirketler için tasarlanmış medya izleme platformu",
    "feat1_icon": "📰", "feat1_title": "Geniş kaynak kapsamı",      "feat1_desc": "Azerbaycan'ın 300'den fazla haber portalı, Telegram kanalları, Facebook ve Instagram sayfaları aynı anda izlenir.",
    "feat2_icon": "🤖", "feat2_title": "Yapay zeka analizi",        "feat2_desc": "Gemini AI her haberi okuyarak negatif, nötr veya pozitif olarak değerlendirir. İnsan faktörü olmadan, doğru sonuç.",
    "feat3_icon": "🔔", "feat3_title": "Anlık Telegram bildirimi",  "feat3_desc": "Yeni haber bulunduğunda Telegram'a bildirim gönderilir. Olumsuz haberler özel olarak işaretlenir.",
    "feat4_icon": "🔑", "feat4_title": "Anahtar kelime sistemi",    "feat4_desc": "İstediğiniz anahtar kelimeyi ve eş anlamlılarını ekleyin. Ajan tüm kaynaklarda otomatik arama yapar.",
    "feat5_icon": "📊", "feat5_title": "Raporlama ve analiz",       "feat5_desc": "PDF ve Excel formatında raporlar oluşturun. Haftalık e-posta raporu ile önemli bir şeyi kaçırmayın.",
    "feat6_icon": "✍️", "feat6_title": "Basın bülteni üreteci",     "feat6_desc": "Yapay zeka desteğiyle profesyonel basın bültenleri ve sosyal medya gönderi başlıkları oluşturun.",
    "how_title": "Nasıl çalışır?",
    "how_sub":   "3 basit adımda medya izlemeye başlayın",
    "step1_title": "Anahtar kelimeleri ekleyin",       "step1_desc": "Kurum adınızı, yöneticilerinizin adlarını, izlemek istediğiniz konuları girin. Eş anlamlılar ve kısaltmalar da eklenebilir.",
    "step2_title": "Ajan otomatik arama yapar",        "step2_desc": "Her 15 dakikada bir 300+ kaynağı tarar: haber portalları, Telegram kanalları, Facebook, Instagram, YouTube.",
    "step3_title": "Sonuçları takip edin",             "step3_desc": "Panelde tüm haberleri görün, Telegram'a bildirim alın. Olumsuz haberlere zamanında tepki verin.",
    "sent_title": "Duygu analizi",
    "sent_sub":   "Yapay zeka her haberi otomatik olarak değerlendirir",
    "sent1_icon": "😊", "sent1_title": "Pozitif",  "sent1_desc": "Kurumunuz hakkında olumlu haberler işaretlenir ve paylaşılmaya hazır hale getirilir.",
    "sent2_icon": "😐", "sent2_title": "Nötr",     "sent2_desc": "Bilgilendirici haberler bu kategoride yer alır. Durum değerlendirmesi yapılabilir.",
    "sent3_icon": "😟", "sent3_title": "Negatif",  "sent3_desc": "Olumsuz haberler özellikle işaretlenir ve anlık Telegram bildirimi gönderilir.",
    "price_label":  "Fiyatlar",
    "price_title":  "Basit ve şeffaf fiyatlar",
    "price_sub":    "Kurumunuzun ihtiyacına uygun planı seçin. Her plan aylık ödemeyle, taahhütsüzdür.",
    "plan_period":  "/ay",
    "plan_btn":     "Demo iste",
    "plan_popular": "En çok seçilen",
    "plan1_name": "Ücretsiz",
    "plan1_desc": "Platformu tanımak, küçük kurumlar için başlangıç paketi.",
    "plan1_f1": "1 anahtar kelime izleme", "plan1_f2": "50+ haber kaynağı",
    "plan1_f3": "Son 24 saat haberleri", "plan1_f4": "AI duygu analizi",
    "plan1_f5": "Telegram bildirimi", "plan1_f6": "PDF/Excel raporu", "plan1_f7": "Çoklu anahtar kelime",
    "plan2_name": "Temel",
    "plan2_desc": "Orta ölçekli kurumlar için tam işlevsel medya izleme.",
    "plan2_f1": "10 anahtar kelime izleme", "plan2_f2": "300+ haber kaynağı",
    "plan2_f3": "Son 30 günlük arşiv", "plan2_f4": "AI duygu analizi",
    "plan2_f5": "Telegram bildirimi", "plan2_f6": "PDF/Excel raporu", "plan2_f7": "Haftalık e-posta raporu",
    "plan3_name": "Pro",
    "plan3_desc": "Büyük kurumlar ve medya ajansları için kapsamlı çözüm.",
    "plan3_f1": "Sınırsız anahtar kelime", "plan3_f2": "300+ haber kaynağı",
    "plan3_f3": "Tam arşiv erişimi", "plan3_f4": "Öncelikli AI analizi",
    "plan3_f5": "Çoklu kullanıcı", "plan3_f6": "API erişimi", "plan3_f7": "Özel raporlama",
    "cta_title": "Medya izlemeye bugün başlayın",
    "cta_sub":   "Demo talep edin, ekibimiz size özel sunum yapsın.",
    "cta_btn":   "🎯 Demo iste",
    "footer_desc": "Azerbaycan kurumları için geliştirilmiş yapay zeka destekli medya izleme platformu.",
    "footer_copy": "© 2025 MediaPulse. Tüm hakları saklıdır.",
    "nav_features":   "Özellikler",
    "nav_how":        "Nasıl çalışır",
    "nav_demo":       "Demo iste",
    "nav_login":      "Giriş yap",
    "hero_btn_login": "Sisteme giriş yap",
    "hero_btn_demo":  "🎯 Canlı demo gör",
    "feat_label":  "Platform özellikleri",
    "how_label":   "Adım adım",
    "sent_label":  "AI Analizi",
    "nav_dashboard_icon":   "📊", "nav_dashboard_label":   "Panel",
    "nav_press_icon":       "📝", "nav_press_label":       "Basın bülteni", "nav_press_show": "1",
    "nav_posttitles_icon":  "✍️", "nav_posttitles_label":  "Gönderi başlıkları", "nav_posttitles_show": "1",
    "nav_keywords_icon":    "🔑", "nav_keywords_label":    "Anahtar kelimeler",
}

count = 0
for key, value in TR.items():
    obj, created = LandingContent.objects.get_or_create(key=key, lang='tr')
    if created or obj.value != value:
        obj.value = value
        obj.save()
        count += 1

print(f"TR məzmunu əlavə edildi: {count} dəyər")

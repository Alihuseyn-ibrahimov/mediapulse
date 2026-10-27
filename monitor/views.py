from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import datetime, json, os
from .models import Organization, NewsResult, Keyword, KeywordAlias, LandingContent, DemoRequest, TvClip

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_AGENT_PYTHON = "/opt/pr-agent/bin/python3"
LANDING_ADMIN_CODE = os.environ.get("LANDING_ADMIN_CODE", "dev-admin-code")  # admin paneli giriş kodu (.env-dən)
TV_CLIP_INGEST_SECRET = os.environ.get("TV_CLIP_INGEST_SECRET", "dev-ingest-secret")  # Hetzner watcher.py -> Django
N8N_WEBHOOK_SECRET     = os.environ.get("N8N_WEBHOOK_SECRET", "dev-n8n-secret")        # Django <-> n8n paylaşılan açar
N8N_DECISION_WEBHOOK_URL = "https://n8n.mediapulse.az/webhook/tv-clip-web-decision"
TV_CLIP_ORG_SLUG = os.environ.get("TV_CLIP_ORG_SLUG", "eesmn")  # TV klipləri hansı təşkilata bağlanır

def _gemini(prompt):
    import subprocess, json, tempfile, os
    script = f"""
import warnings, sys
warnings.filterwarnings("ignore")
try:
    import google.generativeai as genai
    import json as _json
    prompt_file = sys.argv[1]
    with open(prompt_file, encoding='utf-8') as f:
        prompt_text = f.read()
    genai.configure(api_key={json.dumps(GEMINI_API_KEY)})
    model = genai.GenerativeModel("gemini-2.5-flash")
    result = model.generate_content(prompt_text)
    sys.stdout.buffer.write(result.text.encode('utf-8'))
except Exception as e:
    print("XETA:" + str(e), file=sys.stderr)
    sys.exit(1)
"""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as pf:
            pf.write(prompt)
            prompt_path = pf.name
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as sf:
            sf.write(script)
            script_path = sf.name
        r = subprocess.run(
            [_AGENT_PYTHON, script_path, prompt_path],
            capture_output=True, timeout=90
        )
        os.unlink(prompt_path)
        os.unlink(script_path)
        if r.returncode != 0:
            return f"Xəta: {r.stderr.decode('utf-8', errors='replace')[:400]}"
        return r.stdout.decode('utf-8', errors='replace').strip()
    except Exception as e:
        return f"Xəta: {e}"


LANDING_DEFAULTS = {
    "hero_badge":         "🇦🇿  Azərbaycan üçün",
    "hero_title":         "Media xəbərlərinizi",
    "hero_title_hl":      "real vaxtda izləyin",
    "hero_desc":          "Qurumunuz haqqında onlayn mediada, sosial şəbəkələrdə və Telegram kanallarında nə yazıldığını anında bilin. Süni intellekt hər xəbəri analiz edir.",
    "stat1_num": "300+",  "stat1_lbl": "İzlənilən xəbər mənbəsi",
    "stat2_num": "15 dəq","stat2_lbl": "Yeniləmə intervalı",
    "stat3_num": "AI",    "stat3_lbl": "Sentiment analizi",
    "stat4_num": "24/7",  "stat4_lbl": "Fasiləsiz monitorinq",
    "feat_title": "Nə təklif edirik?",
    "feat_sub":   "MediaPulse — dövlət qurumları və şirkətlər üçün hazırlanmış media monitorinq platforması",
    "feat1_icon": "📰", "feat1_title": "Geniş mənbə əhatəsi",      "feat1_desc": "Azərbaycanın 300-dən çox xəbər portalı, Telegram kanalları, Facebook və Instagram səhifələri eyni anda izlənilir.",
    "feat2_icon": "🤖", "feat2_title": "Süni intellekt analizi",    "feat2_desc": "Gemini AI hər xəbəri oxuyub mənfi və ya müsbət olaraq qiymətləndirir. İnsan faktoru olmadan, dəqiq nəticə.",
    "feat3_icon": "🔔", "feat3_title": "Ani Telegram bildirişi",    "feat3_desc": "Yeni xəbər tapılan kimi Telegram-a bildiriş göndərilir. Mənfi xəbərlər xüsusi işarələnir.",
    "feat4_icon": "🔑", "feat4_title": "Açar söz sistemi",          "feat4_desc": "İstədiyiniz açar sözü və onun sinonimlərini əlavə edin. Agent avtomatik bütün mənbələrdə axtarış aparır.",
    "feat5_icon": "📊", "feat5_title": "İnteraktiv dashboard",      "feat5_desc": "Sentiment bölgüsü, günlük xəbər axını, açar söz üzrə statistika — hamısı bir ekranda.",
    "feat6_icon": "🔒", "feat6_title": "Təhlükəsiz və şəxsi",       "feat6_desc": "Hər müştəri öz məlumatlarını görür. HTTPS şifrələməsi, Cloudflare qoruması.",
    "how_title": "Necə işləyir?",
    "how_sub":   "3 sadə addımda media monitorinqə başlayın",
    "step1_title": "Açar sözləri əlavə edin",        "step1_desc": "Qurum adınızı, rəhbərlərinizin adlarını, izləmək istədiyiniz mövzuları daxil edin. Sinonim və qısaltmalar da əlavə edilə bilər.",
    "step2_title": "Agent avtomatik axtarış aparır",  "step2_desc": "Hər 15 dəqiqədən bir 300+ mənbəni skan edir: xəbər portalları, Telegram kanalları, Facebook, Instagram, YouTube.",
    "step3_title": "Nəticələri izləyin",              "step3_desc": "Dashboard-da bütün xəbərləri görün, Telegram-a bildiriş alın. Mənfi xəbərlərə vaxtında reaksiya verin.",
    "sent_title": "Sentiment analizi",
    "sent_sub":   "Süni intellekt hər xəbəri avtomatik qiymətləndirir",
    "sent_menfi_emoji":   "🔴", "sent_menfi_title":   "Mənfi",   "sent_menfi_desc":   "Şikayət, tənqid, hüquq pozuntusu, müavinət problemi, etiraz xəbərləri",
    "sent_musbet_emoji":  "🟢", "sent_musbet_title":  "Müsbət",  "sent_musbet_desc":  "Nailiyyət, islahat, yeni xidmət, ödəniş artımı, andiçmə, saziş xəbərləri",
    "cta_title": "Hər xəbəri vaxtında bilin",
    "cta_desc":  "Qurum reputasiyanızı real vaxtda izləyin",
    "footer_text": "MediaPulse — Media Monitorinq Platforması &nbsp;|&nbsp; mediapulse.az &nbsp;|&nbsp; © 2026",
    # Naviqasiya menyusu
    "nav_dashboard_icon":  "📊", "nav_dashboard_label":  "Dashboard",
    "nav_press_icon":      "📝", "nav_press_label":      "Press-reliz",     "nav_press_show":      "1",
    "nav_posttitles_icon": "✍️", "nav_posttitles_label": "Post başlıqları", "nav_posttitles_show": "1",
    "nav_keywords_icon":   "🔑", "nav_keywords_label":   "Açar sözlər",
    # Landing navbar + hero buttons
    "nav_features":   "Xüsusiyyətlər",
    "nav_how":        "Necə işləyir",
    "nav_demo":       "Demo istə",
    "nav_login":      "Daxil ol",
    "hero_btn_login": "Sistemə daxil ol",
    "hero_btn_demo":  "🎯 Canlı demo gör",
    # Section labels
    "feat_label":  "Platforma imkanları",
    "how_label":   "Addım-addım",
    "sent_label":  "AI Analizi",
    # Pricing
    "show_pricing": "1",
    "price_label":  "Tariflər",
    "price_title":  "Sadə və şəffaf qiymətlər",
    "price_sub":    "Qurumunuzun ehtiyacına uyğun plan seçin. Hər plan aylıq ödənişlə, öhdəliksizdir.",
    "plan_period":  "/ay",
    "plan_btn":     "Demo istə",
    "plan_popular": "Ən çox seçilən",
    "plan1_name": "Pulsuz",
    "plan1_desc": "Platformanı tanımaq, kiçik qurumlar üçün başlanğıc paketi.",
    "plan1_f1": "1 açar söz izləmə", "plan1_f2": "50+ xəbər mənbəsi",
    "plan1_f3": "Son 24 saat xəbərləri", "plan1_f4": "AI sentiment analizi",
    "plan1_f5": "Telegram bildirişi", "plan1_f6": "PDF/Excel hesabat", "plan1_f7": "Çoxlu açar söz",
    "plan2_name": "Əsas",
    "plan2_desc": "Orta ölçülü qurumlar üçün tam funksional media monitorinq.",
    "plan2_f1": "10 açar söz izləmə", "plan2_f2": "300+ xəbər mənbəsi",
    "plan2_f3": "Son 30 günlük arxiv", "plan2_f4": "AI sentiment analizi",
    "plan2_f5": "Telegram bildirişi", "plan2_f6": "Həftəlik PDF hesabat", "plan2_f7": "Fərdi mənbə əlavəsi",
    "plan3_desc": "Böyük qurumlar və nazirliklər üçün tam həll, fərdi dəstəklə.",
    "plan3_f1": "Limitsiz açar söz", "plan3_f2": "300+ xəbər mənbəsi",
    "plan3_f3": "Tam arxiv (6 ay)", "plan3_f4": "AI sentiment analizi",
    "plan3_f5": "Telegram + WhatsApp bildiriş", "plan3_f6": "Aylıq PDF/Excel hesabat", "plan3_f7": "Fərdi mənbə əlavəsi",
    # Demo form
    "demo_label":     "Pulsuz demo",
    "demo_title":     "Demo istəyin",
    "demo_sub":       "Platformamızı canlı görmək üçün məlumatlarınızı göndərin — 24 saat ərzində sizinlə əlaqə saxlayacağıq.",
    "demo_plan_badge":"Seçilmiş plan",
    "demo_name":      "Ad Soyad",
    "demo_company":   "Şirkət / Qurum adı",
    "demo_contact":   "Telefon və ya E-poçt",
    "demo_note":      "Qeyd (isteğe bağlı)",
    "demo_success":   "Müraciətiniz qəbul olundu! Tezliklə sizinlə əlaqə saxlayacağıq.",
    # CTA
    "cta_btn": "Sistemə daxil ol",
    # Canlı nümunə lenti (hero altında, avtomatik dövr edən kartlar)
    "radar_label": "Canlı nümunə",
    "radar_title": "AI bunu belə qiymətləndirir",
    "radar_sub":   "Mediada gündəlik rast gəlinən xəbər tiplərinin illüstrativ nümunələri",
    "radar1_text": "Yeni sosial dəstək proqramı təqdim olundu",
    "radar2_text": "Xidmət göstərilməsində gecikmə barədə şikayət",
    "radar3_text": "Əməkhaqqı artımı rəsmi elan edildi",
    "radar4_text": "İnfrastruktur nöqsanı ictimaiyyətə açıqlandı",
    "radar5_text": "Yeni tərəfdaşlıq sazişi imzalandı",
    "radar6_text": "İstifadəçi məlumatlarının qorunması ilə bağlı iddia",
    # FAQ bölməsi
    "faq_label": "Suallar",
    "faq_title": "Tez-tez verilən suallar",
    "faq_sub":   "Aydın olmayan nəsə var? Aşağıda cavabını tapa bilərsiniz",
    "faq1_q": "Sistemin qurulması nə qədər vaxt aparır?",
    "faq1_a": "Demo müraciətindən sonra hesabınız 24 saat ərzində hazırlanır. Açar sözləri əlavə etdikdən dərhal sonra monitorinq avtomatik başlayır.",
    "faq2_q": "Hansı mənbələr izlənilir?",
    "faq2_a": "300-dən çox xəbər portalı, Telegram kanalları, Facebook, Instagram və YouTube səhifələri eyni anda skan olunur. İstəyə görə fərdi mənbə də əlavə edilə bilər.",
    "faq3_q": "Sentiment analizi necə aparılır?",
    "faq3_a": "Hər xəbər süni intellekt (Gemini AI) tərəfindən oxunur və məzmununa görə müsbət və ya mənfi olaraq qiymətləndirilir. İnsan müdaxiləsi tələb olunmur.",
    "faq4_q": "Bildirişləri necə alıram?",
    "faq4_a": "Telegram botunu qoşduqdan sonra yeni xəbər tapılan kimi anında bildiriş gəlir. Mənfi xəbərlər üçün ayrıca vurğulanmış format istifadə olunur.",
    "faq5_q": "Ödəniş və müqavilə şərtləri necədir?",
    "faq5_a": "Bütün planlar aylıq ödənişlidir, uzunmüddətli öhdəlik tələb olunmur. İstənilən vaxt planınızı dəyişə və ya ləğv edə bilərsiniz.",
}


def _get_landing_content(lang='az'):
    db_vals = {obj.key: obj.value for obj in LandingContent.objects.filter(lang=lang)}
    if lang != 'az':
        az_vals = {obj.key: obj.value for obj in LandingContent.objects.filter(lang='az')}
        merged = dict(LANDING_DEFAULTS)
        merged.update(az_vals)
        merged.update(db_vals)
        return merged
    result = dict(LANDING_DEFAULTS)
    result.update(db_vals)
    return result

SUPPORTED_LANGS = ['az', 'ru', 'en', 'es', 'tr']
LANG_LABELS = {'az': '🇦🇿 AZ', 'ru': '🇷🇺 RU', 'en': '🇬🇧 EN', 'es': '🇪🇸 ES', 'tr': '🇹🇷 TR'}

def landing(request):
    lang = request.GET.get('lang') or request.session.get('lang', 'az')
    if lang not in SUPPORTED_LANGS:
        lang = 'az'
    request.session['lang'] = lang
    ctx = _get_landing_content(lang)
    return render(request, "landing.html", {"lc": ctx, "lang": lang, "lang_labels": LANG_LABELS})


def grammar_check(request):
    """Landing məzmununu Gemini ilə Azərbaycan dili normalarına görə yoxlayır."""
    if not request.session.get("la_auth"):
        return redirect("landing_admin")

    # Düzəliş tətbiqi
    if request.method == "POST" and request.POST.get("action") == "apply":
        saved = json.loads(request.session.get("grammar_result", "{}"))
        for key in request.POST.getlist("apply_keys"):
            if key in saved:
                obj, _ = LandingContent.objects.get_or_create(key=key)
                obj.value = saved[key]["corrected"]
                obj.save()
        request.session.pop("grammar_result", None)
        return redirect("landing_admin")

    # Nəticə artıq hazırdırsa göstər
    if "grammar_result" in request.session:
        corrections = json.loads(request.session["grammar_result"])
        total = request.session.get("grammar_total", 0)
        request.session.pop("grammar_result", None)
        request.session.pop("grammar_total", None)
        request.session.pop("grammar_done", None)
        return render(request, "monitor/grammar_check.html", {
            "corrections": corrections,
            "total_checked": total,
        })

    # Yeni yoxlama başlat — arxa planda thread ilə
    if request.GET.get("run") == "1":
        import threading, re as _re

        def _run(session_key):
            from django.contrib.sessions.backends.db import SessionStore
            s = SessionStore(session_key=session_key)
            lc = _get_landing_content()
            skip = {k for k in lc if any(x in k for x in ["icon", "emoji", "num", "show", "slug", "url"])}
            texts = {k: v for k, v in lc.items() if k not in skip and v and len(v) > 10}
            prompt = (
                "Sən Azərbaycan dili ekspertisən. Aşağıdakı mətnləri Azərbaycan ədəbi dili normalarına görə yoxla.\n"
                "Yalnız səhvli mətnlər üçün düzəldilmiş versiya ver. Səhv yoxdursa — həmin key-i daxil etmə.\n"
                "YALNIZ JSON formatında cavab ver:\n"
                '{"key": {"original": "...", "corrected": "...", "note": "qısa izah"}, ...}\n\n'
                "Mətnlər:\n" +
                "\n".join(f'"{k}": "{v}"' for k, v in list(texts.items())[:40])
            )
            raw = _gemini(prompt)
            corrections = {}
            try:
                m = _re.search(r'\{.*\}', raw, _re.DOTALL)
                if m:
                    corrections = json.loads(m.group())
            except Exception:
                pass
            s["grammar_result"] = json.dumps(corrections)
            s["grammar_total"] = len(texts)
            s["grammar_done"] = True
            s.save()

        t = threading.Thread(target=_run, args=(request.session.session_key,), daemon=True)
        t.start()
        return render(request, "monitor/grammar_check.html", {"loading": True})

    # Yükləmə vəziyyətini yoxla (polling)
    if request.GET.get("poll") == "1":
        from django.contrib.sessions.backends.db import SessionStore
        s = SessionStore(session_key=request.session.session_key)
        done = s.get("grammar_done", False)
        return JsonResponse({"done": done})

    # İlk açılış — "Başla" səhifəsi göstər
    return render(request, "monitor/grammar_check.html", {"start": True})


def landing_admin(request):
    # Giriş yoxlaması — session əsaslı, Django auth-dan müstəqil
    if request.method == "POST" and request.POST.get("action") == "login":
        from .throttle import is_locked, register_failure, clear as clear_throttle
        if is_locked(request, "ladmin"):
            return render(request, "monitor/landing_admin_login.html",
                          {"error": "Çox sayda uğursuz cəhd. 15 dəqiqə sonra yenidən yoxlayın."})
        if request.POST.get("code", "") == LANDING_ADMIN_CODE:
            clear_throttle(request, "ladmin")
            request.session["la_auth"] = True
        else:
            register_failure(request, "ladmin")
            return render(request, "monitor/landing_admin_login.html", {"error": "Kod yanlışdır"})
        return redirect("landing_admin")

    if not request.session.get("la_auth"):
        return render(request, "monitor/landing_admin_login.html", {})

    if request.method == "POST" and request.POST.get("action") == "logout":
        request.session.pop("la_auth", None)
        return redirect("landing_admin")

    admin_lang = request.GET.get("lang", "az")
    if admin_lang not in SUPPORTED_LANGS:
        admin_lang = "az"

    if request.method == "POST":
        key   = request.POST.get("key", "").strip()
        value = request.POST.get("value", "")
        plang = request.POST.get("lang", "az")
        if plang not in SUPPORTED_LANGS:
            plang = "az"
        if key and key in LANDING_DEFAULTS:
            obj, _ = LandingContent.objects.get_or_create(key=key, lang=plang)
            obj.value = value
            obj.save()
        return redirect(f"{request.path}?lang={plang}")

    current = _get_landing_content(admin_lang)
    _TEXTAREA_KEYS = {
        "hero_desc", "feat_sub", "how_sub", "sent_sub", "cta_desc", "footer_text",
        "feat1_desc", "feat2_desc", "feat3_desc", "feat4_desc", "feat5_desc", "feat6_desc",
        "step1_desc", "step2_desc", "step3_desc",
        "sent_menfi_desc", "sent_musbet_desc",
        "faq1_a", "faq2_a", "faq3_a", "faq4_a", "faq5_a",
    }

    def _field(key, label):
        return {"key": key, "label": label, "value": current.get(key, ""), "textarea": key in _TEXTAREA_KEYS, "lang": admin_lang}

    sections = [
        ("Hero bölməsi", [
            _field("hero_badge",    "Badge mətni"),
            _field("hero_title",    "Başlıq (birinci sətir)"),
            _field("hero_title_hl", "Başlıq (vurğulanmış hissə)"),
            _field("hero_desc",     "Açıqlama mətni"),
        ]),
        ("Statistika", [
            _field("stat1_num", "Stat 1 — rəqəm"), _field("stat1_lbl", "Stat 1 — etiket"),
            _field("stat2_num", "Stat 2 — rəqəm"), _field("stat2_lbl", "Stat 2 — etiket"),
            _field("stat3_num", "Stat 3 — rəqəm"), _field("stat3_lbl", "Stat 3 — etiket"),
            _field("stat4_num", "Stat 4 — rəqəm"), _field("stat4_lbl", "Stat 4 — etiket"),
        ]),
        ("Xidmətlər bölməsi", [
            _field("feat_title", "Bölmə başlığı"), _field("feat_sub", "Alt başlıq"),
            _field("feat1_icon", "Kart 1 — emoji"), _field("feat1_title", "Kart 1 — ad"), _field("feat1_desc", "Kart 1 — mətn"),
            _field("feat2_icon", "Kart 2 — emoji"), _field("feat2_title", "Kart 2 — ad"), _field("feat2_desc", "Kart 2 — mətn"),
            _field("feat3_icon", "Kart 3 — emoji"), _field("feat3_title", "Kart 3 — ad"), _field("feat3_desc", "Kart 3 — mətn"),
            _field("feat4_icon", "Kart 4 — emoji"), _field("feat4_title", "Kart 4 — ad"), _field("feat4_desc", "Kart 4 — mətn"),
            _field("feat5_icon", "Kart 5 — emoji"), _field("feat5_title", "Kart 5 — ad"), _field("feat5_desc", "Kart 5 — mətn"),
            _field("feat6_icon", "Kart 6 — emoji"), _field("feat6_title", "Kart 6 — ad"), _field("feat6_desc", "Kart 6 — mətn"),
        ]),
        ("Necə işləyir", [
            _field("how_title", "Bölmə başlığı"), _field("how_sub", "Alt başlıq"),
            _field("step1_title", "Addım 1 — ad"), _field("step1_desc", "Addım 1 — mətn"),
            _field("step2_title", "Addım 2 — ad"), _field("step2_desc", "Addım 2 — mətn"),
            _field("step3_title", "Addım 3 — ad"), _field("step3_desc", "Addım 3 — mətn"),
        ]),
        ("Sentiment analizi bölməsi", [
            _field("sent_title", "Bölmə başlığı"), _field("sent_sub", "Alt başlıq"),
            _field("sent_menfi_emoji",   "Mənfi — emoji"),   _field("sent_menfi_title",   "Mənfi — ad"),   _field("sent_menfi_desc",   "Mənfi — mətn"),
            _field("sent_musbet_emoji",  "Müsbət — emoji"),  _field("sent_musbet_title",  "Müsbət — ad"),  _field("sent_musbet_desc",  "Müsbət — mətn"),
        ]),
        ("Tarif bölməsi", [
            _field("show_pricing", "Tarif bölməsini göstər? (1=bəli, 0=xeyr)"),
        ]),
        ("Canlı nümunə lenti", [
            _field("radar_label", "Bölmə etiketi"), _field("radar_title", "Bölmə başlığı"), _field("radar_sub", "Alt başlıq"),
            _field("radar1_text", "Nümunə 1 (müsbət)"), _field("radar2_text", "Nümunə 2 (mənfi)"),
            _field("radar3_text", "Nümunə 3 (müsbət)"), _field("radar4_text", "Nümunə 4 (mənfi)"),
            _field("radar5_text", "Nümunə 5 (müsbət)"), _field("radar6_text", "Nümunə 6 (mənfi)"),
        ]),
        ("Tez-tez verilən suallar", [
            _field("faq_label", "Bölmə etiketi"), _field("faq_title", "Bölmə başlığı"), _field("faq_sub", "Alt başlıq"),
            _field("faq1_q", "Sual 1"), _field("faq1_a", "Cavab 1"),
            _field("faq2_q", "Sual 2"), _field("faq2_a", "Cavab 2"),
            _field("faq3_q", "Sual 3"), _field("faq3_a", "Cavab 3"),
            _field("faq4_q", "Sual 4"), _field("faq4_a", "Cavab 4"),
            _field("faq5_q", "Sual 5"), _field("faq5_a", "Cavab 5"),
        ]),
        ("CTA və Footer", [
            _field("cta_title",   "CTA başlığı"),
            _field("cta_desc",    "CTA açıqlaması"),
            _field("footer_text", "Footer mətni"),
        ]),
        ("Naviqasiya menyusu", [
            _field("nav_dashboard_icon",  "Dashboard — emoji"),
            _field("nav_dashboard_label", "Dashboard — ad"),
            _field("nav_press_icon",      "Press-reliz — emoji"),
            _field("nav_press_label",     "Press-reliz — ad"),
            _field("nav_press_show",      "Press-reliz — göstər? (1=bəli, 0=xeyr)"),
            _field("nav_posttitles_icon",  "Post başlıqları — emoji"),
            _field("nav_posttitles_label", "Post başlıqları — ad"),
            _field("nav_posttitles_show",  "Post başlıqları — göstər? (1=bəli, 0=xeyr)"),
            _field("nav_keywords_icon",   "Açar sözlər — emoji"),
            _field("nav_keywords_label",  "Açar sözlər — ad"),
        ]),
    ]
    return render(request, "monitor/landing_admin.html", {
        "sections": sections,
        "admin_lang": admin_lang,
        "lang_labels": LANG_LABELS,
        "supported_langs": SUPPORTED_LANGS,
    })


@csrf_exempt
@require_POST
def tv_clip_ingest(request):
    """Hetzner tv-monitor (watcher.py) buraya yeni tapılan klipi qeydə alır."""
    if request.headers.get("X-Ingest-Secret") != TV_CLIP_INGEST_SECRET:
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    channel = data.get("channel", "").strip()
    keyword = data.get("keyword", "").strip()
    video_url = data.get("videoUrl", "").strip()
    if not (channel and keyword and video_url):
        return JsonResponse({"ok": False, "error": "channel/keyword/videoUrl tələb olunur"}, status=400)

    org_slug = data.get("orgSlug", "").strip() or TV_CLIP_ORG_SLUG
    org = Organization.objects.filter(slug=org_slug).first()

    title = data.get("title", "").strip()
    clip = TvClip.objects.create(
        organization=org,
        channel=channel,
        keyword=keyword,
        title=title,
        video_url=video_url,
    )

    # ── TV süjeti PR-monitorinq lentinə də düşür ─────────────────────
    # Eyni süjet iki dəfə gələ bilər: əvvəl parça klip, sonra tam (birləşdirilmiş)
    # versiya — hər ikisi eyni başlıqla. Belə halda yeni sətir yaratmır, mövcud
    # NewsResult-un linkini tam versiyaya yeniləyir (təkrar Telegram da getmir).
    if org and title:
        sentiment = (data.get("sentiment") or "").strip()
        if sentiment not in ("MÜSBƏT", "MƏNFİ"):
            sentiment = "MÜSBƏT"
        source = f"TV: {channel}"
        recent = timezone.now() - datetime.timedelta(hours=24)
        existing = NewsResult.objects.filter(
            organization=org, title=title, source=source, saved_at__gte=recent,
        ).first()
        if existing:
            existing.link = video_url
            existing.save(update_fields=["link"])
        else:
            NewsResult.objects.create(
                organization=org,
                keyword=keyword,
                title=title,
                summary=f"{channel} kanalında tapılan TV süjeti (avtomatik kəsilmiş klip).",
                link=video_url,
                source=source,
                sentiment=sentiment,
                saved_at=timezone.now(),
            )
            _tv_clip_telegram_alert(org, channel, keyword, title, video_url, sentiment)

    return JsonResponse({"ok": True, "id": clip.pk})


def _tv_clip_telegram_alert(org, channel, keyword, title, video_url, sentiment):
    """TV süjeti üçün PR-monitorinq botuna bildiriş — agent.py-nin
    _telegram_alert formatı ilə eyni vizual dildə, mənbə kimi TV kanalı."""
    if not TELEGRAM_TOKEN:
        return
    if sentiment == "MƏNFİ" and not org.notif_on_negative:
        return
    if sentiment == "MÜSBƏT" and not org.notif_on_positive:
        return
    from django.utils.html import escape as _esc
    emoji = {"MƏNFİ": "🔴", "MÜSBƏT": "🟢"}.get(sentiment, "🟡")
    _tg_send(
        f"{emoji} <b>PR XƏBƏRDARLİĞI</b> — 📺 TV\n\n"
        f"🔑 {_esc(keyword)}\n"
        f"📌 {_esc(title)}\n"
        f"📺 {_esc(channel)}\n"
        f'🔗 <a href="{video_url}">Süjetə bax</a>'
    )


@login_required
@require_POST
def tv_clip_decide(request, pk):
    """Müştəri dashboard-undan Təsdiqlə/Rədd et — n8n-in web-decision webhook-unu çağırır."""
    org = _get_org(request.user)
    try:
        role = request.user.membership.role
    except Exception:
        role = None
    if not org or role != "admin":
        return JsonResponse({"ok": False, "error": "icazə yoxdur"}, status=403)

    action = request.POST.get("action")
    if action not in ("approve", "reject"):
        return JsonResponse({"ok": False, "error": "yanlış action"}, status=400)

    clip = get_object_or_404(TvClip, pk=pk, organization=org)
    clip.status = "approved" if action == "approve" else "rejected"
    clip.decided_by = request.user if request.user.is_authenticated else None
    clip.decided_at = timezone.now()
    clip.save()

    if action == "approve":
        import urllib.request
        payload = json.dumps({
            "clip_id": clip.pk,
            "action": action,
            "channel": clip.channel,
            "keyword": clip.keyword,
            "title": clip.title,
            "video_url": clip.video_url,
        }).encode()
        req = urllib.request.Request(
            N8N_DECISION_WEBHOOK_URL, data=payload,
            headers={"Content-Type": "application/json", "X-Webhook-Secret": N8N_WEBHOOK_SECRET},
        )
        try:
            urllib.request.urlopen(req, timeout=15)
        except Exception:
            pass

    from django.urls import reverse
    return redirect(reverse("dashboard") + "#tv")


@csrf_exempt
@require_POST
def tv_clip_upload_result(request):
    """n8n-in geri-çağırışı — yükləmə uğurlu/uğursuz olduqda status yenilənir."""
    if request.headers.get("X-Webhook-Secret") != N8N_WEBHOOK_SECRET:
        return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "invalid json"}, status=400)

    try:
        clip = TvClip.objects.get(pk=data.get("clip_id"))
    except (TvClip.DoesNotExist, TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "clip tapılmadı"}, status=404)

    clip.status = data.get("status") if data.get("status") in ("uploaded", "rejected") else "failed"
    clip.youtube_video_id = data.get("youtube_video_id", "")
    clip.n8n_execution_id = data.get("n8n_execution_id", "")
    clip.save()
    return JsonResponse({"ok": True})


def _get_org(user):
    try:
        return user.membership.organization
    except Exception:
        return None


_TV_STATUS_LABEL = {
    "pending":  "Gözləyir",
    "approved": "Təsdiqləndi",
    "rejected": "Rədd edildi",
    "uploaded": "YouTube-a yükləndi",
    "failed":   "Xəta",
}


@login_required
def notifications_feed(request):
    """Dashboard bildiriş zəngi üçün — son xəbərləri JSON qaytarır.
    ?type=pr (default) → PR monitorinq xəbərləri (NewsResult).
    ?type=tv            → TV/YouTube monitorinq klipləri (TvClip).
    Frontend hansının 'oxunmamış' olduğunu localStorage-dakı son-baxış vaxtı
    ilə müqayisə edərək müəyyən edir."""
    org = _get_org(request.user)
    if not org:
        return JsonResponse({"ok": False, "items": []}, status=403)
    since = timezone.now() - datetime.timedelta(days=7)
    feed_type = request.GET.get("type", "pr")

    if feed_type == "tv":
        qs = (TvClip.objects
              .filter(organization=org, created_at__gte=since)
              .order_by("-created_at")[:30])
        items = [{
            "id":       c.id,
            "title":    (c.title or f"{c.channel} — {c.keyword}")[:180],
            "status":   c.status,
            "status_label": _TV_STATUS_LABEL.get(c.status, c.status),
            "channel":  c.channel,
            "keyword":  c.keyword,
            "link":     c.video_url,
            "ts":       c.created_at.isoformat(),
        } for c in qs]
    else:
        qs = (NewsResult.objects
              .filter(organization=org, saved_at__gte=since)
              .order_by("-saved_at")[:30])
        items = [{
            "id":        r.id,
            "title":     r.title[:180],
            "sentiment": r.sentiment,
            "source":    r.source,
            "keyword":   r.keyword,
            "link":      r.link,
            "ts":        r.saved_at.isoformat(),
        } for r in qs]

    return JsonResponse({
        "ok": True,
        "type": feed_type,
        "items": items,
        "server_now": timezone.now().isoformat(),
    })


@login_required
def dashboard(request):
    org = _get_org(request.user)
    if not org:
        return render(request, "monitor/no_org.html")

    days = int(request.GET.get("days", 1))
    sentiment      = request.GET.get("sentiment", "")
    search         = request.GET.get("search", "").strip()
    date_from      = request.GET.get("date_from", "").strip()
    date_to        = request.GET.get("date_to", "").strip()
    keyword_filter = request.GET.get("keyword_filter", "").strip()
    source_filter  = request.GET.get("source_filter", "").strip()   # platforma: facebook/youtube/telegram/news

    if days == 0 and (date_from or date_to):
        qs = NewsResult.objects.filter(organization=org)
    else:
        cutoff = timezone.now() - datetime.timedelta(days=days)
        qs = NewsResult.objects.filter(organization=org, saved_at__gte=cutoff)

    if date_from:
        qs = qs.filter(saved_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(saved_at__date__lte=date_to)
    if sentiment:
        qs = qs.filter(sentiment=sentiment)
    if search:
        qs = qs.filter(title__icontains=search) | qs.filter(source__icontains=search)
    if keyword_filter:
        qs = qs.filter(keyword__icontains=keyword_filter)
    # Platforma (sosial şəbəkə) filtri
    if source_filter == "facebook":
        qs = qs.filter(source__icontains="facebook")
    elif source_filter == "youtube":
        qs = qs.filter(source__icontains="youtube")
    elif source_filter == "telegram":
        qs = qs.filter(source__icontains="t.me")
    elif source_filter == "tv":
        qs = qs.filter(source__istartswith="TV:")
    elif source_filter == "news":
        qs = (qs.exclude(source__icontains="facebook")
                .exclude(source__icontains="youtube")
                .exclude(source__icontains="t.me")
                .exclude(source__istartswith="TV:"))

    results = list(qs.order_by("sentiment", "-saved_at")[:200])

    n_menfi  = qs.filter(sentiment="MƏNFİ").count()
    n_musbet = qs.filter(sentiment="MÜSBƏT").count()
    n_total = qs.count()
    counts = {
        "total":  n_total,
        "menfi":  n_menfi,
        "musbet": n_musbet,
        "nsi":    _calc_nsi(n_musbet, n_menfi, n_total),
    }

    # Günlük xəbər axını (yalnız üst metrik kartların sparkline-ları üçün —
    # tam qrafik/müqayisə/mənbə reytinqi bölmələri "Statistika" səhifəsinə köçüb)
    from django.db.models.functions import TruncDate
    from django.db.models import Count
    daily_qs = (qs.annotate(date=TruncDate("saved_at"))
                  .values("date", "sentiment")
                  .annotate(say=Count("id"))
                  .order_by("date"))

    daily_dates = sorted(set(str(r["date"]) for r in daily_qs))
    daily_menfi  = {str(r["date"]): r["say"] for r in daily_qs if r["sentiment"] == "MƏNFİ"}
    daily_musbet = {str(r["date"]): r["say"] for r in daily_qs if r["sentiment"] == "MÜSBƏT"}

    import json as _json
    chart_data = _json.dumps({
        "daily": {
            "labels": daily_dates,
            "menfi":  [daily_menfi.get(d, 0)  for d in daily_dates],
            "musbet": [daily_musbet.get(d, 0) for d in daily_dates],
        },
    })

    has_keywords = org.keywords.filter(is_active=True).exists()
    has_news     = NewsResult.objects.filter(organization=org).exists()
    has_notif    = org.notif_on_negative or org.notif_on_positive or org.notif_daily_summary

    org_keywords = list(org.keywords.filter(is_active=True).values_list("word", flat=True))

    # Competitor keywords for sidebar comparison
    competitor_kws = list(org.keywords.filter(is_active=True, is_competitor=True).values_list("word", flat=True))
    own_kws = list(org.keywords.filter(is_active=True, is_competitor=False).values_list("word", flat=True))

    try:
        is_org_admin = request.user.membership.role == "admin"
    except Exception:
        is_org_admin = False

    return render(request, "monitor/dashboard.html", {
        "org": org,
        "results": results,
        "counts": counts,
        "days": days,
        "selected_sentiment": sentiment,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "keyword_filter": keyword_filter,
        "source_filter": source_filter,
        "org_keywords": org_keywords,
        "competitor_kws": competitor_kws,
        "own_kws": own_kws,
        "chart_data": chart_data,
        "hours_range": range(24),
        "show_onboarding": not org.onboarding_done,
        "ob_keywords": has_keywords,
        "ob_news":     has_news,
        "ob_notif":    has_notif,
        "tv_clips": TvClip.objects.filter(organization=org)[:30],
        "tv_pending_count": TvClip.objects.filter(organization=org, status="pending").count(),
        "is_org_admin": is_org_admin,
    })


@login_required
def keywords_view(request):
    org = _get_org(request.user)
    if not org:
        return redirect("dashboard")

    if request.user.membership.role != "admin":
        return redirect("dashboard")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            word = request.POST.get("word", "").strip()
            if word:
                Keyword.objects.get_or_create(organization=org, word=word)
        elif action == "delete":
            kw_id = request.POST.get("kw_id")
            Keyword.objects.filter(id=kw_id, organization=org).delete()
        elif action == "toggle":
            kw_id = request.POST.get("kw_id")
            kw = get_object_or_404(Keyword, id=kw_id, organization=org)
            kw.is_active = not kw.is_active
            kw.save()
        elif action == "toggle_competitor":
            kw_id = request.POST.get("kw_id")
            kw = get_object_or_404(Keyword, id=kw_id, organization=org)
            kw.is_competitor = not kw.is_competitor
            kw.save()
        elif action == "add_alias":
            kw_id   = request.POST.get("kw_id")
            alias_w = request.POST.get("alias_word", "").strip()
            if alias_w:
                kw = get_object_or_404(Keyword, id=kw_id, organization=org)
                KeywordAlias.objects.get_or_create(keyword=kw, word=alias_w)
        elif action == "delete_alias":
            alias_id = request.POST.get("alias_id")
            KeywordAlias.objects.filter(id=alias_id, keyword__organization=org).delete()
        return redirect("keywords")

    keywords = Keyword.objects.filter(organization=org).prefetch_related("aliases").order_by("-created_at")
    return render(request, "monitor/keywords.html", {"org": org, "keywords": keywords})


@login_required
@require_POST
def keyword_add_ajax(request):
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return JsonResponse({"ok": False})
    word = request.POST.get("word", "").strip()
    if word:
        Keyword.objects.get_or_create(organization=org, word=word)
        return JsonResponse({"ok": True})
    return JsonResponse({"ok": False, "error": "boş söz"})


@login_required
def keyword_suggest(request):
    import json as _json
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return JsonResponse({"error": "icazə yoxdur"}, status=403)

    existing = list(Keyword.objects.filter(organization=org).values_list("word", flat=True))
    recent_titles = list(
        NewsResult.objects.filter(organization=org)
        .order_by("-saved_at")[:30]
        .values_list("title", flat=True)
    )

    prompt = f"""Sən media monitorinq mütəxəssisisisniz.
Qurum adı: {org.name}
Mövcud açar sözlər: {', '.join(existing) if existing else 'yoxdur'}
Son 30 xəbər başlığı:
{chr(10).join('- ' + t for t in recent_titles[:20])}

Yuxarıdakı məlumatlara əsasən bu qurum üçün media izləmədə faydalı ola biləcək YENİ açar söz tövsiyəsi ver.
Mövcud sözləri təkrarlama.
Cavabı YALNIZ JSON massiv formatında ver, başqa heç nə yazma:
["söz1", "söz2", "söz3", "söz4", "söz5"]"""

    raw = _gemini(prompt)
    try:
        # JSON massivi tap
        start = raw.find("[")
        end = raw.rfind("]") + 1
        suggestions = _json.loads(raw[start:end])
        suggestions = [s for s in suggestions if s not in existing][:8]
    except Exception:
        suggestions = []

    return JsonResponse({"suggestions": suggestions})


@login_required
def news_edit(request, pk):
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return redirect("dashboard")

    news = get_object_or_404(NewsResult, pk=pk, organization=org)
    if request.method == "POST":
        news.sentiment = request.POST.get("sentiment", news.sentiment)
        news.summary   = request.POST.get("summary", news.summary)
        news.save()
    return redirect("dashboard")


@login_required
def press_release_suggest(request):
    """Son xəbərlərə əsasən press-reliz mövzusu təklif edir."""
    org = _get_org(request.user)
    if not org:
        return JsonResponse({"ok": False})
    import datetime as _dt
    since = timezone.now() - _dt.timedelta(days=7)
    results = list(NewsResult.objects.filter(
        organization=org, saved_at__gte=since
    ).order_by("-saved_at")[:20])

    if not results:
        return JsonResponse({"ok": True, "topic": "", "details": ""})

    titles = "\n".join(f"- {r.title}" for r in results[:15])
    neg = sum(1 for r in results if r.sentiment == "MƏNFİ")
    pos = sum(1 for r in results if r.sentiment == "MÜSBƏT")

    prompt = f"""Aşağıdakı xəbər başlıqlarına əsasən {org.name} üçün 1 press-reliz mövzusu təklif et.
Xəbərlər (son 7 gün):
{titles}

Statistika: {len(results)} xəbər, {neg} mənfi, {pos} müsbət.

JSON formatında qaytar:
{{"topic": "...", "details": "2-3 cümlə izah"}}

Yalnız JSON, başqa heç nə yazma."""

    raw = _gemini(prompt)
    import json as _json
    try:
        import re as _re
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        data = _json.loads(m.group()) if m else {}
        return JsonResponse({"ok": True, "topic": data.get("topic",""), "details": data.get("details","")})
    except Exception:
        return JsonResponse({"ok": True, "topic": "", "details": raw[:200]})


@login_required
def keyword_analytics(request):
    org = _get_org(request.user)
    if not org:
        return redirect("dashboard")

    days = int(request.GET.get("days", 30))
    cutoff = timezone.now() - datetime.timedelta(days=days)

    keywords = org.keywords.filter(is_active=True).order_by("word")

    stats = []
    for kw in keywords:
        qs = NewsResult.objects.filter(organization=org, keyword=kw.word, saved_at__gte=cutoff)
        total = qs.count()
        pos   = qs.filter(sentiment="MÜSBƏT").count()
        neg   = qs.filter(sentiment="MƏNFİ").count()

        # Daily counts for the last `days` days
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        daily = (
            qs.annotate(date=TruncDate("saved_at"))
              .values("date")
              .annotate(cnt=Count("id"))
              .order_by("date")
        )
        daily_labels = [str(d["date"]) for d in daily]
        daily_counts = [d["cnt"] for d in daily]

        stats.append({
            "keyword": kw.word,
            "total": total,
            "pos": pos,
            "neg": neg,
            "daily_labels": daily_labels,
            "daily_counts": daily_counts,
        })

    # Sort by total desc
    stats.sort(key=lambda x: x["total"], reverse=True)

    # ── Ümumi qrafiklər (sentiment bölgüsü / günlük axın / açar söz bölgüsü) ──
    # Dashboard-dakı "Statistika və analiz" bölməsindən köçürülüb — hamısı
    # bu səhifənin "days" filtri ilə eyni dövrü əhatə edir.
    from django.db.models import Count, Q
    org_qs = NewsResult.objects.filter(organization=org, saved_at__gte=cutoff)
    n_menfi  = org_qs.filter(sentiment="MƏNFİ").count()
    n_musbet = org_qs.filter(sentiment="MÜSBƏT").count()

    from django.db.models.functions import TruncDate
    daily_qs = (org_qs.annotate(date=TruncDate("saved_at"))
                       .values("date", "sentiment")
                       .annotate(say=Count("id"))
                       .order_by("date"))
    daily_dates  = sorted(set(str(r["date"]) for r in daily_qs))
    daily_menfi  = {str(r["date"]): r["say"] for r in daily_qs if r["sentiment"] == "MƏNFİ"}
    daily_musbet = {str(r["date"]): r["say"] for r in daily_qs if r["sentiment"] == "MÜSBƏT"}

    kw_qs = (org_qs.values("keyword", "sentiment")
                   .annotate(say=Count("id"))
                   .order_by("keyword"))
    kw_names  = sorted(set(r["keyword"] for r in kw_qs))
    kw_menfi  = {r["keyword"]: r["say"] for r in kw_qs if r["sentiment"] == "MƏNFİ"}
    kw_musbet = {r["keyword"]: r["say"] for r in kw_qs if r["sentiment"] == "MÜSBƏT"}

    chart_data = json.dumps({
        "pie": [n_menfi, n_musbet],
        "daily": {
            "labels": daily_dates,
            "menfi":  [daily_menfi.get(d, 0)  for d in daily_dates],
            "musbet": [daily_musbet.get(d, 0) for d in daily_dates],
        },
        "kw": {
            "labels": kw_names,
            "menfi":  [kw_menfi.get(k, 0)  for k in kw_names],
            "musbet": [kw_musbet.get(k, 0) for k in kw_names],
        },
    })

    # ── Müqayisəli analiz ("days" filtrindən asılı olmayan öz dövrü) ──────────
    cmp_period = request.GET.get("cmp", "week")
    cmp_days = {"week": 7, "month": 30, "quarter": 90, "day": 1}.get(cmp_period, 7)
    now = timezone.now()
    this_start = now - datetime.timedelta(days=cmp_days)
    last_start = now - datetime.timedelta(days=cmp_days * 2)

    this_qs = NewsResult.objects.filter(organization=org, saved_at__gte=this_start)
    last_qs = NewsResult.objects.filter(organization=org, saved_at__gte=last_start, saved_at__lt=this_start)

    def _period_stats(q):
        total  = q.count()
        menfi  = q.filter(sentiment="MƏNFİ").count()
        musbet = q.filter(sentiment="MÜSBƏT").count()
        menfi_pct  = round(menfi  / total * 100) if total else 0
        musbet_pct = round(musbet / total * 100) if total else 0
        return {"total": total, "menfi": menfi, "musbet": musbet,
                "menfi_pct": menfi_pct, "musbet_pct": musbet_pct}

    def _delta(a, b):
        diff = a - b
        return {"val": abs(diff), "up": diff >= 0, "same": diff == 0}

    tw = _period_stats(this_qs)
    lw = _period_stats(last_qs)
    comparison = {
        "this": tw, "last": lw,
        "total_d":  _delta(tw["total"],      lw["total"]),
        "menfi_d":  _delta(tw["menfi"],      lw["menfi"]),
        "musbet_d": _delta(tw["musbet"],     lw["musbet"]),
        "menfi_pct_d":  _delta(tw["menfi_pct"],  lw["menfi_pct"]),
        "musbet_pct_d": _delta(tw["musbet_pct"], lw["musbet_pct"]),
    }

    # ── Mənbə reytinqi (bütün dövr, ilk 10) ───────────────────────────────────
    src_qs = (NewsResult.objects
              .filter(organization=org, source__isnull=False)
              .exclude(source="")
              .values("source")
              .annotate(
                  total=Count("id"),
                  menfi=Count("id", filter=Q(sentiment="MƏNFİ")),
                  musbet=Count("id", filter=Q(sentiment="MÜSBƏT")),
              )
              .order_by("-total")[:10])

    source_ratings = []
    for s in src_qs:
        t = s["total"] or 1
        source_ratings.append({
            "source":  s["source"],
            "total":   s["total"],
            "menfi":   s["menfi"],
            "musbet":  s["musbet"],
            "menfi_pct":  round(s["menfi"]  / t * 100),
            "musbet_pct": round(s["musbet"] / t * 100),
        })

    return render(request, "monitor/keyword_analytics.html", {
        "org": org,
        "stats": stats,
        "days": days,
        "stats_json": json.dumps(stats),
        "chart_data": chart_data,
        "comparison": comparison,
        "cmp_period": cmp_period,
        "source_ratings": source_ratings,
    })


@login_required
def press_release(request):
    result = ""
    if request.method == "POST":
        org_name   = request.POST.get("org_name", "").strip()
        topic      = request.POST.get("topic", "").strip()
        details    = request.POST.get("details", "").strip()
        tone       = request.POST.get("tone", "rəsmi")
        lang       = request.POST.get("lang", "az")

        lang_label = "Azərbaycan dilində" if lang == "az" else "rus dilində" if lang == "ru" else "ingilis dilində"
        prompt = f"""Sən PR mütəxəssisisən. Aşağıdakı məlumatlara əsasən peşəkar press-reliz yaz.

Təşkilat: {org_name}
Mövzu: {topic}
Ətraflı məlumat: {details}
Ton: {tone}
Dil: {lang_label}

Press-reliz strukturu:
- Başlıq (cəlbedici, informativ)
- Alt başlıq (isteğe bağlı)
- Tarix və şəhər
- Giriş paraqrafı (ən vacib məlumat)
- Əsas hissə (2-3 paraqraf)
- Sitat (rəhbərdən və ya nümayəndədən)
- Bağlayıcı paraqraf
- Şirkət haqqında qısa məlumat (boilerplate)
- Əlaqə məlumatları

Yalnız press-reliz mətni yaz, başqa izahat əlavə etmə."""

        result = _gemini(prompt)

    return render(request, "monitor/press_release.html", {"result": result})


@login_required
def post_titles(request):
    result = ""
    if request.method == "POST":
        topic   = request.POST.get("topic", "").strip()
        details = request.POST.get("details", "").strip()
        count   = request.POST.get("count", "5")
        platforms = request.POST.getlist("platforms")
        lang    = request.POST.get("lang", "az")

        platforms_str = ", ".join(platforms) if platforms else "ümumi"
        lang_label = "Azərbaycan dilində" if lang == "az" else "rus dilində" if lang == "ru" else "ingilis dilində"

        prompt = f"""Sən sosial media mütəxəssisisən. Aşağıdakı məzmun üçün cəlbedici sosial media post başlıqları yaz.

Mövzu: {topic}
Ətraflı məlumat: {details}
Platform(lar): {platforms_str}
Başlıq sayı: {count}
Dil: {lang_label}

Hər başlıq:
- Cəlbedici və oxunaqlı olsun
- Platforma üçün uyğun uzunluqda olsun
- Emoji istifadə et (uyğun olduqda)
- Hashtag təklif et (hər başlıq üçün 3-5 ədəd)

Nömrəli siyahı şəklində yaz. Hər başlığın altında həmin başlıq üçün hashtag-ları yaz."""

        result = _gemini(prompt)

    return render(request, "monitor/post_titles.html", {"result": result})


@login_required
def news_delete(request, pk):
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return redirect("dashboard")
    NewsResult.objects.filter(pk=pk, organization=org).delete()
    return redirect("dashboard")


TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def _tg_send(text):
    import urllib.request, urllib.parse
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    try:
        urllib.request.urlopen(url, data, timeout=8)
    except Exception:
        pass


def _calc_nsi(musbet, menfi, total):
    """Net Sentiment İndeksi: (Müsbət−Mənfi)/Ümumi×100, -100..+100 aralığında.
    Rəqib monitorinq şirkətlərinin hesabatlarında standart göstəricidir."""
    if not total:
        return 0.0
    return round((musbet - menfi) / total * 100, 1)


def _peak_day(qs):
    """Ən çox xəbərin toplandığı günü qaytarır: (tarix, say) və ya None (boş qs)."""
    from django.db.models.functions import TruncDate
    from django.db.models import Count
    row = (qs.annotate(date=TruncDate("saved_at"))
             .values("date")
             .annotate(say=Count("id"))
             .order_by("-say", "-date")
             .first())
    if not row:
        return None
    return row["date"], row["say"]


def _top_headlines(qs, sentiment, n=10):
    """Verilmiş sentiment üzrə ən son N başlığı (başlıq, link) cütləri kimi qaytarır."""
    rows = (qs.filter(sentiment=sentiment)
              .order_by("-saved_at")
              .values_list("title", "link")[:n])
    return list(rows)


def _source_sentiment_table(qs, n=15):
    """Mənbə üzrə say/sentiment/NSİ cədvəli — ümumi sayına görə azalan sırayla ilk N mənbə."""
    from django.db.models import Count, Q
    rows = (qs.exclude(source="")
              .values("source")
              .annotate(
                  total=Count("id"),
                  musbet=Count("id", filter=Q(sentiment="MÜSBƏT")),
                  menfi=Count("id", filter=Q(sentiment="MƏNFİ")),
              )
              .order_by("-total")[:n])
    out = []
    for r in rows:
        out.append({
            **r,
            "nsi": _calc_nsi(r["musbet"], r["menfi"], r["total"]),
        })
    return out


def _resolve_export_range(request, default_days=30):
    """Hesabat üçün tarix aralığını müəyyən edir. `date_from`/`date_to`
    (YYYY-MM-DD) verilibsə həmin dəqiq aralıq, əks halda `days` (son N gün)
    istifadə olunur. Qaytarır: (since, until, dövr etiketi)."""
    date_from = request.GET.get("date_from", "").strip()
    date_to   = request.GET.get("date_to", "").strip()
    since = until = None
    if date_from:
        try:
            since = timezone.make_aware(datetime.datetime.combine(
                datetime.date.fromisoformat(date_from), datetime.time.min))
        except ValueError:
            date_from = ""
    if date_to:
        try:
            until = timezone.make_aware(datetime.datetime.combine(
                datetime.date.fromisoformat(date_to), datetime.time.max))
        except ValueError:
            date_to = ""

    if since or until:
        label = f"{date_from or '…'} — {date_to or '…'}"
        return since, until, label

    days = int(request.GET.get("days", default_days))
    return timezone.now() - datetime.timedelta(days=days), None, f"Son {days} gün"


@login_required
def export_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    org = _get_org(request.user)
    if not org:
        return redirect("dashboard")

    since, until, period_label = _resolve_export_range(request)
    qs = NewsResult.objects.filter(organization=org, saved_at__gte=since)
    if until:
        qs = qs.filter(saved_at__lte=until)
    results = qs.order_by("-saved_at")

    n_total  = qs.count()
    n_musbet = qs.filter(sentiment="MÜSBƏT").count()
    n_menfi  = qs.filter(sentiment="MƏNFİ").count()
    nsi      = _calc_nsi(n_musbet, n_menfi, n_total)
    peak     = _peak_day(qs)
    top_pos  = _top_headlines(qs, "MÜSBƏT", 10)
    top_neg  = _top_headlines(qs, "MƏNFİ", 10)
    src_table = _source_sentiment_table(qs, 15)

    wb = openpyxl.Workbook()

    # ── Xülasə vərəqi ────────────────────────────────────────────────
    sw = wb.active
    sw.title = "Xülasə"
    header_fill = PatternFill("solid", fgColor="E2E8F0")
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    sw.merge_cells("A1:E1")
    sw["A1"] = "MediaPulse — Media Monitorinq Hesabatı"
    sw["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    sw["A1"].fill = PatternFill("solid", fgColor="1E3A5F")
    sw["A1"].alignment = Alignment(horizontal="center", vertical="center")
    sw.row_dimensions[1].height = 32

    sw.merge_cells("A2:E2")
    sw["A2"] = f"{org.name}  |  {period_label}  |  {datetime.date.today().strftime('%d.%m.%Y')}"
    sw["A2"].font = Font(size=11, color="64748B")
    sw["A2"].alignment = Alignment(horizontal="center")
    sw.row_dimensions[2].height = 22

    metric_labels = ["Cəmi xəbər", "Müsbət", "Mənfi", "Net Sentiment İndeksi (NSİ)"]
    metric_values = [n_total, n_musbet, n_menfi, nsi]
    metric_colors = ["1E3A5F", "10B981", "EF4444", "2F6FB3"]
    for col, (lbl, val, color) in enumerate(zip(metric_labels, metric_values, metric_colors), 1):
        c1 = sw.cell(row=4, column=col, value=lbl)
        c1.font = Font(bold=True, size=10, color="64748B")
        c1.alignment = Alignment(horizontal="center")
        c2 = sw.cell(row=5, column=col, value=val)
        c2.font = Font(bold=True, size=20, color=color)
        c2.alignment = Alignment(horizontal="center")
    sw.row_dimensions[5].height = 30

    row = 7
    if peak:
        sw.cell(row=row, column=1, value=f"Pik gün: {peak[0].strftime('%d.%m.%Y')} — {peak[1]} xəbər").font = Font(bold=True, size=11, color="1E3A5F")
        row += 2

    def _write_headline_block(title, items, color, start_row):
        sw.cell(row=start_row, column=1, value=title).font = Font(bold=True, size=12, color=color)
        r = start_row + 1
        for headline, link in items:
            cell = sw.cell(row=r, column=1, value=headline[:150])
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if link:
                cell.hyperlink = link
                cell.font = Font(color="1D4ED8", underline="single")
            sw.row_dimensions[r].height = 16
            r += 1
        return r + 1

    row = _write_headline_block("🟢 Top 10 müsbət başlıq", top_pos, "10B981", row)
    row = _write_headline_block("🔴 Top 10 mənfi başlıq", top_neg, "EF4444", row)

    if src_table:
        row += 1
        sw.cell(row=row, column=1, value="Mənbə üzrə reytinq").font = Font(bold=True, size=12, color="1E3A5F")
        row += 1
        for col, h in enumerate(["Mənbə", "Ümumi", "Müsbət", "Mənfi", "NSİ"], 1):
            c = sw.cell(row=row, column=col, value=h)
            c.font = Font(bold=True, size=10)
            c.fill = header_fill
            c.border = border
        row += 1
        for r in src_table:
            for col, val in enumerate([r["source"], r["total"], r["musbet"], r["menfi"], r["nsi"]], 1):
                c = sw.cell(row=row, column=col, value=val)
                c.border = border
            row += 1

    sw.column_dimensions["A"].width = 70
    for col_letter in ["B", "C", "D", "E"]:
        sw.column_dimensions[col_letter].width = 16

    # ── Detallar vərəqi ──────────────────────────────────────────────
    ws = wb.create_sheet("Detallar")

    # Başlıq
    ws.merge_cells("A1:G1")
    ws["A1"] = f"MediaPulse — Media Monitorinq Hesabatı"
    ws["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="1E3A5F")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 32

    ws.merge_cells("A2:G2")
    ws["A2"] = f"{org.name}  |  {period_label}  |  {datetime.date.today().strftime('%d.%m.%Y')}"
    ws["A2"].font = Font(size=11, color="64748B")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[2].height = 22

    # Sütun başlıqları
    headers = ["#", "Tarix", "Açar söz", "Başlıq", "Xülasə", "Mənbə", "Sentiment", "Link"]
    header_fill = PatternFill("solid", fgColor="E2E8F0")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.font = Font(bold=True, size=11)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 20

    # Məlumatlar
    sentiment_colors = {"MƏNFİ": "FEE2E2", "MÜSBƏT": "D1FAE5"}
    thin = Side(style="thin", color="E2E8F0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for i, news in enumerate(results, 1):
        row = i + 4
        color = sentiment_colors.get(news.sentiment, "FFFFFF")
        fill  = PatternFill("solid", fgColor=color)

        values = [i, news.saved_at.strftime("%d.%m.%Y %H:%M"), news.keyword,
                  news.title, news.summary[:200] if news.summary else "", news.source,
                  news.sentiment, news.link or ""]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if col == len(values) and val:   # Link sütunu — klikləyən hiperlink
                cell.hyperlink = val
                cell.font = Font(color="1D4ED8", underline="single")
        ws.row_dimensions[row].height = 40

    # Sütun genişliyi
    widths = [5, 16, 22, 60, 50, 18, 12, 55]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    fname = f"mediapulse_{org.slug}_{datetime.date.today()}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    wb.save(response)
    return response


def _build_report_pdf_bytes(org, qs, period_label, for_email=False):
    """Brendli PDF hesabatı qurur və PDF bayt-larını qaytarır. `export_pdf`
    (birbaşa yükləmə) və e-poçtla göndərilən hesabatlar (`_do_send_report`,
    `weekly_report.py`) eyni bu funksiyanı çağırır ki, hər yerdə eyni
    struktur (statistika kartları, qrafiklər, Top 10 başlıq, mənbə reytinqi,
    metodologiya) görünsün — üç yerdə təkrarlanan PDF kodu saxlamaq əvəzinə.

    for_email=True olanda: hesabat üçüncü-tərəf xəbər saytlarının kliklənən
    URL-lərini DAXİL ETMİR. Səbəb: hesabat onlarla scrape edilmiş xəbər
    saytına (bəziləri aşağı reputasiyalı .info domenləri) yüzlərlə keçid
    yığırdı; bunlardan biri belə Google Safe Browsing / mail.ru antivirus
    qara siyahısında olanda BÜTÜN PDF "virus" kimi işarələnib bloklanırdı
    (2026-07-23 Gmail "Virus tapıldı" + mail.ru 550 spam). E-poçt versiyasında
    linklər mətnlə əvəz olunur, tam interaktiv versiya panelə yönləndirilir.
    Yüklənən versiya (for_email=False) linkləri saxlayır — o, e-poçt
    antivirusundan keçmir."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    import io

    results = qs.order_by("-saved_at")

    n_total  = qs.count()
    n_musbet = qs.filter(sentiment="MÜSBƏT").count()
    n_menfi  = qs.filter(sentiment="MƏNFİ").count()
    nsi      = _calc_nsi(n_musbet, n_menfi, n_total)
    peak     = _peak_day(qs)
    top_pos  = _top_headlines(qs, "MÜSBƏT", 10)
    top_neg  = _top_headlines(qs, "MƏNFİ", 10)
    src_table = _source_sentiment_table(qs, 15)

    # Unicode font qeydiyyatı (Azərbaycan hərfləri üçün)
    _FONT_DIR = "/usr/share/fonts/truetype/dejavu"
    try:
        pdfmetrics.registerFont(TTFont("DejaVu",     f"{_FONT_DIR}/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold",f"{_FONT_DIR}/DejaVuSans-Bold.ttf"))
        _FONT      = "DejaVu"
        _FONT_BOLD = "DejaVu-Bold"
    except Exception:
        _FONT      = "Helvetica"
        _FONT_BOLD = "Helvetica-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)

    styles = getSampleStyleSheet()
    navy   = colors.HexColor("#1E3A5F")
    accent = colors.HexColor("#2F6FB3")
    red    = colors.HexColor("#EF4444")
    green  = colors.HexColor("#10B981")
    amber  = colors.HexColor("#F59E0B")
    light  = colors.HexColor("#F8FAFC")
    border_c = colors.HexColor("#E2E8F0")
    muted  = colors.HexColor("#64748B")

    title_style = ParagraphStyle("title", fontSize=17, leading=20, textColor=colors.white,
                                  fontName=_FONT_BOLD, spaceAfter=0)
    sub_style   = ParagraphStyle("sub",   fontSize=10.5, leading=13, textColor=navy,
                                  fontName=_FONT, spaceAfter=0)
    cell_style  = ParagraphStyle("cell",  fontSize=8,  fontName=_FONT,
                                  leading=11, textColor=colors.HexColor("#111827"))
    sent_style  = ParagraphStyle("sent",  fontSize=8,  fontName=_FONT_BOLD,
                                  leading=11, alignment=1)
    link_style = ParagraphStyle("link", fontSize=6.5, fontName=_FONT,
                                leading=8, textColor=colors.HexColor("#1D4ED8"))
    # QEYD: ParagraphStyle-də `leading` təyin edilməyəndə reportlab-ın defoltu
    # sabit 12pt-dir (fontSize-ə mütənasib DEYİL). Bir cədvəl xanasında bir
    # neçə Paragraph üst-üstə yığılanda (statistika kartları kimi) bu,
    # fontSize 12-dən böyük olan hər stildə mətnin növbəti abzasın üstünə
    # daşmasına səbəb olur — ona görə burda hamısına açıq leading verilib.
    stat_lbl_style = ParagraphStyle("statlbl", fontSize=9, leading=12, fontName=_FONT,
                                     textColor=muted, alignment=1)
    stat_val_style = ParagraphStyle("statval", fontSize=24, leading=28, fontName=_FONT_BOLD,
                                     alignment=1)
    caption_style = ParagraphStyle("caption", fontSize=9.5, leading=12, fontName=_FONT_BOLD,
                                    textColor=navy, alignment=1, spaceBefore=4)
    h2_style = ParagraphStyle("h2", fontSize=13, leading=16, fontName=_FONT_BOLD, textColor=navy, spaceAfter=8)
    headline_style = ParagraphStyle("headline", fontSize=8.5, fontName=_FONT,
                                     leading=12, textColor=colors.HexColor("#111827"))
    body_style = ParagraphStyle("body", fontSize=9.5, fontName=_FONT, leading=15,
                                 textColor=colors.HexColor("#111827"))

    import re as _re
    def _clean(s):
        s = (s or "").strip()
        s = _re.sub(r'<[^>]+>', '', s)   # HTML/XML teqlərini sil
        s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        return s

    def _link_p(url):
        # E-poçt versiyasında üçüncü-tərəf URL-i heç cür (link və ya mətn kimi)
        # daxil edilmir — antivirus yanlış-pozitivinin qarşısını almaq üçün.
        if for_email:
            return Paragraph("—", cell_style)
        if not url or url == "#":
            return Paragraph("—", cell_style)
        safe = _clean(url)
        return Paragraph(f'<a href="{safe}">{safe}</a>', link_style)

    # ── Brendli başlıq banner-i ────────────────────────────────────────
    banner = Table([[Paragraph("MediaPulse — Media Monitorinq Hesabatı", title_style)]],
                    colWidths=[26.7*cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), navy),
        ("TOPPADDING", (0,0), (-1,-1), 12), ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
    ]))
    info_bar = Table([[Paragraph(
        f"{org.name}&nbsp;&nbsp;|&nbsp;&nbsp;{_clean(period_label)}&nbsp;&nbsp;|&nbsp;&nbsp;"
        f"Yaradıldı: {datetime.date.today().strftime('%d.%m.%Y')}", sub_style)]],
        colWidths=[26.7*cm])
    info_bar.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#EAF2FB")),
        ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 16),
    ]))

    story = [banner, info_bar, Spacer(1, 0.5*cm)]

    if n_total == 0:
        story.append(Paragraph("Bu dövr üzrə heç bir nəticə tapılmadı.", body_style))
        doc.build(story)
        return buf.getvalue()

    # ── Statistika kartları (Cəmi / Müsbət / Mənfi / NSİ) ───────────────
    def _stat_cell(label, value, color):
        return [Paragraph(str(value), ParagraphStyle("v", parent=stat_val_style, textColor=color)),
                Paragraph(label, stat_lbl_style)]

    stats_row = Table([[
        _stat_cell("Cəmi xəbər", n_total, navy),
        _stat_cell("Müsbət", n_musbet, green),
        _stat_cell("Mənfi", n_menfi, red),
        _stat_cell("Net Sentiment İndeksi", nsi, accent),
    ]], colWidths=[6.675*cm]*4)
    stats_row.setStyle(TableStyle([
        ("BOX", (0,0), (0,-1), 0.75, border_c), ("BOX", (1,0), (1,-1), 0.75, border_c),
        ("BOX", (2,0), (2,-1), 0.75, border_c), ("BOX", (3,0), (3,-1), 0.75, border_c),
        ("BACKGROUND", (0,0), (-1,-1), light),
        ("TOPPADDING", (0,0), (-1,-1), 10), ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(stats_row)
    story.append(Spacer(1, 0.5*cm))

    # ── Qrafiklər: sentiment bölgüsü + günlük axın ──────────────────────
    pie_d = Drawing(340, 170)
    pie = Pie()
    pie.x, pie.y, pie.width, pie.height = 90, 15, 130, 130
    pie.data = [n_musbet, n_menfi]
    pie.labels = [f"Müsbət ({n_musbet})", f"Mənfi ({n_menfi})"]
    pie.slices.strokeWidth = 0.75
    pie.slices.strokeColor = colors.white
    pie.slices.fontName = _FONT   # DejaVu — Azərbaycan hərfləri üçün (Helvetica-da tofu qutu görünür)
    pie.slices[0].fillColor = green
    pie.slices[1].fillColor = red
    pie.simpleLabels = 1
    pie.sideLabels = 0
    pie_d.add(pie)

    from django.db.models.functions import TruncDate
    from django.db.models import Count, Q as _Q
    daily_qs = (qs.annotate(date=TruncDate("saved_at"))
                  .values("date")
                  .annotate(musbet=Count("id", filter=_Q(sentiment="MÜSBƏT")),
                            menfi=Count("id", filter=_Q(sentiment="MƏNFİ")))
                  .order_by("date"))
    daily_rows = list(daily_qs)[-31:]   # oxunaqlı qalması üçün son 31 gün
    truncated_note = " (son 31 gün göstərilir)" if daily_qs.count() > 31 else ""

    bar_d = Drawing(340, 170)
    if daily_rows:
        bc = VerticalBarChart()
        bc.x, bc.y, bc.width, bc.height = 40, 30, 280, 120
        bc.data = [[r["musbet"] for r in daily_rows], [r["menfi"] for r in daily_rows]]
        bc.categoryAxis.categoryNames = [r["date"].strftime("%d.%m") for r in daily_rows]
        bc.categoryAxis.labels.fontSize = 5.5
        bc.categoryAxis.labels.angle = 45
        bc.categoryAxis.labels.dy = -8
        bc.categoryAxis.labels.dx = -4
        bc.valueAxis.labels.fontSize = 6.5
        bc.bars[0].fillColor = green
        bc.bars[1].fillColor = red
        bc.groupSpacing = 2
        bar_d.add(bc)

    charts_row = Table([[pie_d, bar_d]], colWidths=[13.35*cm, 13.35*cm])
    charts_row.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP")]))
    story.append(charts_row)
    caps = Table([[Paragraph("Sentiment bölgüsü", caption_style),
                   Paragraph(f"Günlük xəbər axını{truncated_note}", caption_style)]],
                 colWidths=[13.35*cm, 13.35*cm])
    story.append(caps)

    if peak:
        story.append(Spacer(1, 0.35*cm))
        peak_box = Table([[Paragraph(
            f"📈&nbsp; Pik gün: <b>{peak[0].strftime('%d.%m.%Y')}</b> — {peak[1]} xəbər",
            ParagraphStyle("peak", fontSize=10, fontName=_FONT, textColor=navy))]],
            colWidths=[26.7*cm])
        peak_box.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FEF9E7")),
            ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#F5E6A8")),
            ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 12),
        ]))
        story.append(peak_box)

    # ── Top 10 müsbət / mənfi başlıqlar ──────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Ən çox diqqət çəkən başlıqlar", h2_style))

    def _headline_list(items, color, icon, empty_msg):
        flow = [Paragraph(f"{icon} Top {len(items) or 10} başlıq", ParagraphStyle(
            "hh", fontSize=11, leading=14, fontName=_FONT_BOLD, textColor=color, spaceAfter=6))]
        if not items:
            flow.append(Paragraph(empty_msg, headline_style))
        for n, (headline, link) in enumerate(items, 1):
            safe_title = _clean(headline)[:140]
            if link and not for_email:
                flow.append(Paragraph(f'{n}. <a href="{_clean(link)}">{safe_title}</a>', ParagraphStyle(
                    "hl", parent=headline_style, textColor=colors.HexColor("#1D4ED8"), spaceAfter=5)))
            else:
                flow.append(Paragraph(f"{n}. {safe_title}", ParagraphStyle(
                    "hl2", parent=headline_style, spaceAfter=5)))
        return flow

    headlines_table = Table([[
        _headline_list(top_pos, green, "🟢", "Bu dövrdə müsbət xəbər tapılmadı."),
        _headline_list(top_neg, red, "🔴", "Bu dövrdə mənfi xəbər tapılmadı."),
    ]], colWidths=[13.35*cm, 13.35*cm])
    headlines_table.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"),
                                          ("LEFTPADDING", (1,0), (1,0), 20)]))
    story.append(headlines_table)

    # ── Mənbə üzrə reytinq ────────────────────────────────────────────
    if src_table:
        story.append(PageBreak())
        story.append(Paragraph("Mənbə üzrə reytinq", h2_style))
        src_header = ["Mənbə", "Ümumi", "Müsbət", "Mənfi", "NSİ"]
        src_data = [src_header]
        for r in src_table:
            src_data.append([
                Paragraph(_clean(r["source"])[:60], cell_style),
                str(r["total"]), str(r["musbet"]), str(r["menfi"]), str(r["nsi"]),
            ])
        src_tbl = Table(src_data, colWidths=[14*cm, 3.175*cm, 3.175*cm, 3.175*cm, 3.175*cm], repeatRows=1)
        src_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), navy), ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), _FONT_BOLD), ("FONTNAME", (0,1), (-1,-1), _FONT),
            ("ALIGN", (1,0), (-1,-1), "CENTER"), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, light]),
            ("GRID", (0,0), (-1,-1), 0.5, border_c),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(src_tbl)

    # ── Ətraflı cədvəl ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Ətraflı siyahı", h2_style))
    if for_email:
        story.append(Paragraph(
            '🔗 Xəbər mənbələrinə birbaşa keçidlər interaktiv panel versiyasında '
            'aktivdir: <a href="https://mediapulse.az/dashboard/">mediapulse.az/dashboard</a>',
            ParagraphStyle("cta", parent=body_style, fontSize=9, textColor=muted, spaceAfter=8)))

    header = ["#", "Tarix", "Açar söz", "Başlıq", "Xülasə", "Mənbə", "Sentiment", "Link"]
    data = [header]

    for i, news in enumerate(results[:200], 1):
        sent = news.sentiment
        title_p   = Paragraph(_clean(news.title)[:120], cell_style)
        summary_p = Paragraph(_clean(news.summary)[:150], cell_style)
        kw_p      = Paragraph(_clean(news.keyword)[:40], cell_style)
        src_p     = Paragraph(_clean(news.source)[:30], cell_style)
        data.append([
            str(i),
            news.saved_at.strftime("%d.%m\n%H:%M"),
            kw_p, title_p, summary_p, src_p,
            Paragraph(sent, sent_style),
            _link_p(news.link),
        ])

    col_widths = [0.7*cm, 1.6*cm, 2.8*cm, 6*cm, 5*cm, 2.3*cm, 1.6*cm, 6.1*cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    ts = TableStyle([
        # Başlıq
        ("BACKGROUND",  (0,0), (-1,0), navy),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), _FONT_BOLD),
        ("FONTNAME",    (0,1), (-1,-1), _FONT),
        ("FONTSIZE",    (0,0), (-1,0), 9),
        ("ALIGN",       (0,0), (-1,0), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, light]),
        ("FONTSIZE",    (0,1), (-1,-1), 8),
        ("GRID",        (0,0), (-1,-1), 0.5, border_c),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0), (-1,-1), 4),
    ])

    # Sentiment rəngləri
    for i, news in enumerate(results[:200], 1):
        if news.sentiment == "MƏNFİ":
            ts.add("TEXTCOLOR", (6,i), (6,i), red)
        elif news.sentiment == "MÜSBƏT":
            ts.add("TEXTCOLOR", (6,i), (6,i), green)
        else:
            ts.add("TEXTCOLOR", (6,i), (6,i), amber)

    table.setStyle(ts)
    story.append(table)

    # ── Metodologiya səhifəsi ────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Metodologiya", h2_style))
    story.append(Paragraph(
        "MediaPulse açar sözlərinizə uyğun xəbərləri xəbər saytlarından, sosial media "
        "platformalarından və TV monitorinq axınından fasiləsiz toplayır. Hər nəticə "
        "süni intellekt tərəfindən müsbət/mənfi sentimentə görə təsnif edilir.",
        body_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Net Sentiment İndeksi (NSİ)</b> — auditoriyanın ümumi əhval-ruhiyyəsini "
        "tək rəqəmlə ifadə edən göstəricidir:",
        body_style))
    story.append(Paragraph(
        "NSİ&nbsp;=&nbsp;(Müsbət xəbər sayı&nbsp;−&nbsp;Mənfi xəbər sayı)&nbsp;÷&nbsp;"
        "Ümumi xəbər sayı&nbsp;×&nbsp;100",
        ParagraphStyle("formula", fontSize=11, fontName=_FONT_BOLD, textColor=navy,
                       spaceAfter=4, spaceBefore=4, leftIndent=10)))
    story.append(Paragraph(
        "Nəticə −100 (tamamilə mənfi) ilə +100 (tamamilə müsbət) arasında dəyişir. "
        "0-dan yuxarı dəyər müsbət xəbərlərin üstünlük təşkil etdiyini göstərir.",
        body_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<b>Mənbə üzrə reytinq</b> cədvəli hər mənbənin (sayt, sosial hesab, TV kanalı) "
        "gətirdiyi ümumi xəbər sayını və bu xəbərlərin sentiment tərkibini göstərir — "
        "hansı mənbənin daha çox müsbət və ya mənfi kontent yaratdığını müəyyən etməyə kömək edir.",
        body_style))

    doc.build(story)
    return buf.getvalue()


@login_required
def export_pdf(request):
    org = _get_org(request.user)
    if not org:
        return redirect("dashboard")

    since, until, period_label = _resolve_export_range(request)
    qs = NewsResult.objects.filter(organization=org, saved_at__gte=since)
    if until:
        qs = qs.filter(saved_at__lte=until)

    pdf_bytes = _build_report_pdf_bytes(org, qs, period_label)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    fname = f"mediapulse_{org.slug}_{datetime.date.today()}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{fname}"'
    return response


@login_required
@require_POST
def dismiss_onboarding(request):
    org = _get_org(request.user)
    if org:
        org.onboarding_done = True
        org.save()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def save_notif_settings(request):
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return JsonResponse({"ok": False})
    org.notif_on_negative   = request.POST.get("notif_on_negative")   == "1"
    org.notif_on_positive   = request.POST.get("notif_on_positive")   == "1"
    org.notif_daily_summary = request.POST.get("notif_daily_summary") == "1"
    try:
        hour = int(request.POST.get("notif_daily_hour", 18))
        org.notif_daily_hour = max(0, min(23, hour))
    except ValueError:
        pass
    org.save()
    return JsonResponse({"ok": True})


def parse_report_emails(raw):
    """Bir neçə e-poçt ünvanını (vergül, nöqtəli vergül, boşluq və ya yeni
    sətirlə ayrılmış) təmizlənmiş, doğrulanmış, təkrarsız siyahıya çevirir.
    Yanlış formatlı ünvanlar sükutla atılır. Həm dashboard view-ləri, həm də
    weekly_report.py cron-u eyni məntiqi istifadə etsin deyə modul səviyyəsində."""
    import re
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
    if not raw:
        return []
    seen, out = set(), []
    for part in re.split(r"[,;\s]+", raw.strip()):
        part = part.strip()
        if not part:
            continue
        try:
            validate_email(part)
        except ValidationError:
            continue
        key = part.lower()
        if key not in seen:
            seen.add(key)
            out.append(part)
    return out


@login_required
@require_POST
def send_test_report(request):
    import io, datetime, threading
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from django.core.mail import EmailMessage

    org = _get_org(request.user)
    try:
        role = request.user.membership.role
    except Exception:
        role = None
    if not org or role != "admin":
        return JsonResponse({"ok": False, "error": "icazə yoxdur"})

    emails = parse_report_emails(request.POST.get("report_email", ""))
    if not emails:
        return JsonResponse({"ok": False, "error": "düzgün e-poçt ünvanı daxil edin"})

    # Background-da göndər, UI-a dərhal cavab qaytar
    def _send():
        try:
            _do_send_report(org, emails)
        except Exception as _e:
            import traceback
            with open('/root/report_error.log', 'a') as _f:
                _f.write(traceback.format_exc() + '\n')
    threading.Thread(target=_send, daemon=True).start()
    return JsonResponse({"ok": True})


def _do_send_report(org, emails):
    import datetime
    from django.conf import settings as _settings
    from django.core.mail import EmailMessage

    # Geriyə uyğunluq: tək sətir də qəbul et
    if isinstance(emails, str):
        emails = parse_report_emails(emails)
    if not emails:
        return

    since = timezone.now() - datetime.timedelta(days=7)
    qs = NewsResult.objects.filter(organization=org, saved_at__gte=since)
    n_total  = qs.count()
    n_menfi  = qs.filter(sentiment="MƏNFİ").count()
    n_musbet = qs.filter(sentiment="MÜSBƏT").count()

    pdf_bytes = _build_report_pdf_bytes(org, qs, "Son 7 gün", for_email=True)
    week_str = timezone.now().strftime("%d.%m.%Y")

    try:
        msg = EmailMessage(
            subject=f"{org.name} — Həftəlik Media Hesabatı ({week_str}) [TEST]",
            body=(
                f"Bu test hesabatıdır.\n\n"
                f"Hörmətli {org.name} komandası,\n\n"
                f"Son 7 günün media monitorinq hesabatı əlavə edilmişdir.\n\n"
                f"Cəmi xəbər: {n_total}\n"
                f"Mənfi: {n_menfi}\n"
                f"Müsbət: {n_musbet}\n\n"
                f"— MediaPulse Media Monitorinq Platforması\n  mediapulse.az"
            ),
            from_email=_settings.DEFAULT_FROM_EMAIL,
            to=emails,
        )
        msg.attach(f"hesabat_{week_str}.pdf", pdf_bytes, "application/pdf")
        msg.send()
    except Exception as _e:
        import traceback
        with open('/root/report_error.log', 'a') as _f:
            _f.write('EMAIL SEND ERROR: ' + traceback.format_exc() + '\n')


@login_required
@require_POST
def save_report_settings(request):
    org = _get_org(request.user)
    if not org or request.user.membership.role != "admin":
        return JsonResponse({"ok": False})
    org.weekly_report_enabled = request.POST.get("weekly_report_enabled") == "1"
    emails = parse_report_emails(request.POST.get("report_email", ""))
    org.report_email = ", ".join(emails)  # təmizlənmiş, doğrulanmış formada saxla
    org.save()
    return JsonResponse({"ok": True, "cleaned": org.report_email, "count": len(emails)})


def demo(request):
    return render(request, "monitor/demo.html")


@require_POST
def demo_request(request):
    name    = request.POST.get("name", "").strip()
    company = request.POST.get("company", "").strip()
    contact = request.POST.get("contact", "").strip()
    message = request.POST.get("message", "").strip()
    plan    = request.POST.get("plan", "").strip()

    if not name or not company or not contact:
        return JsonResponse({"ok": False, "error": "Bütün sahələri doldurun"})

    DemoRequest.objects.create(name=name, company=company, contact=contact, plan=plan, message=message)

    tg_text = (
        f"🔔 <b>Yeni Demo Müraciəti!</b>\n\n"
        f"👤 Ad: {name}\n"
        f"🏢 Şirkət: {company}\n"
        f"📞 Əlaqə: {contact}\n"
        f"📦 Plan: {plan or '—'}\n"
        f"💬 Qeyd: {message or '—'}"
    )
    _tg_send(tg_text)

    return JsonResponse({"ok": True})

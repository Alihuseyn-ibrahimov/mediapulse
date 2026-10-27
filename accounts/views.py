from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from monitor.views import _get_landing_content, SUPPORTED_LANGS

LOGIN_STRINGS = {
    'az': {
        'tagline1': 'Mediada nə', 'tagline2': 'yazıldığını', 'tagline_hl': 'anında', 'tagline3': 'bilin',
        'brand_desc': 'Azərbaycanın aparıcı media monitorinq platforması. 300+ mənbə, süni intellekt analizi, real vaxt bildirişlər.',
        'stat1_lbl': 'İzlənilən mənbə', 'stat2_num': '15 dəq', 'stat2_lbl': 'Yeniləmə intervalı',
        'stat3_lbl': 'Sentiment analizi', 'stat4_lbl': 'Fasiləsiz izləmə',
        'footer': '© 2026 MediaPulse. Bütün hüquqlar qorunur.',
        'heading': 'Xoş gəldiniz 👋', 'sub': 'Hesabınıza daxil olmaq üçün məlumatlarınızı daxil edin',
        'lbl_user': 'İstifadəçi adı', 'ph_user': 'İstifadəçi adınızı daxil edin',
        'lbl_pass': 'Şifrə', 'btn': 'Daxil ol →',
        'back': '← Ana səhifə', 'forgot': 'Şifrəmi unutdum',
        'or': 'və ya', 'demo_link': '🎯 Canlı demo ilə tanış olun',
        'error_msg': 'İstifadəçi adı və ya şifrə yanlışdır.',
    },
    'ru': {
        'tagline1': 'Следите за тем,', 'tagline2': 'что пишут о вас', 'tagline_hl': 'сейчас', 'tagline3': '',
        'brand_desc': 'Ведущая платформа медиамониторинга. 300+ источников, анализ ИИ, уведомления в реальном времени.',
        'stat1_lbl': 'Отслеживаемых источников', 'stat2_num': '15 мин', 'stat2_lbl': 'Интервал обновления',
        'stat3_lbl': 'Анализ тональности', 'stat4_lbl': 'Круглосуточный мониторинг',
        'footer': '© 2026 MediaPulse. Все права защищены.',
        'heading': 'Добро пожаловать 👋', 'sub': 'Введите данные для входа в аккаунт',
        'lbl_user': 'Имя пользователя', 'ph_user': 'Введите имя пользователя',
        'lbl_pass': 'Пароль', 'btn': 'Войти →',
        'back': '← Главная', 'forgot': 'Забыл пароль',
        'or': 'или', 'demo_link': '🎯 Посмотреть живое демо',
        'error_msg': 'Неверное имя пользователя или пароль.',
    },
    'en': {
        'tagline1': 'Know what the media', 'tagline2': 'writes about you', 'tagline_hl': 'instantly', 'tagline3': '',
        'brand_desc': "Azerbaijan's leading media monitoring platform. 300+ sources, AI analysis, real-time alerts.",
        'stat1_lbl': 'Sources tracked', 'stat2_num': '15 min', 'stat2_lbl': 'Update interval',
        'stat3_lbl': 'Sentiment analysis', 'stat4_lbl': '24/7 monitoring',
        'footer': '© 2026 MediaPulse. All rights reserved.',
        'heading': 'Welcome back 👋', 'sub': 'Enter your credentials to access your account',
        'lbl_user': 'Username', 'ph_user': 'Enter your username',
        'lbl_pass': 'Password', 'btn': 'Log in →',
        'back': '← Home', 'forgot': 'Forgot password',
        'or': 'or', 'demo_link': '🎯 Watch live demo',
        'error_msg': 'Incorrect username or password.',
    },
    'es': {
        'tagline1': 'Sepa lo que los medios', 'tagline2': 'escriben sobre usted', 'tagline_hl': 'ahora', 'tagline3': '',
        'brand_desc': 'La plataforma líder de monitoreo de medios. 300+ fuentes, análisis de IA, alertas en tiempo real.',
        'stat1_lbl': 'Fuentes rastreadas', 'stat2_num': '15 min', 'stat2_lbl': 'Intervalo de actualización',
        'stat3_lbl': 'Análisis de sentimiento', 'stat4_lbl': 'Monitoreo 24/7',
        'footer': '© 2026 MediaPulse. Todos los derechos reservados.',
        'heading': 'Bienvenido 👋', 'sub': 'Ingrese sus credenciales para acceder a su cuenta',
        'lbl_user': 'Usuario', 'ph_user': 'Ingrese su nombre de usuario',
        'lbl_pass': 'Contraseña', 'btn': 'Iniciar sesión →',
        'back': '← Inicio', 'forgot': 'Olvidé mi contraseña',
        'or': 'o', 'demo_link': '🎯 Ver demo en vivo',
        'error_msg': 'Nombre de usuario o contraseña incorrectos.',
    },
}


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    lang = request.GET.get('lang') or request.session.get('lang', 'az')
    if lang not in SUPPORTED_LANGS:
        lang = 'az'
    request.session['lang'] = lang
    ls = LOGIN_STRINGS.get(lang, LOGIN_STRINGS['az'])
    error = None
    if request.method == "POST":
        from monitor.throttle import is_locked, register_failure, clear as clear_throttle
        if is_locked(request, "login"):
            error = "Çox sayda uğursuz cəhd. Zəhmət olmasa 15 dəqiqə sonra yenidən yoxlayın."
        else:
            user = authenticate(request,
                                username=request.POST.get("username"),
                                password=request.POST.get("password"))
            if user:
                clear_throttle(request, "login")
                login(request, user)
                return redirect("dashboard")
            register_failure(request, "login")
            error = ls['error_msg']
    return render(request, "accounts/login.html", {"error": error, "ls": ls, "lang": lang})


def logout_view(request):
    logout(request)
    return redirect("login")

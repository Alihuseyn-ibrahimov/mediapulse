from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from django.http import HttpResponse
import os
from accounts import views as acc_views
from monitor import views as mon_views

def _serve_static(filename, content_type):
    binary = content_type.startswith('image/')
    def view(request):
        fpath = os.path.join(settings.BASE_DIR, 'staticfiles', filename)
        mode = 'rb' if binary else 'r'
        with open(fpath, mode) as f:
            content = f.read()
        resp = HttpResponse(content, content_type=content_type)
        if filename == 'sw.js':
            resp['Service-Worker-Allowed'] = '/'
            resp['Cache-Control'] = 'no-cache'
        return resp
    return view

urlpatterns = [
    path("admin/",     admin.site.urls),
    path("",           mon_views.landing,       name="landing"),
    path("privacy/",   TemplateView.as_view(template_name="privacy.html"), name="privacy"),
    path("terms/",     TemplateView.as_view(template_name="terms.html"),   name="terms"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("sitemap.xml", TemplateView.as_view(template_name="sitemap.xml", content_type="application/xml")),
    path("login/",     acc_views.login_view,    name="login"),
    path("logout/",    acc_views.logout_view,   name="logout"),
    path("dashboard/", mon_views.dashboard,     name="dashboard"),
    path("notifications/feed/", mon_views.notifications_feed, name="notifications_feed"),
    path("keywords/",      mon_views.keywords_view, name="keywords"),
    path("press-release/",         mon_views.press_release,         name="press_release"),
    path("press-release/suggest/", mon_views.press_release_suggest, name="press_release_suggest"),
    path("post-titles/",   mon_views.post_titles,   name="post_titles"),
    path("landing-admin/",      mon_views.landing_admin, name="landing_admin"),
    path("landing-admin/grammar/",  mon_views.grammar_check, name="grammar_check"),
    path("tv-clips/<int:pk>/decide/",             mon_views.tv_clip_decide,       name="tv_clip_decide"),
    path("landing-admin/tv-clips/ingest/",        mon_views.tv_clip_ingest,       name="tv_clip_ingest"),
    path("landing-admin/tv-clips/upload-result/", mon_views.tv_clip_upload_result, name="tv_clip_upload_result"),
    path("demo/",                   mon_views.demo,         name="demo"),
    path("export/excel/",           mon_views.export_excel,       name="export_excel"),
    path("settings/notif/",         mon_views.save_notif_settings,  name="save_notif_settings"),
    path("settings/report/",        mon_views.save_report_settings, name="save_report_settings"),
    path("settings/report/test/",   mon_views.send_test_report,     name="send_test_report"),
    path("onboarding/dismiss/",     mon_views.dismiss_onboarding,  name="dismiss_onboarding"),
    path("export/pdf/",             mon_views.export_pdf,   name="export_pdf"),
    path("demo-request/",          mon_views.demo_request, name="demo_request"),
    path("keywords/analytics/",    mon_views.keyword_analytics, name="keyword_analytics"),
    path("keywords/suggest/",      mon_views.keyword_suggest,  name="keyword_suggest"),
    path("keywords/add-ajax/",     mon_views.keyword_add_ajax, name="keyword_add_ajax"),
    path("news/<int:pk>/edit/",   mon_views.news_edit,   name="news_edit"),
    path("news/<int:pk>/delete/", mon_views.news_delete, name="news_delete"),
    path("sw.js",         _serve_static('sw.js',         'application/javascript')),
    path("manifest.json", _serve_static('manifest.json', 'application/json')),
    path("icon-192.png",  _serve_static('icon-192.png',  'image/png')),
    path("icon-512.png",  _serve_static('icon-512.png',  'image/png')),
    path("accounts/login/",  RedirectView.as_view(url="/login/",  permanent=False)),
    path("accounts/logout/", RedirectView.as_view(url="/logout/", permanent=False)),
    path("accounts/",  include("django.contrib.auth.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

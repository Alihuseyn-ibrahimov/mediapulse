"""
Smoke testlər — əsas səhifələrin sınmadığını yoxlayır.
Bu testlər deploy-dan əvvəl işlədilir; keçmirsə deploy dayanır.
Məqsəd: dashboard/analitika 500 kimi xətaları CANLIYA çıxmazdan əvvəl tutmaq.
"""
import json
from unittest.mock import patch

from django.test import TestCase, Client, override_settings
from django.contrib.auth.models import User
from django.utils import timezone

from monitor.models import Organization, OrganizationMember, Keyword, NewsResult, TvClip
from monitor import views as mon_views


@override_settings(
    SECURE_SSL_REDIRECT=False,   # test client http göndərir — redirect olmasın
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class SmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Test Təşkilat", slug="test-teskilat")
        cls.user = User.objects.create_user(username="tester", password="testpass123")
        OrganizationMember.objects.create(user=cls.user, organization=cls.org, role="admin")
        Keyword.objects.create(organization=cls.org, word="test açar", is_active=True)
        Keyword.objects.create(organization=cls.org, word="rəqib", is_active=True, is_competitor=True)
        NewsResult.objects.create(
            organization=cls.org, keyword="test açar", title="Test xəbər başlığı",
            link="https://example.com/1", summary="Test xülasə", source="example.com",
            sentiment="MÜSBƏT", saved_at=timezone.now(),
        )
        NewsResult.objects.create(
            organization=cls.org, keyword="rəqib", title="Rəqib xəbəri",
            link="https://example.com/2", summary="Mənfi xəbər", source="example.com",
            sentiment="MƏNFİ", saved_at=timezone.now(),
        )

    def setUp(self):
        self.client = Client()

    # ── Açıq səhifələr ──────────────────────────────────────────────
    def test_landing_all_langs(self):
        for lang in ["az", "ru", "en", "es", "tr"]:
            r = self.client.get(f"/?lang={lang}")
            self.assertEqual(r.status_code, 200, f"landing lang={lang} → {r.status_code}")

    def test_login_page(self):
        self.assertEqual(self.client.get("/login/").status_code, 200)

    def test_demo_page(self):
        self.assertEqual(self.client.get("/demo/").status_code, 200)

    def test_privacy_and_terms_pages(self):
        self.assertEqual(self.client.get("/privacy/").status_code, 200)
        self.assertEqual(self.client.get("/terms/").status_code, 200)

    def test_dashboard_requires_login(self):
        # Login olmadan dashboard login-ə yönləndirməlidir
        self.assertEqual(self.client.get("/dashboard/").status_code, 302)

    # ── Login tələb edən səhifələr ──────────────────────────────────
    def test_authenticated_pages(self):
        self.client.force_login(self.user)
        for path in [
            "/dashboard/",
            "/keywords/",
            "/keywords/analytics/",
            "/press-release/",
            "/post-titles/",
        ]:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, f"{path} → {r.status_code}")

    def test_dashboard_with_filters(self):
        # Son əlavə edilən filtrlər (tarix aralığı, açar söz) sınmasın
        self.client.force_login(self.user)
        r = self.client.get("/dashboard/?days=0&date_from=2026-01-01&date_to=2026-12-31&keyword_filter=rəqib&sentiment=MƏNFİ")
        self.assertEqual(r.status_code, 200)

    def test_dashboard_source_filter(self):
        # Platforma filtri (facebook/youtube/telegram/news) sınmasın
        self.client.force_login(self.user)
        for src in ["facebook", "youtube", "telegram", "news"]:
            r = self.client.get(f"/dashboard/?source_filter={src}")
            self.assertEqual(r.status_code, 200, f"source_filter={src} → {r.status_code}")

    def test_analytics_all_periods(self):
        # days==7 şablon xətası kimi problemləri tut
        self.client.force_login(self.user)
        for days in [7, 14, 30, 90]:
            r = self.client.get(f"/keywords/analytics/?days={days}")
            self.assertEqual(r.status_code, 200, f"analytics days={days} → {r.status_code}")

    # ── Hesabat ixracı (PDF/Excel) ───────────────────────────────────
    def test_export_pdf_default_days(self):
        self.client.force_login(self.user)
        r = self.client.get("/export/pdf/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")

    def test_export_excel_custom_date_range_filters_results(self):
        self.client.force_login(self.user)
        old = NewsResult.objects.create(
            organization=self.org, keyword="test açar", title="Köhnə xəbər",
            link="https://example.com/old", source="example.com",
            sentiment="MÜSBƏT", saved_at=timezone.now() - timezone.timedelta(days=40),
        )
        r = self.client.get(
            f"/export/excel/?date_from={old.saved_at.date()}&date_to={old.saved_at.date()}"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_export_invalid_dates_falls_back_to_days(self):
        self.client.force_login(self.user)
        r = self.client.get("/export/pdf/?date_from=yanlis-tarix&days=7")
        self.assertEqual(r.status_code, 200)

    # ── SEO ─────────────────────────────────────────────────────────
    def test_sitemap_and_robots(self):
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertEqual(self.client.get("/robots.txt").status_code, 200)

    def test_landing_has_seo_tags(self):
        html = self.client.get("/").content.decode()
        self.assertIn('property="og:title"', html)
        self.assertIn('application/ld+json', html)
        self.assertIn('hreflang="ru"', html)

    # ── TV monitorinq / YouTube bölməsi (müştəri dashboard-unda) ──────
    def test_dashboard_shows_tv_section(self):
        self.client.force_login(self.user)
        TvClip.objects.create(organization=self.org, channel="AzTV", keyword="pensiya", video_url="https://x/1.mp4")
        r = self.client.get("/dashboard/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("YouTube / TV Monitorinq", html)
        self.assertIn("pensiya", html)

    def test_tv_clip_ingest_requires_secret(self):
        r = self.client.post(
            "/landing-admin/tv-clips/ingest/",
            data=json.dumps({"channel": "AzTV", "keyword": "test", "videoUrl": "https://x/1.mp4"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)
        self.assertEqual(TvClip.objects.count(), 0)

    def test_tv_clip_ingest_assigns_org(self):
        r = self.client.post(
            "/landing-admin/tv-clips/ingest/",
            data=json.dumps({"channel": "AzTV", "keyword": "test", "videoUrl": "https://x/1.mp4",
                             "orgSlug": self.org.slug}),
            content_type="application/json",
            HTTP_X_INGEST_SECRET=mon_views.TV_CLIP_INGEST_SECRET,
        )
        self.assertEqual(r.status_code, 200)
        clip = TvClip.objects.get()
        self.assertEqual(clip.organization, self.org)

    def test_tv_clip_ingest_creates_news_result(self):
        # TV süjeti PR-monitorinq lentinə (NewsResult) də düşməlidir
        r = self.client.post(
            "/landing-admin/tv-clips/ingest/",
            data=json.dumps({"channel": "AzTV", "keyword": "pensiya",
                             "title": "Pensiyalar artırılır? | AzTV",
                             "videoUrl": "https://tvclips.example/clip1.mp4",
                             "sentiment": "MÜSBƏT", "orgSlug": self.org.slug}),
            content_type="application/json",
            HTTP_X_INGEST_SECRET=mon_views.TV_CLIP_INGEST_SECRET,
        )
        self.assertEqual(r.status_code, 200)
        nr = NewsResult.objects.get(source="TV: AzTV")
        self.assertEqual(nr.organization, self.org)
        self.assertEqual(nr.sentiment, "MÜSBƏT")
        self.assertEqual(nr.link, "https://tvclips.example/clip1.mp4")

    def test_tv_clip_ingest_full_version_updates_link(self):
        # Eyni başlıqlı ikinci ingest (tam versiya) yeni sətir yaratmır, linki yeniləyir
        body = {"channel": "AzTV", "keyword": "pensiya",
                "title": "Pensiyalar artırılır? | AzTV",
                "videoUrl": "https://tvclips.example/piece.mp4",
                "sentiment": "MÜSBƏT", "orgSlug": self.org.slug}
        self.client.post("/landing-admin/tv-clips/ingest/", data=json.dumps(body),
                         content_type="application/json",
                         HTTP_X_INGEST_SECRET=mon_views.TV_CLIP_INGEST_SECRET)
        body["videoUrl"] = "https://tvclips.example/full.mp4"
        self.client.post("/landing-admin/tv-clips/ingest/", data=json.dumps(body),
                         content_type="application/json",
                         HTTP_X_INGEST_SECRET=mon_views.TV_CLIP_INGEST_SECRET)
        rows = NewsResult.objects.filter(source="TV: AzTV")
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().link, "https://tvclips.example/full.mp4")

    def test_dashboard_tv_source_filter(self):
        # source_filter=tv yalnız TV sətirlərini göstərir, news isə TV-ni xaric edir
        NewsResult.objects.create(
            organization=self.org, keyword="pensiya", title="TV süjeti başlığı",
            link="https://tvclips.example/x.mp4", source="TV: AzTV",
            sentiment="MÜSBƏT", saved_at=timezone.now(),
        )
        self.client.force_login(self.user)
        r = self.client.get("/dashboard/?source_filter=tv")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("TV süjeti başlığı", html)
        self.assertNotIn("Test xəbər başlığı", html)
        r = self.client.get("/dashboard/?source_filter=news")
        html = r.content.decode()
        self.assertNotIn("TV süjeti başlığı", html)
        self.assertIn("Test xəbər başlığı", html)

    def test_tv_clip_decide_requires_login(self):
        clip = TvClip.objects.create(organization=self.org, channel="AzTV", keyword="test", video_url="https://x/1.mp4")
        r = self.client.post(f"/tv-clips/{clip.pk}/decide/", {"action": "approve"})
        self.assertEqual(r.status_code, 302)  # login-ə yönləndir

    def test_tv_clip_decide_wrong_org_404(self):
        # başqa təşkilatın klipini təsdiqləmək mümkün olmamalıdır
        other = Organization.objects.create(name="Digər", slug="diger")
        clip = TvClip.objects.create(organization=other, channel="AzTV", keyword="test", video_url="https://x/1.mp4")
        self.client.force_login(self.user)
        r = self.client.post(f"/tv-clips/{clip.pk}/decide/", {"action": "approve"})
        self.assertEqual(r.status_code, 404)

    @patch("urllib.request.urlopen")
    def test_tv_clip_decide_approve(self, mock_urlopen):
        clip = TvClip.objects.create(organization=self.org, channel="AzTV", keyword="test", video_url="https://x/1.mp4")
        self.client.force_login(self.user)
        r = self.client.post(f"/tv-clips/{clip.pk}/decide/", {"action": "approve"})
        self.assertRedirects(r, "/dashboard/#tv", fetch_redirect_response=False)
        clip.refresh_from_db()
        self.assertEqual(clip.status, "approved")
        mock_urlopen.assert_called_once()

    def test_tv_clip_upload_result(self):
        clip = TvClip.objects.create(organization=self.org, channel="AzTV", keyword="test", video_url="https://x/1.mp4", status="approved")
        r = self.client.post(
            "/landing-admin/tv-clips/upload-result/",
            data=json.dumps({"clip_id": clip.pk, "status": "uploaded", "youtube_video_id": "abc123"}),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET=mon_views.N8N_WEBHOOK_SECRET,
        )
        self.assertEqual(r.status_code, 200)
        clip.refresh_from_db()
        self.assertEqual(clip.status, "uploaded")
        self.assertEqual(clip.youtube_video_id, "abc123")

    # ── Bildiriş zəngi feed-i ───────────────────────────────────────
    def test_notifications_feed_requires_login(self):
        r = self.client.get("/notifications/feed/")
        self.assertEqual(r.status_code, 302)  # login-ə yönləndir

    def test_notifications_feed_returns_org_news(self):
        self.client.force_login(self.user)
        r = self.client.get("/notifications/feed/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        # setUpTestData 2 NewsResult yaradıb — hər ikisi qayıtmalıdır
        self.assertEqual(len(data["items"]), 2)
        first = data["items"][0]
        for field in ("id", "title", "sentiment", "source", "keyword", "link", "ts"):
            self.assertIn(field, first)

    def test_notifications_feed_isolated_per_org(self):
        # başqa təşkilatın xəbərləri sızmamalıdır
        other = Organization.objects.create(name="Digər", slug="diger-org")
        NewsResult.objects.create(
            organization=other, keyword="x", title="Digər org xəbəri",
            link="https://example.com/other", source="x", sentiment="MÜSBƏT",
            saved_at=timezone.now(),
        )
        self.client.force_login(self.user)
        data = self.client.get("/notifications/feed/").json()
        titles = [it["title"] for it in data["items"]]
        self.assertNotIn("Digər org xəbəri", titles)
        self.assertEqual(len(data["items"]), 2)

    def test_notifications_feed_tv_type_returns_clips(self):
        TvClip.objects.create(organization=self.org, channel="AzTV", keyword="pensiya",
                               title="Pensiya artımı süjeti", video_url="https://x/1.mp4",
                               status="uploaded")
        self.client.force_login(self.user)
        r = self.client.get("/notifications/feed/?type=tv")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["type"], "tv")
        self.assertEqual(len(data["items"]), 1)
        item = data["items"][0]
        for field in ("id", "title", "status", "status_label", "channel", "keyword", "link", "ts"):
            self.assertIn(field, item)
        self.assertEqual(item["status"], "uploaded")

    def test_notifications_feed_tv_isolated_per_org(self):
        other = Organization.objects.create(name="Digər", slug="diger-org-tv")
        TvClip.objects.create(organization=other, channel="ATV", keyword="y",
                               video_url="https://x/2.mp4")
        TvClip.objects.create(organization=self.org, channel="AzTV", keyword="x",
                               video_url="https://x/1.mp4")
        self.client.force_login(self.user)
        data = self.client.get("/notifications/feed/?type=tv").json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["channel"], "AzTV")

    def test_notifications_feed_default_type_is_pr(self):
        self.client.force_login(self.user)
        r = self.client.get("/notifications/feed/")
        self.assertEqual(r.json()["type"], "pr")

    # ── Çoxlu hesabat e-poçtu ───────────────────────────────────────
    def test_parse_report_emails_splits_and_validates(self):
        # vergül / yeni sətir / nöqtəli vergül / boşluqla ayrılır,
        # yanlış format atılır, təkrarlar (reqistrdən asılı olmayaraq) silinir
        raw = "bir@qurum.az, iki@qurum.az\nUC@qurum.az; yalnis-email  BIR@qurum.az"
        out = mon_views.parse_report_emails(raw)
        self.assertEqual(out, ["bir@qurum.az", "iki@qurum.az", "UC@qurum.az"])

    def test_parse_report_emails_empty(self):
        self.assertEqual(mon_views.parse_report_emails(""), [])
        self.assertEqual(mon_views.parse_report_emails("   yalnis  "), [])

    def test_save_report_settings_stores_multiple(self):
        self.client.force_login(self.user)
        r = self.client.post("/settings/report/", {
            "weekly_report_enabled": "1",
            "report_email": "a@qurum.az, b@qurum.az",
        })
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["count"], 2)
        self.org.refresh_from_db()
        self.assertEqual(self.org.report_email, "a@qurum.az, b@qurum.az")

    def test_do_send_report_delivers_to_all_recipients(self):
        from django.core import mail
        mail.outbox = []
        mon_views._do_send_report(self.org, ["a@qurum.az", "b@qurum.az", "c@qurum.az"])
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(sorted(mail.outbox[0].to), ["a@qurum.az", "b@qurum.az", "c@qurum.az"])
        self.assertTrue(mail.outbox[0].attachments)  # PDF əlavəsi var

    def test_do_send_report_accepts_raw_string(self):
        # geriyə uyğunluq: tək sətir string də qəbul edilib parse olunur
        from django.core import mail
        mail.outbox = []
        mon_views._do_send_report(self.org, "x@qurum.az, y@qurum.az")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(sorted(mail.outbox[0].to), ["x@qurum.az", "y@qurum.az"])

    # ── E-poçt PDF-i antivirus təhlükəsizliyi ───────────────────────
    def _pdf_uri_netlocs(self, pdf_bytes):
        import re
        from urllib.parse import urlparse
        uris = re.findall(rb"/URI\s*\(([^)]*)\)", pdf_bytes)
        return {urlparse(u.decode("latin-1")).netloc.lower() for u in uris}

    def test_email_pdf_has_no_third_party_links(self):
        # E-poçt versiyası üçüncü-tərəf xəbər saytı URL-i DAXİL ETMƏMƏLİDİR
        # (antivirus yanlış-pozitivinin qarşısı). Yalnız birinci-tərəf
        # mediapulse.az keçidinə icazə var.
        qs = NewsResult.objects.filter(organization=self.org)
        pdf = mon_views._build_report_pdf_bytes(self.org, qs, "Test", for_email=True)
        netlocs = self._pdf_uri_netlocs(pdf)
        third_party = {d for d in netlocs if d and not d.endswith("mediapulse.az")}
        self.assertEqual(third_party, set(), f"e-poçt PDF-ində 3-cü tərəf link var: {third_party}")

    def test_download_pdf_keeps_links(self):
        # Yüklənən versiya (for_email=False) linkləri saxlayır — e-poçt
        # antivirusundan keçmədiyi üçün təhlükəsizdir və faydalıdır.
        qs = NewsResult.objects.filter(organization=self.org)
        pdf = mon_views._build_report_pdf_bytes(self.org, qs, "Test", for_email=False)
        netlocs = self._pdf_uri_netlocs(pdf)
        self.assertIn("example.com", netlocs)

    # ── Qaçırılan linklər bazası (MissedLink) ───────────────────────
    def test_missed_link_unique_per_org(self):
        from monitor.models import MissedLink
        from django.db import IntegrityError
        MissedLink.objects.create(organization=self.org, url="https://facebook.com/share/p/x",
                                   category="facebook", report_date="2026-07-22")
        # eyni org+url ikinci dəfə yaradıla bilməz
        with self.assertRaises(IntegrityError):
            MissedLink.objects.create(organization=self.org, url="https://facebook.com/share/p/x",
                                      category="facebook", report_date="2026-07-22")

    def test_missed_link_categorize(self):
        import importlib.util, os
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        spec = importlib.util.spec_from_file_location("lml", os.path.join(root, "load_missed_links.py"))
        lml = importlib.util.module_from_spec(spec); spec.loader.exec_module(lml)
        self.assertEqual(lml.categorize("https://www.facebook.com/share/p/1BR"), "facebook")
        self.assertEqual(lml.categorize("https://youtu.be/abc"), "youtube")
        self.assertEqual(lml.categorize("https://youtube.com/live/x"), "youtube")
        self.assertEqual(lml.categorize("https://report.az/xeber"), "news")

from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    name       = models.CharField(max_length=200, verbose_name="Təşkilat adı")
    slug       = models.SlugField(unique=True, verbose_name="URL adı")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active  = models.BooleanField(default=True, verbose_name="Aktivdir")
    plan       = models.CharField(
        max_length=20,
        choices=[("free", "Pulsuz"), ("basic", "Əsas"), ("pro", "Pro")],
        default="free",
        verbose_name="Plan",
    )
    onboarding_done      = models.BooleanField(default=False, verbose_name="Onboarding tamamlandı")
    notif_on_negative    = models.BooleanField(default=True,  verbose_name="Mənfi xəbərdə bildiriş")
    notif_on_positive    = models.BooleanField(default=False, verbose_name="Müsbət xəbərdə bildiriş")
    notif_daily_summary  = models.BooleanField(default=False, verbose_name="Gündəlik xülasə")
    notif_daily_hour     = models.IntegerField(default=18,    verbose_name="Xülasə saatı (0-23)")
    weekly_report_enabled = models.BooleanField(default=False, verbose_name="Həftəlik PDF hesabat")
    # Bir neçə ünvan: vergül/nöqtəli vergül/boşluq/yeni sətirlə ayrılmış.
    # Emal/doğrulama üçün monitor.views.parse_report_emails istifadə olunur.
    report_email          = models.TextField(blank=True, verbose_name="Hesabat e-poçtları")

    class Meta:
        verbose_name = "Təşkilat"
        verbose_name_plural = "Təşkilatlar"

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name="membership")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    role         = models.CharField(
        max_length=10,
        choices=[("admin", "Admin"), ("viewer", "İzləyici")],
        default="viewer",
        verbose_name="Rol",
    )

    class Meta:
        verbose_name = "Üzv"
        verbose_name_plural = "Üzvlər"

    def __str__(self):
        return f"{self.user.username} — {self.organization.name}"


class Keyword(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="keywords")
    word         = models.CharField(max_length=200, verbose_name="Açar söz")
    is_active      = models.BooleanField(default=True,  verbose_name="Aktivdir")
    is_competitor  = models.BooleanField(default=False, verbose_name="Rəqibdir")
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Açar söz"
        verbose_name_plural = "Açar sözlər"
        unique_together = ("organization", "word")

    def __str__(self):
        return f"{self.word} ({self.organization.name})"


class KeywordAlias(models.Model):
    keyword    = models.ForeignKey(Keyword, on_delete=models.CASCADE, related_name="aliases")
    word       = models.CharField(max_length=200, verbose_name="Əlavə söz")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alias"
        verbose_name_plural = "Aliaslar"
        unique_together = ("keyword", "word")

    def __str__(self):
        return self.word


LANG_CHOICES = [('az', 'AZ'), ('ru', 'RU'), ('en', 'EN'), ('es', 'ES'), ('tr', 'TR')]

class LandingContent(models.Model):
    key        = models.CharField(max_length=100)
    lang       = models.CharField(max_length=5, choices=LANG_CHOICES, default='az')
    value      = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('key', 'lang')
        verbose_name = "Landing məzmunu"
        verbose_name_plural = "Landing məzmunu"

    def __str__(self):
        return f"{self.key} [{self.lang}]"


class DemoRequest(models.Model):
    name       = models.CharField(max_length=200, verbose_name="Ad Soyad")
    company    = models.CharField(max_length=200, verbose_name="Şirkət/Qurum adı")
    contact    = models.CharField(max_length=200, verbose_name="Telefon / E-poçt")
    plan       = models.CharField(max_length=100, blank=True, verbose_name="Seçilmiş plan")
    message    = models.TextField(blank=True, verbose_name="Qeyd")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarix")
    is_read    = models.BooleanField(default=False, verbose_name="Baxılıb")

    class Meta:
        verbose_name = "Demo müraciəti"
        verbose_name_plural = "Demo müraciətləri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.company}"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("CREATE", "Əlavə edildi"),
        ("UPDATE", "Dəyişdirildi"),
        ("DELETE", "Silindi"),
        ("ACTION", "Əməliyyat"),
    ]
    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İstifadəçi")
    action      = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name="Əməliyyat")
    model_name  = models.CharField(max_length=100, verbose_name="Model")
    object_id   = models.CharField(max_length=50, blank=True, verbose_name="Obyekt ID")
    object_repr = models.CharField(max_length=500, blank=True, verbose_name="Obyekt")
    changes     = models.TextField(blank=True, verbose_name="Dəyişikliklər")
    ip_address  = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP ünvan")
    timestamp   = models.DateTimeField(auto_now_add=True, verbose_name="Tarix")

    class Meta:
        verbose_name = "Audit qeydi"
        verbose_name_plural = "Audit arxivi"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.action}] {self.model_name} — {self.user} — {self.timestamp:%d.%m.%Y %H:%M}"


class NewsResult(models.Model):
    SENTIMENT_CHOICES = [
        ("MÜSBƏT",  "Müsbət"),
        ("MƏNFİ",   "Mənfi"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="results")
    keyword      = models.CharField(max_length=200, verbose_name="Açar söz")
    title        = models.TextField(verbose_name="Başlıq")
    summary      = models.TextField(blank=True, verbose_name="Xülasə")
    link         = models.URLField(max_length=500, verbose_name="Link")
    source       = models.CharField(max_length=200, blank=True, verbose_name="Mənbə")
    sentiment    = models.CharField(max_length=10, choices=SENTIMENT_CHOICES, default="MÜSBƏT")
    saved_at     = models.DateTimeField(verbose_name="Saxlanma tarixi")

    class Meta:
        verbose_name = "Xəbər"
        verbose_name_plural = "Xəbərlər"
        ordering = ["-saved_at"]

    def __str__(self):
        return f"[{self.sentiment}] {self.title[:60]}"


class TvClip(models.Model):
    STATUS_CHOICES = [
        ("pending",  "Gözləyir"),
        ("approved", "Təsdiqləndi"),
        ("rejected", "Rədd edildi"),
        ("uploaded", "YouTube-a yükləndi"),
        ("failed",   "Xəta"),
    ]

    organization       = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="tv_clips", null=True, blank=True, verbose_name="Təşkilat")
    channel            = models.CharField(max_length=100, verbose_name="Kanal")
    keyword            = models.CharField(max_length=200, verbose_name="Açar söz")
    title              = models.CharField(max_length=300, blank=True, verbose_name="Başlıq")
    video_url          = models.URLField(max_length=500, verbose_name="Video linki")
    youtube_video_id   = models.CharField(max_length=32, blank=True, verbose_name="YouTube video ID")
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Status")
    n8n_execution_id   = models.CharField(max_length=64, blank=True, verbose_name="n8n icra ID")
    decided_by         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Qərar verən")
    created_at         = models.DateTimeField(auto_now_add=True, verbose_name="Tapılma tarixi")
    decided_at         = models.DateTimeField(null=True, blank=True, verbose_name="Qərar tarixi")

    class Meta:
        verbose_name = "TV klipi"
        verbose_name_plural = "TV klipləri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status}] {self.channel} — {self.keyword}"


class MissedLink(models.Model):
    """İstifadəçinin manual monitorinqdə tapıb sistemin QAÇIRDIĞI xəbər linkləri.
    Məqsəd: (1) monitorinqi hansı sinif mənbədə/kanalda təkmilləşdirmək lazım
    olduğunu izləmək; (2) xüsusən Facebook üçün — Apify inteqrasiyasına
    keçəndə bu "insan tapdığı həqiqət" dəsti ilə Apify-ın tapdıqlarını
    müqayisə edib örtük faizini ölçmək. Hər gün ayrıca partiya (report_date)."""
    CATEGORY_CHOICES = [
        ("facebook", "Facebook"),
        ("youtube",  "YouTube"),
        ("news",     "Xəbər saytı"),
        ("other",    "Digər"),
    ]

    organization    = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="missed_links", verbose_name="Təşkilat")
    url             = models.URLField(max_length=600, verbose_name="Link")
    category        = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other", verbose_name="Kateqoriya")
    report_date     = models.DateField(verbose_name="Xəbərin tarixi")
    note            = models.CharField(max_length=300, blank=True, verbose_name="Qeyd")
    # Sonrakı müqayisə üçün: sistem/Apify bu linki artıq tuta bildimi?
    caught_later    = models.BooleanField(default=False, verbose_name="Sonradan tutuldu")
    created_at      = models.DateTimeField(auto_now_add=True, verbose_name="Əlavə tarixi")

    class Meta:
        verbose_name = "Qaçırılan link"
        verbose_name_plural = "Qaçırılan linklər"
        ordering = ["-report_date", "category"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "url"], name="uniq_org_missed_url"),
        ]

    def __str__(self):
        return f"[{self.report_date}] {self.category}: {self.url[:60]}"

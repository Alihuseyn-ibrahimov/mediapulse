import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.timezone import localtime
from .models import Organization, OrganizationMember, Keyword, KeywordAlias, NewsResult, DemoRequest, AuditLog, TvClip, MissedLink


# ── Audit yardımçıları ────────────────────────────────────────────────────────

def _get_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _obj_to_dict(obj):
    """Model obyektini sadə dict-ə çevirir (audit üçün)."""
    data = {}
    for f in obj._meta.fields:
        try:
            data[f.name] = str(getattr(obj, f.name))
        except Exception:
            pass
    return data


def _diff(old_dict, new_dict):
    """İki dict arasındakı fərqi tapır."""
    changes = {}
    all_keys = set(old_dict) | set(new_dict)
    for k in all_keys:
        ov, nv = old_dict.get(k), new_dict.get(k)
        if ov != nv:
            changes[k] = {"əvvəl": ov, "sonra": nv}
    return changes


def audit(request, action, obj, changes_text=""):
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=obj.__class__.__name__,
        object_id=str(obj.pk) if obj.pk else "",
        object_repr=str(obj)[:500],
        changes=changes_text,
        ip_address=_get_ip(request),
    )


class AuditMixin:
    """Bütün admin siniflərinə qoşulur — save/delete/action-ları arxivləyir."""

    def save_model(self, request, obj, form, change):
        if change:
            try:
                old = _obj_to_dict(self.model.objects.get(pk=obj.pk))
            except Exception:
                old = {}
            super().save_model(request, obj, form, change)
            new = _obj_to_dict(obj)
            diff = _diff(old, new)
            audit(request, "UPDATE", obj, json.dumps(diff, ensure_ascii=False))
        else:
            super().save_model(request, obj, form, change)
            audit(request, "CREATE", obj)

    def delete_model(self, request, obj):
        audit(request, "DELETE", obj, json.dumps(_obj_to_dict(obj), ensure_ascii=False))
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            audit(request, "DELETE", obj, json.dumps(_obj_to_dict(obj), ensure_ascii=False))
        super().delete_queryset(request, queryset)

    def _audit_action(self, request, queryset, description):
        for obj in queryset:
            audit(request, "ACTION", obj, description)


# ── İnline-lar ────────────────────────────────────────────────────────────────

class AliasInline(admin.TabularInline):
    model       = KeywordAlias
    extra       = 1
    fields      = ("word",)
    verbose_name = "Alias"
    verbose_name_plural = "Aliaslar"


class KeywordInline(admin.TabularInline):
    model       = Keyword
    extra       = 1
    fields      = ("word", "is_active")
    show_change_link = True


class MemberInline(admin.TabularInline):
    model       = OrganizationMember
    extra       = 1
    fields      = ("user", "role")


# ── Organization ──────────────────────────────────────────────────────────────

@admin.register(Organization)
class OrganizationAdmin(AuditMixin, admin.ModelAdmin):
    list_display  = ("name", "slug", "plan", "is_active", "notif_badge", "onboarding_done", "created_at")
    list_filter   = ("plan", "is_active", "onboarding_done")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines       = [MemberInline, KeywordInline]
    actions       = ["activate", "deactivate"]

    fieldsets = (
        ("Əsas məlumat", {
            "fields": ("name", "slug", "plan", "is_active")
        }),
        ("Telegram Bildiriş Parametrləri", {
            "fields": (
                "notif_on_negative",
                "notif_on_positive",
                "notif_daily_summary",
                "notif_daily_hour",
            ),
            "classes": ("collapse",),
        }),
        ("Onboarding", {
            "fields": ("onboarding_done",),
            "classes": ("collapse",),
        }),
    )

    def notif_badge(self, obj):
        parts = []
        if obj.notif_on_negative:   parts.append("🔴 Mənfi")
        if obj.notif_on_positive:   parts.append("🟢 Müsbət")
        if obj.notif_daily_summary: parts.append(f"📊 {obj.notif_daily_hour}:00")
        return format_html('<span style="font-size:12px">{}</span>', " | ".join(parts) if parts else "—")
    notif_badge.short_description = "Bildiriş"

    @admin.action(description="✅ Seçilənləri aktiv et")
    def activate(self, request, queryset):
        self._audit_action(request, queryset, "Aktiv edildi")
        queryset.update(is_active=True)

    @admin.action(description="⏸️ Seçilənləri deaktiv et")
    def deactivate(self, request, queryset):
        self._audit_action(request, queryset, "Deaktiv edildi")
        queryset.update(is_active=False)


# ── Keyword ───────────────────────────────────────────────────────────────────

@admin.register(Keyword)
class KeywordAdmin(AuditMixin, admin.ModelAdmin):
    list_display  = ("word", "organization", "alias_count", "is_active", "created_at")
    list_filter   = ("organization", "is_active")
    search_fields = ("word", "organization__name")
    inlines       = [AliasInline]
    actions       = ["activate", "deactivate"]

    def alias_count(self, obj):
        c = obj.aliases.count()
        return f"{c} alias" if c else "—"
    alias_count.short_description = "Aliaslar"

    @admin.action(description="✅ Aktiv et")
    def activate(self, request, queryset):
        self._audit_action(request, queryset, "Aktiv edildi")
        queryset.update(is_active=True)

    @admin.action(description="⏸️ Deaktiv et")
    def deactivate(self, request, queryset):
        self._audit_action(request, queryset, "Deaktiv edildi")
        queryset.update(is_active=False)


@admin.register(KeywordAlias)
class KeywordAliasAdmin(AuditMixin, admin.ModelAdmin):
    list_display  = ("word", "keyword", "keyword_org")
    search_fields = ("word", "keyword__word")
    list_filter   = ("keyword__organization",)

    def keyword_org(self, obj):
        return obj.keyword.organization.name
    keyword_org.short_description = "Təşkilat"


# ── OrganizationMember ────────────────────────────────────────────────────────

@admin.register(OrganizationMember)
class OrganizationMemberAdmin(AuditMixin, admin.ModelAdmin):
    list_display  = ("user", "organization", "role")
    list_filter   = ("role", "organization")
    search_fields = ("user__username", "organization__name")


# ── NewsResult ────────────────────────────────────────────────────────────────

@admin.register(NewsResult)
class NewsResultAdmin(AuditMixin, admin.ModelAdmin):
    list_display   = ("title_short", "organization", "keyword", "sentiment_badge", "source", "saved_at")
    list_filter    = ("organization", "sentiment", "keyword")
    search_fields  = ("title", "keyword", "source")
    date_hierarchy = "saved_at"
    actions        = ["delete_selected", "mark_musbet", "mark_menfi"]
    readonly_fields = ("saved_at",)

    fieldsets = (
        (None, {
            "fields": ("organization", "keyword", "sentiment", "saved_at")
        }),
        ("Məzmun", {
            "fields": ("title", "summary", "link", "source")
        }),
    )

    def title_short(self, obj):
        return obj.title[:65]
    title_short.short_description = "Başlıq"

    def sentiment_badge(self, obj):
        colors = {"MƏNFİ": "#fee2e2", "MÜSBƏT": "#d1fae5"}
        text_c = {"MƏNFİ": "#991b1b", "MÜSBƏT": "#065f46"}
        bg = colors.get(obj.sentiment, "#f3f4f6")
        tc = text_c.get(obj.sentiment, "#374151")
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600">{}</span>',
            bg, tc, obj.sentiment
        )
    sentiment_badge.short_description = "Sentiment"

    @admin.action(description="🟢 Seçilənləri MÜSBƏTə çevir")
    def mark_musbet(self, request, queryset):
        self._audit_action(request, queryset, "Sentiment → MÜSBƏT")
        queryset.update(sentiment="MÜSBƏT")

    @admin.action(description="🔴 Seçilənləri MƏNFİyə çevir")
    def mark_menfi(self, request, queryset):
        self._audit_action(request, queryset, "Sentiment → MƏNFİ")
        queryset.update(sentiment="MƏNFİ")


# ── DemoRequest ───────────────────────────────────────────────────────────────

@admin.register(DemoRequest)
class DemoRequestAdmin(AuditMixin, admin.ModelAdmin):
    list_display   = ("name", "company", "contact", "plan_badge", "is_read", "created_at")
    list_filter    = ("is_read",)
    search_fields  = ("name", "company", "contact")
    date_hierarchy = "created_at"
    readonly_fields = ("name", "company", "contact", "plan", "message", "created_at")
    actions        = ["mark_read", "mark_unread"]

    fieldsets = (
        ("Müraciət", {
            "fields": ("name", "company", "contact", "plan", "message", "created_at")
        }),
        ("Status", {
            "fields": ("is_read",)
        }),
    )

    def plan_badge(self, obj):
        if not obj.plan:
            return "—"
        colors = {"Pulsuz": "#f1f5f9", "Əsas": "#eff6ff", "Pro": "#f0fdf4"}
        bg = next((v for k, v in colors.items() if k in obj.plan), "#f3f4f6")
        return format_html(
            '<span style="background:{};padding:2px 8px;border-radius:8px;font-size:12px;font-weight:600">{}</span>',
            bg, obj.plan
        )
    plan_badge.short_description = "Plan"

    @admin.action(description="✅ Baxıldı olaraq işarələ")
    def mark_read(self, request, queryset):
        self._audit_action(request, queryset, "Baxıldı olaraq işarələndi")
        queryset.update(is_read=True)

    @admin.action(description="🔲 Baxılmadı olaraq işarələ")
    def mark_unread(self, request, queryset):
        self._audit_action(request, queryset, "Baxılmadı olaraq işarələndi")
        queryset.update(is_read=False)


# ── MissedLink (manual tapılan, sistemin qaçırdığı linklər) ────────────────────

@admin.register(MissedLink)
class MissedLinkAdmin(AuditMixin, admin.ModelAdmin):
    list_display   = ("report_date", "category", "url", "organization", "caught_later", "created_at")
    list_filter    = ("category", "caught_later", "organization", "report_date")
    search_fields  = ("url", "note")
    date_hierarchy = "report_date"
    readonly_fields = ("created_at",)
    list_per_page  = 100


# ── TvClip ────────────────────────────────────────────────────────────────────

@admin.register(TvClip)
class TvClipAdmin(AuditMixin, admin.ModelAdmin):
    list_display   = ("channel", "keyword", "organization", "status_badge", "decided_by", "created_at", "decided_at")
    list_filter    = ("status", "channel", "organization")
    search_fields  = ("channel", "keyword", "title", "youtube_video_id")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)

    def status_badge(self, obj):
        colors = {
            "pending":  ("#fef3c7", "#92400e"),
            "approved": ("#eff6ff", "#1e40af"),
            "rejected": ("#fee2e2", "#991b1b"),
            "uploaded": ("#d1fae5", "#065f46"),
            "failed":   ("#fee2e2", "#991b1b"),
        }
        bg, tc = colors.get(obj.status, ("#f3f4f6", "#374151"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600">{}</span>',
            bg, tc, obj.get_status_display()
        )
    status_badge.short_description = "Status"


# ── AuditLog ──────────────────────────────────────────────────────────────────

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display   = ("timestamp_fmt", "user", "action_badge", "model_name", "object_repr_short", "ip_address")
    list_filter    = ("action", "model_name", "user")
    search_fields  = ("object_repr", "changes", "user__username")
    date_hierarchy = "timestamp"
    readonly_fields = ("user", "action", "model_name", "object_id", "object_repr", "changes_pretty", "ip_address", "timestamp")

    fieldsets = (
        ("Əməliyyat", {
            "fields": ("user", "action", "model_name", "object_id", "object_repr", "ip_address", "timestamp")
        }),
        ("Dəyişikliklər", {
            "fields": ("changes_pretty",),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def timestamp_fmt(self, obj):
        t = localtime(obj.timestamp)
        return format_html('<span style="font-size:12px;color:#6b7280">{}</span>', t.strftime("%d.%m.%Y %H:%M:%S"))
    timestamp_fmt.short_description = "Tarix"
    timestamp_fmt.admin_order_field = "timestamp"

    def action_badge(self, obj):
        cfg = {
            "CREATE": ("#d1fae5", "#065f46", "➕ Əlavə"),
            "UPDATE": ("#eff6ff", "#1e40af", "✏️ Dəyişiklik"),
            "DELETE": ("#fee2e2", "#991b1b", "🗑️ Silindi"),
            "ACTION": ("#fef3c7", "#92400e", "⚡ Əməliyyat"),
        }
        bg, tc, label = cfg.get(obj.action, ("#f3f4f6", "#374151", obj.action))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:8px;font-size:12px;font-weight:600">{}</span>',
            bg, tc, label
        )
    action_badge.short_description = "Növ"

    def object_repr_short(self, obj):
        return obj.object_repr[:60] if obj.object_repr else "—"
    object_repr_short.short_description = "Obyekt"

    def changes_pretty(self, obj):
        if not obj.changes:
            return "—"
        try:
            data = json.loads(obj.changes)
            if isinstance(data, dict) and data:
                rows = ""
                for field, val in data.items():
                    if isinstance(val, dict) and "əvvəl" in val:
                        rows += (
                            f'<tr><td style="padding:4px 8px;font-weight:600;color:#374151">{field}</td>'
                            f'<td style="padding:4px 8px;color:#991b1b">{val.get("əvvəl","")}</td>'
                            f'<td style="padding:4px 8px;color:#065f46">{val.get("sonra","")}</td></tr>'
                        )
                    else:
                        rows += (
                            f'<tr><td style="padding:4px 8px;font-weight:600;color:#374151">{field}</td>'
                            f'<td colspan="2" style="padding:4px 8px">{val}</td></tr>'
                        )
                return format_html(
                    '<table style="border-collapse:collapse;font-size:13px;width:100%">'
                    '<tr style="background:#f3f4f6"><th style="padding:4px 8px;text-align:left">Sahə</th>'
                    '<th style="padding:4px 8px;text-align:left">Əvvəl</th>'
                    '<th style="padding:4px 8px;text-align:left">Sonra</th></tr>'
                    '{}</table>',
                    format_html(rows)
                )
        except Exception:
            pass
        return obj.changes[:500]
    changes_pretty.short_description = "Dəyişikliklər"

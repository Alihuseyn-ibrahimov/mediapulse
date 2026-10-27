"""
Sadə IP-əsaslı login cəhd limiti (brute-force qoruması).
Django DB-cache istifadə edir — gunicorn işçiləri arasında paylaşılır.
Cloudflare arxasında olduğu üçün real IP CF-Connecting-IP başlığından oxunur.
"""
from django.core.cache import cache

MAX_ATTEMPTS = 6      # bu qədər səhvdən sonra blok
WINDOW       = 900    # 15 dəqiqə — səhvlərin sayılma pəncərəsi
LOCK         = 900    # 15 dəqiqə — blok müddəti


def _client_ip(request):
    return (request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "?"))


def is_locked(request, scope):
    """Bu IP həmin login növü üçün bloklanıbmı?"""
    return cache.get(f"lock:{scope}:{_client_ip(request)}") is not None


def register_failure(request, scope):
    """Səhv cəhdi qeyd et; həddə çatsa blokla. True → indi bloklandı."""
    ip  = _client_ip(request)
    key = f"fail:{scope}:{ip}"
    n   = (cache.get(key) or 0) + 1
    cache.set(key, n, WINDOW)
    if n >= MAX_ATTEMPTS:
        cache.set(f"lock:{scope}:{ip}", True, LOCK)
        cache.delete(key)
        return True
    return False


def clear(request, scope):
    """Uğurlu girişdən sonra sayğacı sıfırla."""
    ip = _client_ip(request)
    cache.delete(f"fail:{scope}:{ip}")
    cache.delete(f"lock:{scope}:{ip}")

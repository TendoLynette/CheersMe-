from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Dashboard
    path("dashboard/", include("CheersMe.dashboard.urls")),

    # Accounts
    path("accounts/", include("CheersMe.accounts.urls")),

    # Events (ONLY here)
    path("events/", include("CheersMe.events.urls")),

    # Other apps
    path("tickets/", include("CheersMe.tickets.urls")),
    path("notifications/", include("CheersMe.notifications.urls")),
    path("payments/", include("CheersMe.payments.urls")),

    # Home page → redirect to events
    path("", include("CheersMe.events.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

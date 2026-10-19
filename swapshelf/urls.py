from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("market.urls")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

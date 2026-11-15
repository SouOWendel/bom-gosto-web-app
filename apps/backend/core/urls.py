from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("usuario.urls")),
    path("api/", include("pedido.urls")),
    path("api/", include("inventario.urls")),
    path("api/", include("estoque.urls")),
    path("api/", include("producao.urls")),
]

# Só expõe o /admin/ quando DJANGO_ADMIN_ENABLED=1 (ninguém tem is_staff no MVP).
if settings.DJANGO_ADMIN_ENABLED:
    urlpatterns.append(path("admin/", admin.site.urls))

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("usuario.urls")),
    path("api/", include("pedido.urls")),
]



from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.usuarios import views as usuarios_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", usuarios_views.index, name="root"),
    path("", include("apps.usuarios.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.productos.urls")),
    path("", include("apps.clientes.urls")),
    path("", include("apps.pedidos.urls")),
    path("", include("apps.reportes.urls")),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

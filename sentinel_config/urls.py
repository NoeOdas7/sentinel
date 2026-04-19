from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def favicon_view(_request):
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
        "<rect width='64' height='64' rx='16' fill='#000000'/>"
        "<circle cx='32' cy='32' r='22' fill='none' stroke='#1D9E75' stroke-width='1.6' opacity='.85'/>"
        "<circle cx='32' cy='32' r='16' fill='none' stroke='#1D9E75' stroke-width='1' opacity='.45'/>"
        "<circle cx='32' cy='32' r='10' fill='none' stroke='#1D9E75' stroke-width='1' opacity='.3'/>"
        "<line x1='32' y1='10' x2='32' y2='54' stroke='#0F6E56' stroke-width='1' opacity='.35'/>"
        "<line x1='10' y1='32' x2='54' y2='32' stroke='#0F6E56' stroke-width='1' opacity='.35'/>"
        "<path d='M32 32 L32 10 A22 22 0 0 1 53.5 32 Z' fill='#5DCAA5' opacity='.18'/>"
        "<line x1='32' y1='32' x2='32' y2='10' stroke='#5DCAA5' stroke-width='1.8' opacity='.92'/>"
        "<circle cx='41' cy='24' r='2.2' fill='#5DCAA5'/>"
        "<circle cx='25' cy='39' r='1.8' fill='#5DCAA5'/>"
        "<circle cx='32' cy='32' r='2.4' fill='#9FE1CB'/>"
        "</svg>"
    )
    return HttpResponse(svg, content_type="image/svg+xml")

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('favicon.ico', favicon_view, name='favicon'),
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/signals/', include('signals.urls')),
    path('api/v1/actors/', include('actors.urls')),
    path('api/v1/resources/', include('resources.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

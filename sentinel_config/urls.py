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
        "<rect width='64' height='64' rx='16' fill='#0f8f7e'/>"
        "<path d='M32 12l16 6v12c0 11-6.8 17.9-16 22-9.2-4.1-16-11-16-22V18l16-6z' fill='#fff3e4'/>"
        "<circle cx='32' cy='30' r='8' fill='#0f8f7e'/>"
        "<path d='M32 24v12M26 30h12' stroke='#fff3e4' stroke-width='3' stroke-linecap='round'/>"
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

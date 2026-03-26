from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from .models import AuthToken

class OTPTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION','')
        if not auth.startswith('Bearer '): return None
        token_val = auth[7:].strip()
        try:
            token = AuthToken.objects.select_related('user').get(token=token_val, is_active=True, expires_at__gt=timezone.now())
        except AuthToken.DoesNotExist:
            raise AuthenticationFailed('Token invalide ou expiré.')
        if not token.user.is_active: raise AuthenticationFailed('Compte désactivé.')
        return (token.user, token_val)
    def authenticate_header(self, request): return 'Bearer'

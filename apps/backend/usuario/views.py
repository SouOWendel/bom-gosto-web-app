from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import PerfilUsuario

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

class LoginView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]
    def post(self, request):
        login = request.data.get("login")
        senha = request.data.get("senha")
        if not login or not senha:
            return Response({"detail": "login e senha são obrigatórios."}, status=400)
        user = authenticate(request, username=login, password=senha)
        if not user:
            return Response({"detail": "credenciais inválidas."}, status=401)
        auth_login(request, user)
        perfil, _ = PerfilUsuario.objects.get_or_create(user=user)
        return Response({"autenticado": True, "login": user.username, "primeiro_acesso": perfil.primeiro_acesso})

class AlterarSenhaView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        senha_atual = request.data.get("senha_atual")
        nova_senha = request.data.get("nova_senha")
        if not senha_atual or not nova_senha:
            return Response({"detail": "senha_atual e nova_senha são obrigatórias."}, status=400)
        if not request.user.check_password(senha_atual):
            return Response({"detail": "senha atual inválida."}, status=400)
        request.user.set_password(nova_senha)
        request.user.save()
        perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
        perfil.primeiro_acesso = False
        perfil.save()
        update_session_auth_hash(request, request.user)
        return Response({"detail": "senha alterada com sucesso.", "primeiro_acesso": False})

class LogoutView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        auth_logout(request)
        return Response({"detail": "logout realizado com sucesso."})

class MeView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        perfil, _ = PerfilUsuario.objects.get_or_create(user=request.user)
        return Response({"login": request.user.username, "primeiro_acesso": perfil.primeiro_acesso})


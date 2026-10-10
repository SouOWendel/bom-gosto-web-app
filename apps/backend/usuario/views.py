import secrets

from django.conf import settings
from django.db import IntegrityError
from rest_framework.authentication import SessionAuthentication
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Usuario

class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return

# endpoint temporario para criar usuarios locais com senha inicial descartavel
class CadastroTesteView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]

    # define o metodo POST para criar um usuario com login e senha temporaria, retornando a senha temporaria para o usuario
    def post(self, request):
        if not settings.DEBUG:
            return Response({"detail": "endpoint disponível apenas em desenvolvimento."}, status=404)

        # valida se o login foi fornecido e nao esta vazio, retornando erro 400 caso contrario
        login = str(request.data.get("login", "")).strip()
        if not login:
            return Response({"detail": "login é obrigatório."}, status=400)

        # gera uma senha temporaria de 6 digitos aleatorios, utilizando a funcao randbelow do modulo secrets para garantir que a senha seja segura e imprevisivel (e criptografada pelo metodo set_password do modelo Usuario no banco de dados)
        senha_temporaria = str(secrets.randbelow(900000) + 100000)
        try:
            Usuario.objects.create_user(login=login, password=senha_temporaria)
        except IntegrityError:
            return Response({"detail": "esse login já está cadastrado."}, status=409)

        return Response({
            "login": login,
            "senha_temporaria": senha_temporaria,
            "primeiro_acesso": True,
        }, status=201)

# define a view de login, que recebe login e senha, autentica o usuario e cria uma sessao
class LoginView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [AllowAny]
    def post(self, request):
        if request.user.is_authenticated:
            return Response({"detail": "usuário já está logado."}, status=status.HTTP_409_CONFLICT)

        login = request.data.get("login")
        senha = request.data.get("senha")
        if not login or not senha:
            return Response({"detail": "login e senha são obrigatórios."}, status=status.HTTP_400_BAD_REQUEST)
        user = authenticate(request, username=login, password=senha)
        if not user:
            return Response({"detail": "credenciais inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        auth_login(request, user)
        return Response({"autenticado": True, "login": user.login, "primeiro_acesso": user.primeiro_acesso})

# define a view de alteracao de senha, que recebe a senha atual e a nova senha, valida a senha atual e altera a senha do usuario logado

# casos de erro tratados:
# - senha atual ou nova senha nao fornecida
# - senha atual invalida
# - nova senha igual a senha atual
# - nova senha com menos de 8 caracteres
class AlterarSenhaView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        senha_atual = request.data.get("senha_atual")
        nova_senha = request.data.get("nova_senha")
        if not senha_atual or not nova_senha:
            return Response({"detail": "senha_atual e nova_senha são obrigatórias."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(senha_atual):
            return Response({"detail": "senha atual inválida."}, status=status.HTTP_400_BAD_REQUEST)
        
        if senha_atual == nova_senha:
            return Response({"detail": "a nova senha deve ser diferente da senha atual."}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(nova_senha) < 8:
            return Response({"detail": "a nova senha deve ter pelo menos 8 caracteres."}, status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(nova_senha)
        request.user.primeiro_acesso = False
        request.user.save()
        update_session_auth_hash(request, request.user)
        return Response({"detail": "senha alterada com sucesso.", "primeiro_acesso": False})

# define a view de logout, que encerra a sessao do usuario logado
class LogoutView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        auth_logout(request)
        return Response({"detail": "logout realizado com sucesso."})

# define a view de informacoes do usuario logado, lendo diretamente do banco de dados
class MeView(APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({"login": request.user.login, "primeiro_acesso": request.user.primeiro_acesso})


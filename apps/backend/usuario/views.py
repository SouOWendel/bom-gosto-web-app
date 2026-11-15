import secrets

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from .models import Usuario


class CsrfTokenView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrf_token": get_token(request)})

# endpoint temporario para criar usuarios locais com senha inicial descartavel
# cria usuarios descartáveis somente em ambiente de desenvolvimento
class CadastroTesteView(APIView):
    permission_classes = [AllowAny]

    @method_decorator(csrf_protect)
    # define o metodo POST para criar um usuario com login e senha temporaria, retornando a senha temporaria para o usuario
    def post(self, request):
        if not settings.TEST_USER_REGISTRATION_ENABLED:
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
# Autentica login e senha e inicia a sessão do usuário.
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @method_decorator(csrf_protect)
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
# - nova senha recusada pelos AUTH_PASSWORD_VALIDATORS
# Troca a senha provisória e libera o acesso normal às rotas protegidas.
class AlterarSenhaView(APIView):
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
        
        try:
            validate_password(nova_senha, user=request.user)
        except DjangoValidationError as erro:
            return Response({"detail": " ".join(erro.messages)}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(nova_senha)
        request.user.primeiro_acesso = False
        request.user.save()
        update_session_auth_hash(request, request.user)
        return Response({"detail": "senha alterada com sucesso.", "primeiro_acesso": False})

# define a view de logout, que encerra a sessao do usuario logado
# Encerra a sessão autenticada no navegador.
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        auth_logout(request)
        return Response({"detail": "logout realizado com sucesso."})

# define a view de informacoes do usuario logado, lendo diretamente do banco de dados
# Retorna os dados básicos do usuário associado à sessão atual.
class MeView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response({"login": request.user.login, "primeiro_acesso": request.user.primeiro_acesso})

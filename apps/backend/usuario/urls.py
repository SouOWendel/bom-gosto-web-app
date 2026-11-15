from django.urls import path
from .views import (
    AlterarSenhaView,
    CadastroTesteView,
    CsrfTokenView,
    LoginView,
    LogoutView,
    MeView,
)

# publica autenticacao, sessao e troca obrigatoria da senha inicial
urlpatterns = [
    path("auth/csrf/", CsrfTokenView.as_view()),
    path("auth/cadastro-teste/", CadastroTesteView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/alterar-senha/", AlterarSenhaView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
]

from django.urls import path
from .views import CadastroTesteView, LoginView, AlterarSenhaView, LogoutView, MeView

<<<<<<< HEAD
# Publica autenticação, sessão e troca obrigatória da senha inicial.
=======
>>>>>>> b6e39bc0499831f6b95da7f3f78788a3f1195ef8
urlpatterns = [
    path("auth/cadastro-teste/", CadastroTesteView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/alterar-senha/", AlterarSenhaView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
]

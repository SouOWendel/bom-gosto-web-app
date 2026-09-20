from django.urls import path
from .views import LoginView, AlterarSenhaView, LogoutView, MeView

urlpatterns = [
    path("auth/login/", LoginView.as_view()),
    path("auth/alterar-senha/", AlterarSenhaView.as_view()),
    path("auth/logout/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
]

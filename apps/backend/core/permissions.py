from rest_framework.permissions import BasePermission


# Bloqueia as rotas operacionais até a senha provisória ser trocada.
class SenhaInicialAlterada(BasePermission):
    message = "Altere a senha inicial antes de acessar o sistema."

    def has_permission(self, request, view):
        return not getattr(request.user, "primeiro_acesso", True)

import secrets

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from usuario.models import Usuario


# Cria a conta inicial pela linha de comando e revela a senha provisória uma única vez.
class Command(BaseCommand):
    help = "Cria a conta inicial fora da API e exibe a senha provisória uma única vez."

    def add_arguments(self, parser):
        parser.add_argument("login")

    def handle(self, *args, **options):
        login = options["login"].strip()
        if not login:
            raise CommandError("Informe um login válido.")
        senha = secrets.token_urlsafe(18)
        try:
            Usuario.objects.create_user(login=login, password=senha, primeiro_acesso=True)
        except IntegrityError as erro:
            raise CommandError("Esse login já está cadastrado.") from erro
        self.stdout.write(self.style.SUCCESS(f"Conta criada para {login}. Senha provisória (exibida uma vez): {senha}"))

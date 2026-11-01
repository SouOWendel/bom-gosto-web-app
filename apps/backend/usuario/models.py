from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

# manager que cria usuarios e armazena senhas usando o hash do Django
# `extra_fields` permite informar outros campos do model na criacao
# Cria usuários e armazena senhas usando o hash seguro fornecido pelo Django.
class UsuarioManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError('O login é obrigatório.')
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # mantem a interface esperada pelo Django. cria um usuario comum sem permissoes administrativas
    def create_superuser(self, login, password=None, **extra_fields):
        return self.create_user(login, password, **extra_fields)

# model de autenticacao mapeado para a tabela `usuario`
# Mapeia a conta do sistema à tabela Usuario existente no banco.
class Usuario(AbstractBaseUser):
    id_usuario = models.AutoField(primary_key=True)
    login = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255, db_column='senha')
    primeiro_acesso = models.BooleanField(default=True)

    last_login = None

    objects = UsuarioManager()

    USERNAME_FIELD = 'login'

    class Meta:
        db_table = 'usuario'

    # define que o usuario esta sempre ativo
    @property
    def is_active(self):
        return True

    # define que o usuario nao possui permissoes administrativas
    @property
    def is_staff(self):
        return False

    def __str__(self):
        return self.login

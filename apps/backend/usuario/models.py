from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

# representa o gerenciador de usuarios personalizado, que define criacao de usuarios e senha (ja criptografada)
# recebe parametro extra_fields para permitir a extensao do modelo de usuario no futuro, caso seja necessario adicionar novos campos
class UsuarioManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError('O login é obrigatório.')
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # cria um superusuario com permissoes administrativas, utilizando o mesmo metodo de criacao de usuario
    def create_superuser(self, login, password=None, **extra_fields):
        return self.create_user(login, password, **extra_fields)

# representa diretamente a tabela "usuario" do banco de dados
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
        managed = False

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

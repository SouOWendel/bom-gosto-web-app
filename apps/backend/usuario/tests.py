from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import Usuario

URL_CADASTRO = "/api/auth/cadastro-teste/"
URL_LOGIN = "/api/auth/login/"
URL_ALTERAR_SENHA = "/api/auth/alterar-senha/"
URL_LOGOUT = "/api/auth/logout/"
URL_ME = "/api/auth/me/"

SENHA_INICIAL = "123456"
SENHA_NOVA = "senha-nova-segura"


# testes de CSRF ja existentes na dev (mantidos sem alteracao)
class AuthCsrfTests(TestCase):
    def setUp(self):
        self.password = "senha-local-de-teste"
        self.user = Usuario.objects.create_user(
            login="csrf-teste",
            password=self.password,
            primeiro_acesso=False,
        )
        self.client = APIClient(enforce_csrf_checks=True)

    def test_csrf_endpoint_sets_cookie_and_returns_token(self):
        response = self.client.get("/api/auth/csrf/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", self.client.cookies)
        self.assertTrue(response.data["csrf_token"])

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            "/api/auth/login/",
            {"login": self.user.login, "senha": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertNotIn("sessionid", self.client.cookies)

    def test_session_auth_mutations_require_csrf_token(self):
        csrf = self.client.get("/api/auth/csrf/").data["csrf_token"]
        login = self.client.post(
            "/api/auth/login/",
            {"login": self.user.login, "senha": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

        domain_write_without_token = self.client.post(
            "/api/pedido/",
            {},
            format="json",
        )
        self.assertEqual(domain_write_without_token.status_code, 403)

        csrf = self.client.get("/api/auth/csrf/").data["csrf_token"]

        logout_without_token = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
        )
        self.assertEqual(logout_without_token.status_code, 403)

        logout = self.client.post(
            "/api/auth/logout/",
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )
        self.assertEqual(logout.status_code, 200)

    @override_settings(TEST_USER_REGISTRATION_ENABLED=False)
    def test_test_registration_is_hidden_when_not_explicitly_enabled(self):
        csrf = self.client.get("/api/auth/csrf/").data["csrf_token"]
        response = self.client.post(
            "/api/auth/cadastro-teste/",
            {"login": "cadastro-desabilitado"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Usuario.objects.filter(login="cadastro-desabilitado").exists())

    @override_settings(DEBUG=True, TEST_USER_REGISTRATION_ENABLED=True)
    def test_enabled_test_registration_still_requires_csrf(self):
        response_without_token = self.client.post(
            "/api/auth/cadastro-teste/",
            {"login": "cadastro-com-csrf"},
            format="json",
        )
        self.assertEqual(response_without_token.status_code, 403)

        csrf = self.client.get("/api/auth/csrf/").data["csrf_token"]
        response = self.client.post(
            "/api/auth/cadastro-teste/",
            {"login": "cadastro-com-csrf"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf,
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(Usuario.objects.filter(login="cadastro-com-csrf").exists())


# testes do model Usuario e do manager que cria usuarios com senha criptografada
class UsuarioModelTests(APITestCase):
    def test_create_user_criptografa_a_senha(self):
        usuario = Usuario.objects.create_user(login="maria", password=SENHA_INICIAL)

        self.assertNotEqual(usuario.password, SENHA_INICIAL)
        self.assertTrue(usuario.check_password(SENHA_INICIAL))

    def test_novo_usuario_comeca_em_primeiro_acesso(self):
        usuario = Usuario.objects.create_user(login="maria", password=SENHA_INICIAL)

        self.assertTrue(usuario.primeiro_acesso)

    def test_create_user_exige_login(self):
        with self.assertRaises(ValueError):
            Usuario.objects.create_user(login="", password=SENHA_INICIAL)

    def test_usuario_ativo_e_sem_permissao_administrativa(self):
        usuario = Usuario.objects.create_user(login="maria", password=SENHA_INICIAL)

        self.assertTrue(usuario.is_active)
        self.assertFalse(usuario.is_staff)
        self.assertEqual(str(usuario), "maria")


# testes do endpoint temporario de cadastro (depende de TEST_USER_REGISTRATION_ENABLED)
class CadastroTesteApiTests(APITestCase):
    @override_settings(TEST_USER_REGISTRATION_ENABLED=True)
    def test_cadastra_usuario_com_senha_temporaria_de_seis_digitos(self):
        resposta = self.client.post(URL_CADASTRO, {"login": "novo"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data["login"], "novo")
        self.assertTrue(resposta.data["primeiro_acesso"])
        self.assertEqual(len(resposta.data["senha_temporaria"]), 6)
        usuario = Usuario.objects.get(login="novo")
        self.assertTrue(usuario.check_password(resposta.data["senha_temporaria"]))

    @override_settings(TEST_USER_REGISTRATION_ENABLED=True)
    def test_rejeita_login_vazio(self):
        resposta = self.client.post(URL_CADASTRO, {"login": "   "}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(TEST_USER_REGISTRATION_ENABLED=True)
    def test_rejeita_login_duplicado(self):
        Usuario.objects.create_user(login="repetido", password=SENHA_INICIAL)

        resposta = self.client.post(URL_CADASTRO, {"login": "repetido"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_409_CONFLICT)

    @override_settings(TEST_USER_REGISTRATION_ENABLED=False)
    def test_endpoint_indisponivel_fora_do_ambiente_de_desenvolvimento(self):
        resposta = self.client.post(URL_CADASTRO, {"login": "novo"}, format="json")

        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(Usuario.objects.filter(login="novo").exists())


# testes de login, sessao (/me) e logout
class LoginApiTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            login="maria", password=SENHA_INICIAL
        )

    def test_login_valido_retorna_primeiro_acesso(self):
        resposta = self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data["autenticado"])
        self.assertEqual(resposta.data["login"], "maria")
        self.assertTrue(resposta.data["primeiro_acesso"])

    def test_login_com_senha_errada_retorna_401(self):
        resposta = self.client.post(
            URL_LOGIN, {"login": "maria", "senha": "errada"}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_com_usuario_inexistente_retorna_401(self):
        resposta = self.client.post(
            URL_LOGIN, {"login": "ninguem", "senha": SENHA_INICIAL}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_exige_login_e_senha(self):
        sem_senha = self.client.post(URL_LOGIN, {"login": "maria"}, format="json")
        sem_login = self.client.post(URL_LOGIN, {"senha": SENHA_INICIAL}, format="json")

        self.assertEqual(sem_senha.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sem_login.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_com_sessao_ativa_retorna_conflito(self):
        self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

        resposta = self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

        self.assertEqual(resposta.status_code, status.HTTP_409_CONFLICT)

    def test_me_retorna_dados_do_usuario_logado(self):
        self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

        resposta = self.client.get(URL_ME)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data["login"], "maria")
        self.assertTrue(resposta.data["primeiro_acesso"])

    def test_me_exige_autenticacao(self):
        resposta = self.client.get(URL_ME)

        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_logout_encerra_a_sessao(self):
        self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

        resposta = self.client.post(URL_LOGOUT)
        depois = self.client.get(URL_ME)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn(
            depois.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_logout_exige_autenticacao(self):
        resposta = self.client.post(URL_LOGOUT)

        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


# testes da troca obrigatoria da senha inicial
class AlterarSenhaApiTests(APITestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            login="maria", password=SENHA_INICIAL
        )
        self.client.post(
            URL_LOGIN, {"login": "maria", "senha": SENHA_INICIAL}, format="json"
        )

    def _alterar(self, senha_atual=SENHA_INICIAL, nova_senha=SENHA_NOVA):
        return self.client.post(
            URL_ALTERAR_SENHA,
            {"senha_atual": senha_atual, "nova_senha": nova_senha},
            format="json",
        )

    def test_altera_senha_e_encerra_primeiro_acesso(self):
        resposta = self._alterar()

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertFalse(resposta.data["primeiro_acesso"])
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(SENHA_NOVA))
        self.assertFalse(self.usuario.primeiro_acesso)

    def test_sessao_continua_valida_apos_trocar_a_senha(self):
        self._alterar()

        resposta = self.client.get(URL_ME)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertFalse(resposta.data["primeiro_acesso"])

    def test_rejeita_campos_ausentes(self):
        sem_nova = self.client.post(
            URL_ALTERAR_SENHA, {"senha_atual": SENHA_INICIAL}, format="json"
        )
        sem_atual = self.client.post(
            URL_ALTERAR_SENHA, {"nova_senha": SENHA_NOVA}, format="json"
        )

        self.assertEqual(sem_nova.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sem_atual.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejeita_senha_atual_invalida(self):
        resposta = self._alterar(senha_atual="errada")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(SENHA_INICIAL))

    def test_rejeita_nova_senha_igual_a_atual(self):
        resposta = self._alterar(nova_senha=SENHA_INICIAL)

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejeita_nova_senha_com_menos_de_oito_caracteres(self):
        resposta = self._alterar(nova_senha="curta12")

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.primeiro_acesso)

    def test_exige_autenticacao(self):
        self.client.post(URL_LOGOUT)

        resposta = self._alterar()

        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
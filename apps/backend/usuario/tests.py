from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Usuario


class AuthCsrfTests(TestCase):
    def setUp(self):
        self.password = "senha-local-de-teste"
        self.user = Usuario.objects.create_user(
            login="csrf-teste",
            password=self.password,
            primeiro_acesso=False,
        )
        self.client = APIClient(enforce_csrf_checks=True)
        # o limite de tentativas de login fica no cache; zera entre os testes
        cache.clear()

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


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        Usuario.objects.create_user(login="limite-teste", password="senha-correta-123", primeiro_acesso=False)

    # depois de 5 tentativas por minuto o login responde 429, mesmo com a senha certa
    def test_login_bloqueia_apos_muitas_tentativas(self):
        client = APIClient()
        for _ in range(5):
            resposta = client.post("/api/auth/login/", {"login": "limite-teste", "senha": "errada"}, format="json")
            self.assertEqual(resposta.status_code, 401)
        bloqueada = client.post("/api/auth/login/", {"login": "limite-teste", "senha": "senha-correta-123"}, format="json")
        self.assertEqual(bloqueada.status_code, 429)


class AdminDesligadoTests(TestCase):
    # o /admin/ do Django nao fica exposto por padrao
    def test_admin_nao_responde_por_padrao(self):
        self.assertEqual(self.client.get("/admin/").status_code, 404)

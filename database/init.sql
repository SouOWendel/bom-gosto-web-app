-- executado automaticamente somente ao inicializar um volume PostgreSQL vazio
-- este script cria a extensao, e o backend aplica migrations ao iniciar
-- depois das migrations, rode manualmente `python manage.py seed_desenvolvimento`
-- para carregar os dados de exemplo

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

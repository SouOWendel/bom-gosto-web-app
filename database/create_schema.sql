-- =====================================================================
-- 01_criar_schema.sql
-- schema inicial do sistema da confeitaria bom gosto (postgresql).
-- pre-requisito: banco db_confeitaria ja criado (create_database.sql) e
-- script executado conectado a ele.
-- a transacao garante que ou todas as tabelas sao criadas, ou nenhuma.
-- =====================================================================

BEGIN;
-- tabelas independentes (nao dependem de nenhuma outra)


-- usuario: login unico do sistema.
-- regras:
--   - o login é unico e obrigatorio.
--   - a senha é guardada apenas como hash (ex: bcrypt), nunca em texto puro.
--   - primeiro_acesso indica se o usuario ainda precisa trocar a senha inicial.
CREATE TABLE usuario (
    id_usuario       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    login            VARCHAR(50)  NOT NULL UNIQUE,
    senha            VARCHAR(255) NOT NULL,
    primeiro_acesso  BOOLEAN      NOT NULL DEFAULT TRUE
);

-- cliente: quem faz encomendas.
-- regras:
--   - nome e telefone sao obrigatorios. endereco é opcional.
--   - o cliente é obrigatorio somente em pedidos externos (ver tabela pedido).
CREATE TABLE cliente (
    id_cliente  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    telefone    VARCHAR(20) NOT NULL,
    endereco    VARCHAR(200)
);

-- receita: modo de preparo base de um doce ou massa.
-- regras:
--   - rendimento_quantidade: quanto a receita rende. se informado, deve ser > 0.
--   - custo_calculado: soma do custo dos ingredientes (valor derivado, calculado
--     a partir de receita_ingrediente e ingrediente.custo_unitario).
--   - os ingredientes de cada receita ficam em receita_ingrediente.
CREATE TABLE receita (
    id_receita             INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                   VARCHAR(100) NOT NULL,
    rendimento_quantidade  NUMERIC(10,2) CHECK (rendimento_quantidade > 0),
    custo_calculado        NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (custo_calculado >= 0)
);

-- ingrediente: materia-prima usada nas receitas.
-- regras:
--   - quantidade_disponivel: saldo atual em estoque, nunca negativo.
--   - quantidade_minima: nivel de alerta. abaixo dele o ingrediente precisa
--     ser reposto.
--   - unidade_medida: unidade em que todas as quantidades do ingrediente sao
--     expressas (inclusive em receita_ingrediente).
--   - custo_unitario: custo por unidade de medida, nunca negativo.
--   - a validade nao fica aqui. ela é registrada em cada entrada, na tabela
--     movimentacao_inventario, o que permite controlar lotes com validades
--     diferentes.
CREATE TABLE ingrediente (
    id_ingrediente         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome                   VARCHAR(100) NOT NULL,
    quantidade_disponivel  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (quantidade_disponivel >= 0),
    quantidade_minima      NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (quantidade_minima >= 0),
    unidade_medida         VARCHAR(10)   NOT NULL CHECK (unidade_medida IN ('g', 'kg', 'ml', 'l', 'unidade')),
    custo_unitario         NUMERIC(10,2) NOT NULL CHECK (custo_unitario >= 0)
);


-- produto, pedido e itens do pedido


-- produto: item do catalogo que a confeitaria vende.
-- regras:
--   - pode estar ligado a uma receita (receita_id). se a receita for apagada,
--     o produto permanece, apenas sem receita.
--   - preco_venda é o preco atual do catalogo. o preco cobrado em cada venda
--     fica registrado em item_pedido.preco_unitario.
CREATE TABLE produto (
    id_produto   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receita_id   INT REFERENCES receita (id_receita) ON DELETE SET NULL,
    nome         VARCHAR(100) NOT NULL,
    preco_venda  NUMERIC(10,2) NOT NULL CHECK (preco_venda >= 0)
);

-- pedido: encomenda ou venda registrada.
-- regras:
--   - tipo: 'interno' ou 'externo'.
--   - subtipo: 'vitrine' ou 'personalizado'. obrigatorio em pedido externo e
--     proibido em pedido interno (chk_subtipo_conforme_tipo).
--   - cliente: obrigatorio em pedido externo, opcional em interno
--     (chk_cliente_pedido_externo).
--   - um cliente com pedidos nao pode ser apagado (on delete restrict), para
--     nao quebrar a regra acima nem perder historico.
--   - status: ciclo de vida do pedido, com valores fixos. comeca em
--     'pedido_feito'. sequencia prevista: 'pedido_feito', 'pagamento_parcial'
--     (sinal pago), 'pedido_em_producao', 'pagamento_total', 'pedido_concluido'.
--     'pedido_cancelado' pode ocorrer ao longo do fluxo (ver tabela cancelamento).
--     a ordem das transicoes é controlada pela aplicacao, nao pelo banco.
--   - valor_total: valor do pedido. valor_sinal: entrada paga antecipadamente,
--     nunca maior que o total (chk_sinal_menor_que_total).
--   - sinal de 50%: em pedido externo, valor_sinal so pode ser 0 (sinal ainda
--     nao pago) ou exatamente 50% do valor_total, arredondado a 2 casas
--     (chk_sinal_externo_50_por_cento). em pedido interno nao ha regra de sinal.
--   - data_entrega, horario_entrega, endereco_entrega e forma_pagamento sao
--     opcionais, pois dependem do tipo de pedido.
CREATE TABLE pedido (
    id_pedido         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id        INT REFERENCES cliente (id_cliente) ON DELETE RESTRICT,
    tipo              VARCHAR(20) NOT NULL CHECK (tipo IN ('interno', 'externo')),
    subtipo           VARCHAR(20) CHECK (subtipo IN ('vitrine', 'personalizado')),
    status            VARCHAR(20) NOT NULL DEFAULT 'pedido_feito'
    CHECK (status IN (
            'pedido_feito', 'pagamento_parcial', 'pedido_em_producao','pagamento_total','pedido_concluido', 'pedido_cancelado'
        )),
    data_entrega      DATE,
    horario_entrega   TIME,
    valor_total       NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (valor_total >= 0),
    valor_sinal       NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (valor_sinal >= 0),
    endereco_entrega  VARCHAR(200),
    forma_pagamento   VARCHAR(30),

    CONSTRAINT chk_subtipo_conforme_tipo CHECK (
        (tipo = 'externo' AND subtipo IS NOT NULL) OR
        (tipo = 'interno' AND subtipo IS NULL)
    ),
    CONSTRAINT chk_cliente_pedido_externo CHECK (
        tipo = 'interno' OR cliente_id IS NOT NULL
    ),
    CONSTRAINT chk_sinal_menor_que_total CHECK (valor_sinal <= valor_total),
    CONSTRAINT chk_sinal_externo_50_por_cento CHECK (
        tipo = 'interno' OR valor_sinal = 0 OR valor_sinal = ROUND(valor_total * 0.5, 2)
    )
);

-- item_pedido: cada linha de um pedido.
-- regras:
--   - todo item pertence a um pedido. se o pedido for apagado, os itens vao junto.
--   - o item referencia um produto do catalogo OU uma receita (item
--     personalizado), nunca os dois e nunca nenhum (chk_item_referencia).
--   - preco_unitario: preco cobrado no momento da venda. guarda o historico,
--     mesmo que o preco do produto mude depois.
--   - custo_unitario: custo do item no momento da venda (vem do custo do lote
--     ou da producao). junto com o preco, permite calcular o lucro da venda
--     nos relatorios e no componente de financas.
--   - quantidade: numero de unidades (itens de produto).
--   - quantidade_peso: peso do item, quando vendido por peso (ex: bolo).
--   - recheio e decoracao: detalhes de itens personalizados.
--   - produto e receita usados em itens nao podem ser apagados (restrict).
CREATE TABLE item_pedido (
    id_item_pedido   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id        INT NOT NULL REFERENCES pedido (id_pedido) ON DELETE CASCADE,
    produto_id       INT REFERENCES produto (id_produto) ON DELETE RESTRICT,
    receita_id       INT REFERENCES receita (id_receita) ON DELETE RESTRICT,
    quantidade       INT,
    preco_unitario   NUMERIC(10,2) NOT NULL CHECK (preco_unitario >= 0),
    custo_unitario   NUMERIC(10,2) CHECK (custo_unitario >= 0),
    recheio          VARCHAR(100),
    quantidade_peso  NUMERIC(10,2) CHECK (quantidade_peso > 0),
    decoracao        VARCHAR(200),

    CONSTRAINT chk_item_referencia CHECK ((produto_id IS NULL) <> (receita_id IS NULL))
);

-- producao e estoque


-- producao: registro de cada preparo de uma receita.
-- regras:
--   - sempre ligada a uma receita, que nao pode ser apagada enquanto houver
--     producao (restrict).
--   - pedido_id opcional: preenchido quando a producao atende um pedido
--     especifico. vazio quando é producao para o estoque.
--   - quantidade_produzida deve ser > 0. custo_total é o custo dos ingredientes
--     consumidos (valor derivado).
--   - data_producao assume a data atual por padrao.
CREATE TABLE producao (
    id_producao           INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    receita_id            INT NOT NULL REFERENCES receita (id_receita) ON DELETE RESTRICT,
    pedido_id             INT REFERENCES pedido (id_pedido) ON DELETE SET NULL,
    quantidade_produzida  NUMERIC(10,2) CHECK (quantidade_produzida > 0),
    custo_total           NUMERIC(10,2) CHECK (custo_total >= 0),
    data_producao         DATE NOT NULL DEFAULT CURRENT_DATE
);

-- estoque_produto: lotes de produtos prontos para venda.
-- regras:
--   - cada lote pertence a um produto e tem origem em uma producao
--     (producao_id obrigatorio), o que permite rastrear de onde veio.
--   - o mesmo produto pode ter varios lotes, cada um com sua validade.
--   - quantidade_disponivel: saldo do lote, nunca negativo.
--   - preco_final e custo: valores do lote, nunca negativos.
CREATE TABLE estoque_produto (
    id_estoque_produto     INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    produto_id             INT NOT NULL REFERENCES produto (id_produto) ON DELETE RESTRICT,
    producao_id            INT NOT NULL REFERENCES producao (id_producao) ON DELETE RESTRICT,
    quantidade_disponivel  NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (quantidade_disponivel >= 0),
    data_validade          DATE,
    preco_final            NUMERIC(10,2) CHECK (preco_final >= 0),
    custo                  NUMERIC(10,2) CHECK (custo >= 0)
);

-- receita_ingrediente: composicao de cada receita (relacao n:n).
-- regras:
--   - a chave composta impede repetir o mesmo ingrediente na mesma receita.
--   - quantidade_necessaria deve ser > 0, na unidade de medida do ingrediente.
--   - apagar uma receita apaga sua composicao. um ingrediente usado em alguma
--     receita nao pode ser apagado (restrict).
CREATE TABLE receita_ingrediente (
    receita_id             INT NOT NULL REFERENCES receita (id_receita) ON DELETE CASCADE,
    ingrediente_id         INT NOT NULL REFERENCES ingrediente (id_ingrediente) ON DELETE RESTRICT,
    quantidade_necessaria  NUMERIC(10,2) NOT NULL CHECK (quantidade_necessaria > 0),
    PRIMARY KEY (receita_id, ingrediente_id)
);

-- movimentacao_inventario: historico de entradas e saidas de ingredientes.
-- regras:
--   - tipo: 'entrada' (compra, reposicao) ou 'saida' (consumo em producao).
--   - quantidade sempre positiva. o sentido é dado pelo tipo.
--   - custo_unitario: custo pago por unidade na compra. obrigatorio nas
--     entradas (chk_entrada_com_custo) e base para os gastos com ingredientes
--     nos relatorios e em financas.
--   - data_validade: validade do lote comprado, informada nas entradas. permite
--     ter varias compras do mesmo ingrediente com validades diferentes.
--   - producao_id opcional: preenchido nas saidas geradas por uma producao,
--     registrando quais ingredientes e quantidades foram usados nela.
--   - o ingrediente nao pode ser apagado se tiver movimentacoes (restrict).
CREATE TABLE movimentacao_inventario (
    id_movimentacao_inventario  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ingrediente_id              INT NOT NULL REFERENCES ingrediente (id_ingrediente) ON DELETE RESTRICT,
    producao_id                 INT REFERENCES producao (id_producao) ON DELETE SET NULL,
    tipo                        VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade                  NUMERIC(10,2) NOT NULL CHECK (quantidade > 0),
    custo_unitario              NUMERIC(10,2) CHECK (custo_unitario >= 0),
    data_validade               DATE,
    data_movimentacao           TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_entrada_com_custo CHECK (tipo = 'saida' OR custo_unitario IS NOT NULL)
);

-- movimentacao_estoque: historico de entradas e saidas de produtos prontos.
-- regras:
--   - tipo: 'entrada' (producao, cancelamento devolvido ao estoque) ou
--     'saida' (venda, perda).
--   - quantidade sempre positiva. o sentido é dado pelo tipo.
--   - pedido_id opcional: preenchido quando a movimentacao vem de um pedido.
--   - o lote nao pode ser apagado se tiver movimentacoes (restrict).
CREATE TABLE movimentacao_estoque (
    id_movimentacao_estoque  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    estoque_produto_id       INT NOT NULL REFERENCES estoque_produto (id_estoque_produto) ON DELETE RESTRICT,
    pedido_id                INT REFERENCES pedido (id_pedido) ON DELETE SET NULL,
    tipo                     VARCHAR(20) NOT NULL CHECK (tipo IN ('entrada', 'saida')),
    quantidade               NUMERIC(10,2) NOT NULL CHECK (quantidade > 0),
    data_movimentacao        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- financeiro, cancelamento e agenda


-- transacao: movimentacoes financeiras.
-- regras:
--   - tipo: 'sinal' (entrada antecipada), 'quitacao' (pagamento final) ou
--     'despesa' (gasto sem pedido associado).
--   - pedido_id opcional (despesas nao tem pedido).
--   - um pedido com transacoes nao pode ser apagado (restrict), para preservar
--     o historico financeiro.
CREATE TABLE transacao (
    id_transacao  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id     INT REFERENCES pedido (id_pedido) ON DELETE RESTRICT,
    valor         NUMERIC(10,2) NOT NULL CHECK (valor >= 0),
    tipo          VARCHAR(20) NOT NULL CHECK (tipo IN ('sinal', 'quitacao', 'despesa')),
    data          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- cancelamento: registro do cancelamento de um pedido.
-- regras:
--   - cada pedido so pode ser cancelado uma vez (unique em pedido_id).
--   - destino: 'estoque' (produto pronto volta ao estoque) ou 'perda'
--     (produto descartado).
--   - o pedido nao pode ser apagado depois de cancelado (restrict). o
--     historico do cancelamento é preservado.
CREATE TABLE cancelamento (
    id_cancelamento    INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id          INT NOT NULL UNIQUE REFERENCES pedido (id_pedido) ON DELETE RESTRICT,
    destino            VARCHAR(20) NOT NULL CHECK (destino IN ('estoque', 'perda')),
    data_cancelamento  DATE NOT NULL DEFAULT CURRENT_DATE
);

-- agenda: agendamento manual feito pela cliente, conforme as necessidades
-- de cada pedido.
-- regras:
--   - pedido_id obrigatorio: todo agendamento pertence a um pedido.
--   - se o pedido for apagado, os agendamentos dele vao junto (cascade).
--   - descricao e data_hora sao obrigatorias.
CREATE TABLE agenda (
    id_agenda  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pedido_id  INT NOT NULL REFERENCES pedido (id_pedido) ON DELETE CASCADE,
    descricao  VARCHAR(255) NOT NULL,
    data_hora  TIMESTAMPTZ NOT NULL
);


-- indices em chaves estrangeiras
-- eles aceleram joins e consultas por relacionamento.

CREATE INDEX idx_produto_receita              ON produto (receita_id);

CREATE INDEX idx_pedido_cliente               ON pedido (cliente_id);

CREATE INDEX idx_pedido_data_entrega          ON pedido (data_entrega);

CREATE INDEX idx_item_pedido_pedido           ON item_pedido (pedido_id);

CREATE INDEX idx_item_pedido_produto          ON item_pedido (produto_id);

CREATE INDEX idx_item_pedido_receita          ON item_pedido (receita_id);

CREATE INDEX idx_estoque_produto_produto      ON estoque_produto (produto_id);

CREATE INDEX idx_estoque_produto_producao     ON estoque_produto (producao_id);

CREATE INDEX idx_producao_receita             ON producao (receita_id);

CREATE INDEX idx_producao_pedido              ON producao (pedido_id);

CREATE INDEX idx_receita_ingrediente_ingr     ON receita_ingrediente (ingrediente_id);

CREATE INDEX idx_mov_inventario_ingrediente   ON movimentacao_inventario (ingrediente_id);

CREATE INDEX idx_mov_inventario_producao      ON movimentacao_inventario (producao_id);

CREATE INDEX idx_mov_estoque_estoque_produto  ON movimentacao_estoque (estoque_produto_id);

CREATE INDEX idx_mov_estoque_pedido           ON movimentacao_estoque (pedido_id);

CREATE INDEX idx_transacao_pedido             ON transacao (pedido_id);

CREATE INDEX idx_agenda_pedido                ON agenda (pedido_id);

CREATE INDEX idx_agenda_data_hora             ON agenda (data_hora);


COMMIT;
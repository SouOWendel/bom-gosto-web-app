BEGIN;


CREATE TABLE Cliente (

    id_cliente INT PRIMARY KEY,
    nome       VARCHAR(100) NOT NULL,
    telefone   VARCHAR(20),
    endereco   VARCHAR(200)
);

CREATE TABLE Usuario (
    id_usuario      INT PRIMARY KEY,
    login           VARCHAR(50) NOT NULL UNIQUE,
    senha           VARCHAR(255) NOT NULL,
    primeiro_acesso BOOLEAN DEFAULT TRUE
);

CREATE TABLE Produto (
    id_produto  INT PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    preco_venda DECIMAL(10,2) NOT NULL
);

CREATE TABLE Receita (
    id_receita            INT PRIMARY KEY,
    nome                  VARCHAR(100) NOT NULL,
    rendimento_quantidade DECIMAL(10,2)
);

CREATE TABLE Ingrediente (
    id_ingrediente        INT PRIMARY KEY,
    nome                  VARCHAR(100) NOT NULL,
    quantidade_disponivel DECIMAL(10,2),
    custo_unitario        DECIMAL(10,2),
    data_validade         DATE,
    quantidade_minima     DECIMAL(10,2)
);

CREATE TABLE Pedido (
    id_pedido        INT PRIMARY KEY,
    cliente_id       INT NOT NULL,
    tipo             VARCHAR(20),
    status           VARCHAR(20),
    data_entrega     DATE,
    horario_entrega  TIME,
    valor_total      DECIMAL(10,2),
    valor_sinal      DECIMAL(10,2),
    endereco_entrega VARCHAR(200),
    forma_pagamento  VARCHAR(30),
    CONSTRAINT FK_Pedido_Cliente
        FOREIGN KEY (cliente_id) REFERENCES Cliente(id_cliente)
);

CREATE TABLE Item_Pedido (
    id_item_pedido  INT PRIMARY KEY,
    produto_id      INT NOT NULL,
    pedido_id       INT NOT NULL,
    recheio         VARCHAR(100),
    decoracao       VARCHAR(200),
    quantidade_peso DECIMAL(10,2),
    CONSTRAINT FK_Item_Pedido_Produto
        FOREIGN KEY (produto_id) REFERENCES Produto(id_produto),
    CONSTRAINT FK_Item_Pedido_Pedido
        FOREIGN KEY (pedido_id) REFERENCES Pedido(id_pedido)
        ON DELETE CASCADE
);

CREATE TABLE Agenda (
    id_agenda INT PRIMARY KEY,
    pedido_id INT NOT NULL,
    descricao VARCHAR(255),
    data_hora TIMESTAMP,
    CONSTRAINT FK_Agenda_Pedido
        FOREIGN KEY (pedido_id) REFERENCES Pedido(id_pedido)
);

CREATE TABLE Cancelamento (
    id_cancelamento   INT PRIMARY KEY,
    pedido_id         INT NOT NULL,
    destino           VARCHAR(20),
    data_cancelamento DATE,
    CONSTRAINT FK_Cancelamento_Pedido
        FOREIGN KEY (pedido_id) REFERENCES Pedido(id_pedido)
);

CREATE TABLE Transacao (
    id_transacao INT PRIMARY KEY,
    pedido_id    INT NOT NULL,
    valor        DECIMAL(10,2),
    tipo         VARCHAR(20),
    data         TIMESTAMP,
    CONSTRAINT FK_Transacao_Pedido
        FOREIGN KEY (pedido_id) REFERENCES Pedido(id_pedido)
);

CREATE TABLE Estoque (
    id_estoque            INT PRIMARY KEY,
    id_produto            INT NOT NULL,
    quantidade_disponivel DECIMAL(10,2) NOT NULL,
    data_validade         DATE,
    custo                 DECIMAL(10,2),
    CONSTRAINT FK_Estoque_Produto
        FOREIGN KEY (id_produto) REFERENCES Produto(id_produto)
);

CREATE TABLE Receita_Produto (
    id_receita     INT NOT NULL,
    id_produto     INT NOT NULL,
    quantidade     DECIMAL(10,3) NOT NULL,
    unidade_medida VARCHAR(20),
    custo_unitario DECIMAL(10,2),
    PRIMARY KEY (id_receita, id_produto),
    CONSTRAINT FK_Receita_Produto_Receita
        FOREIGN KEY (id_receita) REFERENCES Receita(id_receita),
    CONSTRAINT FK_Receita_Produto_Produto
        FOREIGN KEY (id_produto) REFERENCES Produto(id_produto)
);

CREATE TABLE Ingrediente_Receita (
    receita_id            INT NOT NULL,
    ingrediente_id        INT NOT NULL,
    quantidade_necessaria DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (ingrediente_id, receita_id),
    CONSTRAINT FK_Ingrediente_Receita_Receita
        FOREIGN KEY (receita_id) REFERENCES Receita(id_receita),
    CONSTRAINT FK_Ingrediente_Receita_Ingrediente
        FOREIGN KEY (ingrediente_id) REFERENCES Ingrediente(id_ingrediente)
);


COMMIT;
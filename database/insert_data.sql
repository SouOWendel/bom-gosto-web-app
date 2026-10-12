BEGIN;


INSERT INTO Cliente (id_cliente, nome, telefone, endereco) VALUES
(1, 'Licilene Alves',  '(11) 97654-3210', 'Rua das Acácias, 120'),
(2, 'Natália',         '(11) 98123-1485', 'Av. Brasil, 845'),
(3, 'Vivi',            '(11) 97456-1003', 'Rua Santa Clara, 33'),
(4, 'Joseane',         '(11) 98765-4321', 'Rua Alberto Borges Soveral, 50'),
(5, 'Márcia Regina',   '(11) 99321-1358', 'Rua do Comércio, 77'),
(6, 'Rafaela Souza',   '(11) 96543-2201', 'Rua Paraná, 410'),
(7, 'Carlos Menezes',  '(11) 94567-8890', 'Av. Independência, 1500');

INSERT INTO Usuario (id_usuario, login, senha, primeiro_acesso) VALUES
(1, 'confeiteira', 'TROCAR_POR_HASH_BCRYPT', TRUE),
(2, 'admin',       'TROCAR_POR_HASH_BCRYPT', FALSE);

INSERT INTO Produto (id_produto, nome, preco_venda) VALUES
(1, 'Bolo 1kg massa branca',     80.90),
(2, 'Caseirinho',                40.00),
(3, 'Salgado bolinha de queijo',  0.90),
(4, 'Doce',                       1.40),
(5, 'Topper simples',             8.00),
(6, 'Refrigerante',               9.00),
(7, 'Pote',                      15.00),
(8, 'Fatia',                     41.20),
(9, 'Mini vulcão',               20.00);

INSERT INTO Receita (id_receita, nome, rendimento_quantidade) VALUES
(1, 'Massa branca',              1.00),
(2, 'Recheio de beijinho',       1.00),
(3, 'Recheio delícia de limão',  1.00),
(4, 'Brigadeiro tradicional',   50.00),
(5, 'Bolinha de queijo',        50.00),
(6, 'Caseirinho vulcão',         6.00),
(7, 'Banoffee de pote',         10.00);

INSERT INTO Ingrediente (id_ingrediente, nome, quantidade_disponivel, custo_unitario, data_validade, quantidade_minima) VALUES
(1,  'Farinha de trigo',    12.00,  5.50, '2027-03-15',  5.00),
(2,  'Açúcar',              10.00,  4.80, '2027-06-30',  4.00),
(3,  'Ovo',                 60.00,  0.90, '2026-10-25', 30.00),
(4,  'Leite condensado',    24.00,  6.90, '2027-02-10', 12.00),
(5,  'Creme de leite',      18.00,  3.50, '2027-01-20', 10.00),
(6,  'Manteiga',             3.00, 42.00, '2026-11-30',  1.50),
(7,  'Leite integral',       8.00,  5.20, '2026-10-12',  4.00),
(8,  'Chocolate em pó 50%',  2.50, 38.00, '2027-05-01',  1.00),
(9,  'Coco ralado',          1.50, 28.00, '2027-04-01',  0.50),
(10, 'Limão',               30.00,  0.60, '2026-10-14', 15.00),
(11, 'Queijo parmesão ralado', 1.20, 55.00, '2026-12-01', 0.50),
(12, 'Banana',               2.00,  6.00, '2026-10-08',  1.00),
(13, 'Doce de leite',        3.00, 22.00, '2027-01-10',  1.00),
(14, 'Fermento em pó',       0.40, 30.00, '2027-02-01',  0.20);


INSERT INTO Ingrediente_Receita (receita_id, ingrediente_id, quantidade_necessaria) VALUES
-- Massa branca (1 kg)
(1, 1, 0.30), (1, 2, 0.25), (1, 3, 4.00), (1, 6, 0.15), (1, 7, 0.25), (1, 14, 0.02),
-- Recheio de beijinho (1 kg)
(2, 4, 3.00), (2, 9, 0.10), (2, 6, 0.02),
-- Recheio delícia de limão (1 kg)
(3, 4, 2.00), (3, 5, 2.00), (3, 10, 6.00),
-- Brigadeiro (50 un)
(4, 4, 4.00), (4, 8, 0.12), (4, 6, 0.04), (4, 5, 1.00),
-- Bolinha de queijo (50 un)
(5, 1, 0.40), (5, 11, 0.20), (5, 3, 3.00), (5, 7, 0.40), (5, 6, 0.05),
-- Caseirinho vulcão (6 un)
(6, 1, 0.25), (6, 2, 0.20), (6, 3, 3.00), (6, 8, 0.10), (6, 7, 0.20), (6, 14, 0.02),
-- Banoffee de pote (10 un)
(7, 12, 0.80), (7, 13, 0.60), (7, 5, 2.00), (7, 2, 0.10);

INSERT INTO Receita_Produto (id_receita, id_produto, quantidade, unidade_medida, custo_unitario) VALUES
(1, 1,  1.000, 'kg',  14.65),
(1, 8,  8.000, 'un',   1.83),
(2, 1,  1.000, 'kg',  24.34),
(3, 1,  1.000, 'kg',  24.40),
(4, 4, 50.000, 'un',   0.75),
(5, 3, 50.000, 'un',   0.40),
(6, 2,  6.000, 'un',   1.75),
(6, 9,  6.000, 'un',   1.75),
(7, 7, 10.000, 'un',   2.55);


INSERT INTO Estoque (id_estoque, id_produto, quantidade_disponivel, data_validade, custo) VALUES
(1, 2,   6.00, '2026-10-08', 1.75),
(2, 3, 100.00, '2026-10-06', 0.40),
(3, 4,  60.00, '2026-10-09', 0.75),
(4, 5,  20.00, '2027-03-01', 2.50),
(5, 6,  12.00, '2026-12-20', 5.80),
(6, 6,  12.00, '2027-01-15', 5.50),
(7, 7,   8.00, '2026-10-07', 2.55),
(8, 8,  10.00, '2026-10-06', 1.83),
(9, 9,   5.00, '2026-10-08', 1.75);


INSERT INTO Pedido (id_pedido, cliente_id, tipo, status, data_entrega, horario_entrega,
                    valor_total, valor_sinal, endereco_entrega, forma_pagamento) VALUES
(1, 1, 'RETIRADA', 'CONCLUIDO', '2026-09-26', '17:30:00', 120.90,  60.00, NULL, 'PIX'),
(2, 2, 'RETIRADA', 'CONCLUIDO', '2026-09-22', '14:00:00',  40.00,  NULL, NULL, 'PIX'),
(3, 3, 'RETIRADA', 'CONCLUIDO', '2026-09-19', '16:00:00', 162.63,  NULL, NULL, 'PIX'),
(4, 4, 'ENTREGA',  'CONCLUIDO', '2026-09-05', '11:00:00',  51.00,  NULL, 'Rua Alberto Borges Soveral, 50', 'PIX'),
(5, 5, 'RETIRADA', 'CONCLUIDO', '2026-09-04', '10:00:00',  61.20,  NULL, NULL, 'PIX'),
(6, 6, 'RETIRADA', 'CANCELADO', '2026-09-12', '15:00:00', 115.90,  50.00, NULL, 'PIX'),
(7, 7, 'RETIRADA', 'AGENDADO',  '2026-10-10', '15:00:00',  90.00,  45.00, NULL, 'PIX');


INSERT INTO Item_Pedido (id_item_pedido, produto_id, pedido_id, recheio, decoracao, quantidade_peso) VALUES
(1,  1, 1, 'delícia de limão',   'Decoração (R$ 40,00)',               1),
(2,  2, 2, 'vulcão formigueiro', NULL,                                 1),
(3,  1, 3, 'beijinho',           'feliz aniversário mãe (bolo rosa)',  1),
(4,  3, 3, NULL,                 NULL,                                 50),
(5,  4, 3, 'brigadeiro',         NULL,                                 25),
(6,  5, 3, NULL,                 'brinde',                             1),
(7,  6, 3, NULL,                 'brinde',                             1),
(8,  7, 4, 'brigadeiro',         NULL,                                 2),
(9,  7, 4, 'bannoffe',           NULL,                                 1),
(10, 8, 5, 'Matilda',            NULL,                                 1),
(11, 9, 5, 'ninho',              NULL,                                 1),
(12, 1, 6, 'brigadeiro',         'Parabéns (R$ 35,00)',                1),
(13, 9, 7, 'ninho',              NULL,                                 3),
(14, 7, 7, 'bannoffe',           NULL,                                 2);


INSERT INTO Agenda (id_agenda, pedido_id, descricao, data_hora) VALUES
(1, 1, 'Retirada bolo 1kg - Licilene Alves',     '2026-09-26 17:30:00'),
(2, 2, 'Retirada caseirinho - Natália',          '2026-09-22 14:00:00'),
(3, 3, 'Retirada Combo 1 (7 pessoas) - Vivi',    '2026-09-19 16:00:00'),
(4, 4, 'Entrega potes - Joseane',                '2026-09-05 11:00:00'),
(5, 5, 'Retirada fatia e mini vulcão - Márcia',  '2026-09-04 10:00:00'),
(6, 7, 'Retirada mini vulcões e potes - Carlos', '2026-10-10 15:00:00');


INSERT INTO Transacao (id_transacao, pedido_id, valor, tipo, data) VALUES
(1, 1,  60.00, 'SINAL',     '2026-09-20 10:15:00'),
(2, 1,  60.90, 'RESTANTE',  '2026-09-26 17:30:00'),
(3, 2,  40.00, 'PAGAMENTO', '2026-09-22 14:05:00'),
(4, 3, 162.63, 'PAGAMENTO', '2026-09-15 09:40:00'),
(5, 4,  51.00, 'PAGAMENTO', '2026-09-05 11:10:00'),
(6, 5,  61.20, 'PAGAMENTO', '2026-09-04 10:05:00'),
(7, 6,  50.00, 'SINAL',     '2026-09-08 14:20:00'),
(8, 6,  50.00, 'ESTORNO',   '2026-09-10 09:00:00'),
(9, 7,  45.00, 'SINAL',     '2026-10-03 10:05:00');

INSERT INTO Cancelamento (id_cancelamento, pedido_id, destino, data_cancelamento) VALUES
(1, 6, 'ESTORNO', '2026-09-10');

COMMIT;
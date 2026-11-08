// define os dados usados nas respostas e requisicoes da api
export interface ApiList<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export type ApiCollection<T> = T[] | ApiList<T>;

export interface Ingredient {
    id_ingrediente: number;
    nome: string;
    quantidade_disponivel: string | null;
    quantidade_minima: string | null;
    data_validade: string | null;
    custo_unitario: string | null;
    abaixo_do_minimo: boolean | null;
    alerta_validade: ExpirationAlert | null;
}

export interface ExpirationAlert {
    nivel: 'critico' | 'atencao' | 'preventivo';
    dias_para_vencer: number;
}

export interface StockLot {
    id_estoque: number;
    id_produto: number;
    quantidade_disponivel: string;
    data_validade: string | null;
    custo: string | null;
    vencido: boolean;
    alerta_validade: ExpirationAlert | null;
}

export interface RecipeProduct {
    produto: number;
    quantidade: string;
    unidade_medida: string | null;
    custo_unitario: string | null;
}

export interface RecipeIngredient {
    id_ingrediente_receita?: number;
    ingrediente: number;
    quantidade_necessaria: string;
}

export interface Recipe {
    id_receita: number;
    nome: string;
    rendimento_quantidade: string | null;
    custo_calculado: string;
    ingredientes: RecipeIngredient[];
    produtos: Array<RecipeProduct & { id_receita_produto: number }>;
}

export interface OrderItem {
    id_item_pedido?: number;
    produto: number | null;
    receita: number | null;
    quantidade: number | null;
    preco_unitario: string;
    custo_unitario?: string | null;
    recheio?: string | null;
    quantidade_peso?: string | null;
    decoracao?: string | null;
    verificacao_estoque?: {
        verificado: boolean;
        disponivel: boolean | null;
        encaminhar_para_producao: boolean | null;
        motivo?: string;
    } | null;
}

export interface Order {
    id_pedido: number;
    cliente: number | null;
    tipo: 'interno' | 'externo';
    subtipo: 'vitrine' | 'personalizado' | null;
    status: 'pedido_feito' | 'em_producao' | 'producao_concluida' | 'concluido' | 'cancelado';
    data_entrega: string | null;
    horario_entrega: string | null;
    valor_total: string;
    valor_sinal: string;
    endereco_entrega: string | null;
    forma_pagamento: string | null;
    itens: OrderItem[];
    analise?: ProductionAnalysis;
}

export interface ProductionAnalysis {
    estoque: Array<{
        id_item_pedido: number;
        produto_id: number | null;
        receita_id: number | null;
        quantidade_solicitada: string;
        quantidade_disponivel: string;
        disponivel: boolean;
        encaminhar_para_producao: boolean;
    }>;
    receitas_sugeridas: Array<{ id_receita: number; nome: string }>;
    ausencias: Array<{ item_pedido: number; tipo: string; motivo: string }>;
    ingredientes_insuficientes: ProductionIngredient[];
    ingredientes: ProductionIngredient[];
    encaminhar_para_producao: boolean;
}

export interface ProductionIngredient {
    id_ingrediente: number;
    nome: string;
    necessario: string;
    disponivel: string;
    suficiente: boolean;
    abaixo_do_minimo: boolean | null;
    data_validade: string | null;
    alerta_validade: ExpirationAlert | null;
}

export interface ProductionConsumption {
    ingrediente_id: number;
    quantidade: string;
}

export interface CompleteProductionPayload {
    data_validade: string;
    consumos: ProductionConsumption[];
}

export interface CancelOrderPayload {
    consumos: ProductionConsumption[];
    destino: 'estoque' | 'descarte';
    produto_aproveitado?: {
        nome: string;
        quantidade: string;
        data_validade: string;
        preco_venda: string;
        custo: string;
    };
}

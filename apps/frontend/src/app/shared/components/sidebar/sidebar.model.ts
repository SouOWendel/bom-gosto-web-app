export interface NavItem {
  id: string;
  label: string;
  route: string;
  icon: string; // Nome do ícone Lucide
  exact?: boolean;
  badge?: string | number;
}

export interface UserProfile {
  name: string;
  role: string;
  avatarUrl?: string;
}

/**
 * Lista de páginas de referência utilizando os ícones oficiais da biblioteca
 * Lucide (@lucide/angular).
 */
export const DEFAULT_SIDEBAR_PAGES: NavItem[] = [
  {
    id: 'inicio',
    label: 'Início',
    route: '/inicio',
    icon: 'layout-grid',
    exact: true,
  },
  {
    id: 'pedidos',
    label: 'Pedidos',
    route: '/pedidos',
    icon: 'receipt',
  },
  {
    id: 'produtos',
    label: 'Produtos',
    route: '/produtos',
    icon: 'cake-slice',
  },
  {
    id: 'estoque',
    label: 'Estoque',
    route: '/estoque',
    icon: 'archive',
  },
  {
    id: 'inventario',
    label: 'Inventário',
    route: '/inventario',
    icon: 'chart-column',
  },
];

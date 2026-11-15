export interface PageAction {
  // Identifica a ação no (actionClick) sem depender do texto do botão.
  id?: string;
  label: string;
  route?: string;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'outline';
}

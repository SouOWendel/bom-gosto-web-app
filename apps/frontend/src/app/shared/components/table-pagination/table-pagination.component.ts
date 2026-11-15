import { Component, computed, input, output } from '@angular/core';

// Rodapé padrão das tabelas: resumo do intervalo exibido e navegação entre páginas.
@Component({
  selector: 'app-table-pagination',
  standalone: true,
  templateUrl: './table-pagination.component.html',
  styleUrls: ['./table-pagination.component.scss'],
})
export class TablePaginationComponent {
  readonly total = input.required<number>();
  readonly pageSize = input.required<number>();
  readonly currentPage = input.required<number>();
  readonly itemLabel = input('itens');
  readonly pageChange = output<number>();

  readonly totalPages = computed(() => Math.ceil(this.total() / this.pageSize()));
  readonly pages = computed(() =>
    Array.from({ length: this.totalPages() }, (_, index) => index + 1),
  );
  readonly range = computed(() => {
    const total = this.total();
    if (total === 0) {
      return { start: 0, end: 0 };
    }
    return {
      start: (this.currentPage() - 1) * this.pageSize() + 1,
      end: Math.min(this.currentPage() * this.pageSize(), total),
    };
  });

  goTo(page: number): void {
    if (page >= 1 && page <= this.totalPages() && page !== this.currentPage()) {
      this.pageChange.emit(page);
    }
  }
}

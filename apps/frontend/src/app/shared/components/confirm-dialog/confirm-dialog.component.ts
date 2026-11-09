import { Component, HostListener, input, output } from '@angular/core';
import { LucideDynamicIcon, LucideX, provideLucideIcons } from '@lucide/angular';
import { ButtonComponent } from '../button/button.component';

// Diálogo genérico para confirmar operações críticas (RNF04); o detalhe é projetado pelo chamador.
@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [ButtonComponent, LucideDynamicIcon],
  providers: [provideLucideIcons(LucideX)],
  templateUrl: './confirm-dialog.component.html',
  styleUrls: ['./confirm-dialog.component.scss'],
})
export class ConfirmDialogComponent {
  readonly title = input.required<string>();
  readonly message = input<string>('');
  readonly confirmLabel = input<string>('Confirmar');
  readonly cancelLabel = input<string>('Voltar');
  readonly variant = input<'primary' | 'danger'>('primary');
  readonly size = input<'default' | 'lg'>('default');
  readonly busy = input(false);
  readonly error = input<string | null>(null);
  readonly closed = output<void>();
  readonly confirmed = output<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  close(): void {
    if (!this.busy()) {
      this.closed.emit();
    }
  }

  confirm(): void {
    if (!this.busy()) {
      this.confirmed.emit();
    }
  }
}

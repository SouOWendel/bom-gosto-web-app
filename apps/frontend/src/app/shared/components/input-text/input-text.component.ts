import { Component, forwardRef, Input } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import {
  LucideCalendar,
  LucideDynamicIcon,
  LucideEye,
  LucideEyeOff,
  LucideHash,
  LucideLock,
  LucideMail,
  LucidePackage,
  LucideSearch,
  provideLucideIcons,
} from '@lucide/angular';

@Component({
  selector: 'app-input-text',
  standalone: true,
  imports: [LucideDynamicIcon],
  providers: [
    provideLucideIcons(
      LucideCalendar,
      LucideEye,
      LucideEyeOff,
      LucideHash,
      LucideLock,
      LucideMail,
      LucidePackage,
      LucideSearch,
    ),
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputTextComponent),
      multi: true,
    },
  ],
  templateUrl: './input-text.component.html',
  styleUrls: ['./input-text.component.scss'],
})
export class InputTextComponent implements ControlValueAccessor {
  @Input({ required: true }) label = '';
  @Input({ required: true }) inputId = '';
  @Input() type = 'text';
  @Input() autocomplete = 'off';
  @Input() placeholder = '';
  @Input() icon = 'mail';
  @Input() suffix = '';
  @Input() size: 'default' | 'compact' = 'default';

  value = '';
  disabled = false;
  showPassword = false;

  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  writeValue(value: string | null): void {
    this.value = value ?? '';
  }

  registerOnChange(onChange: (value: string) => void): void {
    this.onChange = onChange;
  }

  registerOnTouched(onTouched: () => void): void {
    this.onTouched = onTouched;
  }

  setDisabledState(disabled: boolean): void {
    this.disabled = disabled;
  }

  handleInput(value: string): void {
    this.value = value;
    this.onChange(value);
  }

  handleBlur(): void {
    this.onTouched();
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }
}

import { Component, EventEmitter, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-phone-input',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './phone-input.html',
  styleUrl: './phone-input.scss',
})
export class PhoneInput {
  // Переименовали Output, чтобы не конфликтовало с методом
  @Output() phoneSubmit = new EventEmitter<string>();

  // Обычные свойства (не signals) для работы с FormsModule
  phone = '';
  errorMessage = '';
  isValid = false;

  onInput(): void {
    const raw = this.phone.replace(/\D/g, '');
    // Для российской маски без +7 считаем 10 цифр
    this.isValid = raw.length === 10;
    this.errorMessage = '';
  }

  // Метод переименован
  handleSubmit(): void {
    if (!this.isValid) {
      this.errorMessage = 'Введите корректный номер телефона';
      return;
    }
    const raw = this.phone.replace(/\D/g, '');
    const formatted = `+7${raw}`;
    this.phoneSubmit.emit(formatted);
    this.phone = '';
    this.isValid = false;
  }
}
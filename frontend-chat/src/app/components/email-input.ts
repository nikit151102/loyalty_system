// email-input.ts
import { Component, EventEmitter, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-email-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="email-input-container">
      <input
        type="email"
        [(ngModel)]="email"
        (keyup.enter)="submitEmail()"
        placeholder="Введите email"
        class="email-input"
        autofocus
      />
      <button (click)="submitEmail()" class="send-btn">➤</button>
    </div>
  `,
  styles: [`
    .email-input-container {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin: 8px 0;
    }
    .email-input {
      flex: 1;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    .email-input:focus {
      border-color: #4A90D9;
    }
    .send-btn {
      background: #4A90D9;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 10px 16px;
      cursor: pointer;
      font-size: 18px;
      transition: background 0.2s;
    }
    .send-btn:hover {
      background: #357ABD;
    }
  `]
})
export class EmailInput {
  @Output() emailSubmit = new EventEmitter<string>();
  email = '';

  submitEmail(): void {
    if (this.email.trim()) {
      this.emailSubmit.emit(this.email.trim());
      this.email = '';
    }
  }
}
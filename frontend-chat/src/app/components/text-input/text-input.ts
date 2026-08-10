import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-text-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="text-input-container">
      <input 
        [type]="type"
        [placeholder]="placeholder"
        [(ngModel)]="value"
        (keyup.enter)="submit()"
        class="text-input"
      />
      <button (click)="submit()" class="submit-btn">
        Отправить
      </button>
    </div>
  `,
  styles: [`
    .text-input-container {
      display: flex;
      gap: 8px;
      padding: 12px 16px;
      max-width: 500px;
      margin: 8px 0;
    }
    
    .text-input {
      flex: 1;
      padding: 12px 16px;
      border: 2px solid #e0e0e0;
      border-radius: 20px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    
    .text-input:focus {
      border-color: #0084ff;
    }
    
    .submit-btn {
      padding: 12px 24px;
      background: #0084ff;
      color: white;
      border: none;
      border-radius: 20px;
      cursor: pointer;
      font-weight: 600;
      transition: background 0.2s;
    }
    
    .submit-btn:hover {
      background: #0073e6;
    }
    
    .submit-btn:disabled {
      background: #ccc;
      cursor: not-allowed;
    }
  `]
})
export class TextInput {
  @Input() placeholder = 'Введите текст';
  @Input() type = 'text';
  @Output() textSubmit = new EventEmitter<string>();
  
  value = '';
  
  submit() {
    const val = this.value.trim();
    if (val) {
      this.textSubmit.emit(val);
      this.value = '';
    }
  }
}
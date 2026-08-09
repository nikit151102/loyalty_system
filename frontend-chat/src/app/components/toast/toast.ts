import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { chatAnimations } from '../../animations/chat.animations';
import { ToastService } from '../../services/toast';

@Component({
  selector: 'app-toast',
  imports: [CommonModule],
  animations: [chatAnimations.fadeSlide],
  templateUrl: './toast.html',
  styleUrl: './toast.scss',
})
export class Toast {
  toastService = inject(ToastService);
  getIcon(type: string): string {
    return { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' }[type] || 'ℹ';
  }
}

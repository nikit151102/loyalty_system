import { CommonModule } from '@angular/common';
import { Component, Input, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-referral-section',
  imports: [CommonModule, FormsModule],
  templateUrl: './referral-section.html',
  styleUrl: './referral-section.scss',
})
export class ReferralSection {
  @Input() stats: any;
  @Input() url = '';

  copied = false;

  constructor(private cdr: ChangeDetectorRef) {}

  copyUrl(): void {

    const textToCopy = this.url || 'Ошибка: ссылка пуста';

    const tempInput = document.createElement('input');
    tempInput.value = textToCopy;
    tempInput.setAttribute('readonly', '');
    tempInput.style.position = 'absolute';
    tempInput.style.left = '-9999px';
    tempInput.style.top = '-9999px';
    document.body.appendChild(tempInput);

    tempInput.select();
    tempInput.setSelectionRange(0, 99999); 

    try {
      const successful = document.execCommand('copy');
      if (successful) {
        this.copied = true;
        this.cdr.detectChanges(); 

        setTimeout(() => {
          this.copied = false;
          this.cdr.detectChanges();
        }, 2000);
      } else {
        console.error('Команда копирования вернула false');
      }
    } catch (err) {
      console.error('Не удалось скопировать текст: ', err);
    } finally {
      document.body.removeChild(tempInput);
    }
  }
}
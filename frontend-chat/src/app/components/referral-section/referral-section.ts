import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
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

  copyUrl(input: HTMLInputElement): void {
    input.select();
    navigator.clipboard.writeText(this.url).then(() => {
      this.copied = true;
      setTimeout(() => this.copied = false, 2000);
    });
  }
}

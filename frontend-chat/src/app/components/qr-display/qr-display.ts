import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, signal } from '@angular/core';
import { Client } from '../../models/client.model';

@Component({
  selector: 'app-qr-display',
  imports: [CommonModule],
  templateUrl: './qr-display.html',
  styleUrl: './qr-display.scss',
})
export class QrDisplay implements OnInit {
  @Input() client!: Client;
  qrDataUrl = signal<string>('');

  ngOnInit(): void {
    if (this.client?.qr_code_base64) {
      this.qrDataUrl.set(`data:image/png;base64,${this.client.qr_code_base64}`);
    } else {
      // Generate simple QR placeholder using a library if available
      this.generateQR();
    }
  }

  private async generateQR(): Promise<void> {
    // For production, use 'qrcode' npm package
    // Here we just show a placeholder with client data
    this.qrDataUrl.set(`data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><rect width='200' height='200' fill='%23327120'/><text x='50%25' y='50%25' text-anchor='middle' fill='white' font-size='20'>QR ${this.client?.referral_code || ''}</text></svg>`);
  }

  downloadQR(): void {
    if (!this.qrDataUrl()) return;
    const link = document.createElement('a');
    link.download = `qr_${this.client?.referral_code || 'client'}.png`;
    link.href = this.qrDataUrl();
    link.click();
  }
}
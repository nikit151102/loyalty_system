import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Client } from '../../models/client.model';

@Component({
  selector: 'app-add-purchase',
  imports: [CommonModule, FormsModule],
  templateUrl: './add-purchase.html',
  styleUrl: './add-purchase.scss',
})
export class AddPurchase {
  @Input() client!: Client;
  @Output() submitted = new EventEmitter<any>();

  form: any = { amount: 0, order_number: '', comment: '' };

  getRate(): number {
    const total = (this.client?.total_purchases_amount || 0) + this.form.amount;
    return total <= 100000 ? 3 : 5;
  }

  getCommission(): number {
    return this.form.amount * (this.getRate() / 100);
  }

  submit(): void {
    if (this.form.amount <= 0) return;
    this.submitted.emit({
      client_id: this.client.id,
      ...this.form
    });
    this.form = { amount: 0, order_number: '', comment: '' };
  }
}

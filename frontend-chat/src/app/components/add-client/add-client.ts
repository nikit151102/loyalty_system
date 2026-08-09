import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-add-client',
  imports: [CommonModule, FormsModule],
  templateUrl: './add-client.html',
  styleUrl: './add-client.scss',
})
export class AddClient {
  @Output() submitted = new EventEmitter<any>();

  form: any = {
    full_name: '',
    phone: '',
    email: '',
    inn: '',
    client_type: 'individual'
  };

  isValid(): boolean {
    return this.form.full_name?.length >= 2 && this.form.phone?.length >= 10;
  }

  submit(): void {
    if (!this.isValid()) return;
    this.submitted.emit(this.form);
    this.form = { full_name: '', phone: '', email: '', inn: '', client_type: 'individual' };
  }
}

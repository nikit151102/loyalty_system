import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { Client } from '../../models/client.model';

@Component({
  selector: 'app-agent-clients',
  imports: [CommonModule],
  templateUrl: './agent-clients.html',
  styleUrl: './agent-clients.scss',
})
export class AgentClients {
  @Input() clients: Client[] = [];
  @Output() action = new EventEmitter<{ action: string; data: any }>();

  page = signal(1);
  pageSize = 5;

  paginatedClients = signal<Client[]>([]);
  totalPages = signal(1);

  ngOnInit(): void { this.updatePagination(); }
  ngOnChanges(): void { this.updatePagination(); }

  private updatePagination(): void {
    const start = (this.page() - 1) * this.pageSize;
    this.paginatedClients.set(this.clients.slice(start, start + this.pageSize));
    this.totalPages.set(Math.ceil(this.clients.length / this.pageSize) || 1);
  }

  nextPage(): void { this.page.update(p => Math.min(p + 1, this.totalPages())); this.updatePagination(); }
  prevPage(): void { this.page.update(p => Math.max(p - 1, 1)); this.updatePagination(); }

  getInitials(name: string): string {
    return name.split(' ').map(x => x[0]).join('').slice(0, 2).toUpperCase();
  }
}

import { Service } from '@angular/core';
import { signal } from '@angular/core';

export interface Toast {
    id: number;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
}


@Service()
export class ToastService {
    toasts = signal<Toast[]>([]);
    private counter = 0;

    show(message: string, type: Toast['type'] = 'info', duration = 3000): void {
        const id = ++this.counter;
        this.toasts.update((t:any) => [...t, { id, message, type, duration }]);
        if (duration > 0) {
            setTimeout(() => this.remove(id), duration);
        }
    }

    remove(id: number): void {
        this.toasts.update(t => t.filter(x => x.id !== id));
    }

    success(message: string): void { this.show(message, 'success'); }
    error(message: string): void { this.show(message, 'error', 5000); }
    info(message: string): void { this.show(message, 'info'); }
}

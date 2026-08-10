import { Injectable, signal, computed } from '@angular/core';
import { Agent } from '../models/agent.model';
import { Client } from '../models/client.model';

export type UserRole = 'agent' | 'client';
export type User = Agent | Client;

@Injectable({
  providedIn: 'root'
})
export class Auth {
    private readonly TOKEN_KEY = 'loyalty_token';
    private readonly USER_KEY = 'loyalty_user';
    private readonly ROLE_KEY = 'loyalty_role';
    private readonly PHONE_KEY = 'loyalty_phone';

    token = signal<string | null>(this.loadToken());
    user = signal<User | null>(this.loadUser());
    role = signal<UserRole | null>(this.loadRole());
    phone = signal<string | null>(this.loadPhone());

    // ИСПРАВЛЕНО: Используем computed сигналы вместо геттеров
    // Теперь их можно вызывать как функции: this.auth.agent()
    agent = computed<Agent | null>(() => 
        this.role() === 'agent' ? (this.user() as Agent) : null
    );
    
    client = computed<Client | null>(() => 
        this.role() === 'client' ? (this.user() as Client) : null
    );

    // Проверки ролей
    isAgent = computed(() => this.role() === 'agent');
    isClient = computed(() => this.role() === 'client');
    isLoggedIn = computed(() => this.token() !== null);

    private loadToken(): string | null {
        return localStorage.getItem(this.TOKEN_KEY);
    }
    
    private loadUser(): User | null {
        const data = localStorage.getItem(this.USER_KEY);
        return data ? JSON.parse(data) : null;
    }

    private loadRole(): UserRole | null {
        return localStorage.getItem(this.ROLE_KEY) as UserRole | null;
    }
    
    private loadPhone(): string | null {
        return localStorage.getItem(this.PHONE_KEY);
    }

    setAuth(token: string, user: User, phone: string, role: UserRole): void {
        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.USER_KEY, JSON.stringify(user));
        localStorage.setItem(this.ROLE_KEY, role);
        localStorage.setItem(this.PHONE_KEY, phone);

        this.token.set(token);
        this.user.set(user);
        this.role.set(role);
        this.phone.set(phone);
    }

    logout(): void {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        localStorage.removeItem(this.ROLE_KEY);
        localStorage.removeItem(this.PHONE_KEY);

        this.token.set(null);
        this.user.set(null);
        this.role.set(null);
        this.phone.set(null);
    }
}
import { Injectable, signal, computed } from '@angular/core';
import { Agent } from '../models/agent.model';

@Injectable({
  providedIn: 'root'
})
export class Auth {
    private readonly TOKEN_KEY = 'loyalty_token';
    private readonly AGENT_KEY = 'loyalty_agent';
    private readonly PHONE_KEY = 'loyalty_phone';

    token = signal<string | null>(this.loadToken());
    agent = signal<Agent | null>(this.loadAgent());
    phone = signal<string | null>(this.loadPhone());

    isLoggedIn = computed(() => this.token() !== null);

    private loadToken(): string | null {
        return localStorage.getItem(this.TOKEN_KEY);
    }
    
    private loadAgent(): Agent | null {
        const data = localStorage.getItem(this.AGENT_KEY);
        return data ? JSON.parse(data) : null;
    }
    
    private loadPhone(): string | null {
        return localStorage.getItem(this.PHONE_KEY);
    }

    setAuth(token: string, agent: Agent, phone: string): void {
        localStorage.setItem(this.TOKEN_KEY, token);
        localStorage.setItem(this.AGENT_KEY, JSON.stringify(agent));
        localStorage.setItem(this.PHONE_KEY, phone);
        this.token.set(token);
        this.agent.set(agent);
        this.phone.set(phone);
    }

    logout(): void {
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.AGENT_KEY);
        localStorage.removeItem(this.PHONE_KEY);
        this.token.set(null);
        this.agent.set(null);
        this.phone.set(null);
    }
}
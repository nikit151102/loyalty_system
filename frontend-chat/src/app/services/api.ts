import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Service } from '@angular/core';
import { Observable, catchError, of } from 'rxjs';
import { Application, Agent, AgentStats } from '../models/agent.model';
import { Client, Purchase } from '../models/client.model';
import { ConfigService } from '../models/config.service';
import { Auth } from './auth';

@Service()
export class Api {
    private http = inject(HttpClient);
    private config = inject(ConfigService);
    private auth = inject(Auth);

    private headers(): HttpHeaders {
        let headers = new HttpHeaders({
            'Content-Type': 'application/json',
            'X-API-Key': this.config.API_KEY
        });
        if (this.auth.token()) {
            headers = headers.set('Authorization', `Bearer ${this.auth.token()}`);
        }
        return headers;
    }

    // ==================== AUTH ====================
    login(payload: { phone: string }): Observable<any> {
        return this.http.post<any>(`${this.config.API_URL}/auth/login`, payload);
    }

    // ==================== APPLICATIONS ====================
    registerAgent(data: { max_user_id: number; phone: string; email: string; city: string; registration_type: string; referral_code?: string }): Observable<Application> {
        const url = data.referral_code
            ? `${this.config.API_URL}/applications/register/${data.referral_code}`
            : `${this.config.API_URL}/applications/register`;
        return this.http.post<Application>(url, data, { headers: this.headers() });
    }

    getApplicationByUser(maxUserId: number): Observable<Application | null> {
        return this.http.get<Application>(`${this.config.API_URL}/applications/user/${maxUserId}`, {
            headers: this.headers()
        }).pipe(catchError(() => of(null)));
    }

    getApplicationByPhone(phone: string): Observable<any> {
        return this.http.get<any>(`${this.config.API_URL}/applications/by-phone/${phone}`);
    }

    // ==================== AGENTS ====================
    getMyProfile(): Observable<any> {
        return this.http.get<any>(`${this.config.API_URL}/agents/me`); // Или /clients/me, если бэкенд роутит по токену
    }

    getMyStatus(): Observable<any> {
        return this.http.get<any>(`${this.config.API_URL}/agents/me/status`, { headers: this.headers() });
    }

    getAgentByPhone(phone: string): Observable<Agent | null> {
        // Note: this endpoint needs to be added to backend
        return this.http.get<Agent>(`${this.config.API_URL}/agents/by-phone/${encodeURIComponent(phone)}`, {
            headers: this.headers()
        }).pipe(catchError(() => of(null)));
    }

    // ==================== STATS ====================
    getMyStats(): Observable<AgentStats> {
        return this.http.get<AgentStats>(`${this.config.API_URL}/statistics/me`, { headers: this.headers() });
    }

    // ==================== CLIENTS ====================
    getClients(skip = 0, limit = 20): Observable<Client[]> {
        return this.http.get<Client[]>(`${this.config.API_URL}/clients`, {
            params: { skip: skip.toString(), limit: limit.toString() },
            headers: this.headers()
        });
    }

    getClientByPhone(phone: string): Observable<Client | null> {
        return this.http.get<Client>(`${this.config.API_URL}/clients/by-phone/${encodeURIComponent(phone)}`, {
            headers: this.headers()
        }).pipe(catchError(() => of(null)));
    }

    createClient(data: any): Observable<Client> {
        return this.http.post<Client>(`${this.config.API_URL}/clients`, data, { headers: this.headers() });
    }

    // ==================== PURCHASES ====================
    createPurchase(data: { client_id: number; amount: number; order_number?: string; comment?: string }): Observable<Purchase> {
        return this.http.post<Purchase>(`${this.config.API_URL}/purchases`, data);
    }

    getClientPurchases(clientId: number): Observable<Purchase[]> {
        return this.http.get<Purchase[]>(`${this.config.API_URL}/purchases/client/${clientId}`);
    }

    // ==================== REFERRALS ====================
    getReferralStats(): Observable<any> {
        return this.http.get<any>(`${this.config.API_URL}/referrals/me`);
    }

    // ==================== QR ====================
    getQRCodeUrl(clientId: number): string {
        return `${this.config.API_URL}/clients/${clientId}/qr?access_token=${this.auth.token()}`;
    }
}

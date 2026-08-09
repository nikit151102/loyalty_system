import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ConfigService {
  readonly API_URL = 'http://localhost:6410';
  readonly API_KEY = 'your-secret-api-key';
  readonly BOT_NAME = 'Макс-Бот';
  readonly BOT_AVATAR = '🤖';
  readonly USER_AVATAR = '👤';
  readonly TYPING_DELAY = 800; // ms before bot message appears
}
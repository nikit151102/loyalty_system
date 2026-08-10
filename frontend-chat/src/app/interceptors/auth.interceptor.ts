import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Auth } from '../services/auth';
import { ConfigService } from '../models/config.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(Auth);
  const config = inject(ConfigService);

  let headers: Record<string, string> = {
    'X-API-Key': config.API_KEY
  };

  if (localStorage.getItem('loyalty_token')) {
    headers['Authorization'] = `Bearer ${localStorage.getItem('loyalty_token')}`;
  }

  const cloned = req.clone({ setHeaders: headers });
  return next(cloned);
};
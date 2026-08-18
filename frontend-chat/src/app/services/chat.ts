import { inject, Service, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Agent, Application } from '../models/agent.model';
import { Client } from '../models/client.model';
import { ConfigService } from '../models/config.service';
import { Message, AppState } from '../models/message.model';
import { Api } from './api';
import { Auth } from './auth';
import { Toast, ToastService } from './toast';

@Service()
export class Chat {
  private api = inject(Api);
  private auth = inject(Auth);
  private toast = inject(ToastService);
  private config = inject(ConfigService);

  messages = signal<Message[]>([]);
  state = signal<AppState>('welcome');
  isTyping = signal(false);
  currentUser: Agent | Client | null = null;
  currentApplication: Application | null = null;

  registrationStep = signal(1);
  registrationData: any = {
    phone: '',
    email: '',
    city: '',
    full_name: '',
    registration_type: '',
    referral_code: null,
    inn: ''
  };

  // Храним текущий введенный номер телефона для использования до авторизации
  private _currentPhone: string | null = null;

  constructor() {
    this._initReferralCode();
    this._checkExistingSession();
  }

  private _initReferralCode(): void {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const ref = urlParams.get('ref') || urlParams.get('start');
      if (ref) {
        this.registrationData.referral_code = ref;
        console.log('🎁 Реферальный код из URL:', ref);
      }
    }
  }

  private async _checkExistingSession(): Promise<void> {
    if (this.auth.isLoggedIn()) {
      const role = this.auth.role();
      const phone = this.auth.phone();

      if (role && phone) {
        this.state.set('checking_phone');
        try {
          const loginRes = await firstValueFrom(this.api.login({ phone, role }));
          if (loginRes?.access_token) {
            await this._handleSuccessfulLogin(loginRes, phone);
            return;
          }
        } catch (e) {
          console.warn('Сессия недействительна, выполняем выход');
          this.auth.logout();
        }
      }
    }
    this.initFlow();
  }

  private async initFlow(): Promise<void> {
    if (this.registrationData.referral_code) {
      await this.addBotMessage(`Привет! 👋 Я ${this.config.BOT_NAME} — помощник программы лояльности.`);
      await this.delay(400);
      await this.addBotMessage(`🎁 Вы перешли по реферальной ссылке!\nЧтобы стать клиентом программы, введите ваш номер телефона:`);
    } else {
      await this.addBotMessage(`Привет! 👋 Я ${this.config.BOT_NAME} — помощник программы лояльности.`);
      await this.delay(600);
      await this.addBotMessage('Введите ваш номер телефона, чтобы продолжить:');
    }
    this.state.set('asking_phone');
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  private async addBotMessage(text: string, extra: Partial<Message> = {}): Promise<void> {
    this.isTyping.set(true);
    await this.delay(this.config.TYPING_DELAY);
    this.isTyping.set(false);
    const msg: Message = {
      id: this.genId(),
      sender: 'bot',
      text,
      type: 'text',
      timestamp: new Date(),
      ...extra
    };
    this.messages.update(m => [...m, msg]);
    await this.delay(150);
  }

  private addUserMessage(text: string): void {
    this.messages.update(m => [...m, {
      id: this.genId(),
      sender: 'user',
      text,
      type: 'text',
      timestamp: new Date()
    }]);
  }

  private genId(): string {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  // ==================== PUBLIC ACTIONS ====================
  private readonly TOKEN_KEY = 'loyalty_token';

  async submitPhone(phone: string): Promise<void> {
    // ИСПРАВЛЕНО: Сохраняем номер телефона сразу при вводе
    this._currentPhone = phone;
    this.addUserMessage(phone);
    this.state.set('checking_phone');

    await this.addBotMessage('🔍 Проверяю данные в базе...');
    const hasReferral = !!this.registrationData.referral_code;

    try {
      const loginRes = await firstValueFrom(this.api.login({ phone }));

      if (loginRes?.status === 'choose_role') {
        await this.addBotMessage(`📋 Номер **${phone}** зарегистрирован и как агент, и как клиент.\n\nВыберите, в какой роли вы хотите войти:`);
        await this.addBotMessage('', {
          type: 'buttons',
          buttons: [
            { id: 'login_as_agent', label: `Войти как Агент`, action: 'login_as_agent', variant: 'primary' },
            { id: 'login_as_client', label: `Войти как Клиент`, action: 'login_as_client', variant: 'outline' }
          ]
        });
        return;
      }

      if (loginRes?.access_token) {
        localStorage.setItem(this.TOKEN_KEY, loginRes.access_token);

        if (hasReferral && loginRes.role === 'agent') {
          await this.addBotMessage(`⚠️ Этот номер уже зарегистрирован как **Агент**.\n\nНо вы перешли по реферальной ссылке! Хотите также зарегистрироваться как **Клиент** этого агента?`);
          await this.addBotMessage('', {
            type: 'buttons',
            buttons: [
              { id: 'reg_as_client_anyway', label: '✅ Да, стать клиентом', action: 'reg_as_client_anyway', variant: 'primary' },
              { id: 'enter_as_agent', label: '👔 Нет, войти как Агент', action: 'enter_as_agent', variant: 'outline' }
            ]
          });
          return;
        }

        await this._handleSuccessfulLogin(loginRes, phone);
        return;
      }
    } catch (loginError: any) {
      if (loginError.status === 404) {
        console.log('User not found in DB, checking applications...');
      } else {
        console.error('Login error:', loginError);
        await this.addBotMessage('⚠️ Произошла ошибка при подключении к серверу. Попробуйте еще раз.');
        this.state.set('asking_phone');
        return;
      }
    }

    if (!hasReferral) {
      try {
        const app = await firstValueFrom(this.api.getApplicationByPhone(phone));
        if (app) {
          this.currentApplication = app;
          if (app.status === 'pending') {
            await this.addBotMessage(`📋 У вас уже есть заявка на рассмотрении. Статус: **⏳ На рассмотрении**`);
            await this.showPendingStatus();
            return;
          } else if (app.status === 'rejected') {
            await this.addBotMessage(`❌ Ваша заявка была отклонена. Причина: ${app.rejection_reason || 'не указана'}`);
            await this.addBotMessage('Хотите подать новую заявку?');
            this.state.set('agent_rejected');
            await this.addBotMessage('', {
              type: 'buttons',
              buttons: [
                { id: 'reregister', label: '🔄 Подать заявку снова', action: 'reregister', variant: 'primary' },
                { id: 'back', label: '← Назад', action: 'back', variant: 'outline' }
              ]
            });
            return;
          } else if (app.status === 'approved') {
            await this.addBotMessage(`✅ Ваша заявка одобрена! Добро пожаловать в систему! 🎉`);
            let agentData: Agent | null = null;
            let token: string | null = null;
            try {
              const retryLogin = await firstValueFrom(this.api.login({ phone }));
              if (retryLogin?.access_token) {
                token = retryLogin.access_token;
                agentData = await firstValueFrom(this.api.getMyProfile());
              }
            } catch (retryError) {
              console.warn('Агент еще не создан в БД бэкендом, используем данные заявки для UI');
            }
            if (!agentData) {
              agentData = {
                id: app.agent_id || 0, max_user_id: app.max_user_id || this.phoneToId(phone),
                phone: app.phone, email: app.email, registration_type: app.registration_type,
                status: 'active' as any, referral_code: 'GENERATING', balance: 0, total_clients: 0,
                total_purchases_amount: 0, total_commission_earned: 0, total_referrals_count: 0,
                created_at: new Date().toISOString(), updated_at: new Date().toISOString(), approved_at: new Date().toISOString()
              } as Agent;
            }
            if (token) this.auth.setAuth(token, agentData, phone, 'agent');
            else { this.auth.user.set(agentData); this.auth.role.set('agent'); this.auth.phone.set(phone); }
            this.currentUser = agentData;
            await this.delay(400);
            await this.addBotMessage(`Рады видеть вас, ${agentData.email?.split('@')[0] || 'Агент'}! 👋`);
            await this.showAgentMenu();
            return;
          }
        }
      } catch (appError: any) {
        console.log('Application not found, starting registration...');
      }
    }

    if (hasReferral) {
      await this.addBotMessage(`🎁 Вы перешли по реферальной ссылке! Давайте оформим вас как клиента программы.`);
      await this.startClientRegistration();
    } else {
      await this.addBotMessage(`Вы впервые в нашей программе. Хотите стать агентом?`);
      this.state.set('welcome');
      await this.addBotMessage('', {
        type: 'buttons',
        buttons: [
          { id: 'start_register', label: '🚀 Стать агентом', action: 'start_register', variant: 'primary' },
          { id: 'learn_more', label: '❓ Узнать больше', action: 'learn_more', variant: 'outline' }
        ]
      });
    }
  }

  async handleButtonAction(action: string, data?: any): Promise<void> {
    switch (action) {
      // ИСПРАВЛЕНО: Используем this._currentPhone вместо this.auth.phone()
      case 'login_as_agent':
        if (this._currentPhone) await this._loginWithRole(this._currentPhone, 'agent');
        break;
      case 'login_as_client':
        if (this._currentPhone) await this._loginWithRole(this._currentPhone, 'client');
        break;
      case 'reg_as_client_anyway':
        await this.addBotMessage('Отлично! Начинаем регистрацию клиента...');
        await this.startClientRegistration();
        break;
      case 'enter_as_agent':
        if (this._currentPhone) await this._loginWithRole(this._currentPhone, 'agent');
        break;

      // === ПЕРЕКЛЮЧЕНИЕ МЕЖДУ РОЛЯМИ ===
      case 'switch_to_client':
        await this._switchToClient();
        break;
      case 'switch_to_agent':
        await this._switchToAgent();
        break;
      // ==========================================

      case 'start_register':
        await this.startAgentRegistration();
        break;
      case 'reregister':
        this.auth.logout();
        this._currentPhone = null;
        await this.startAgentRegistration();
        break;
      case 'back':
        this.goToWelcome();
        break;
      case 'show_stats':
        await this.showAgentStats();
        break;
      case 'show_clients':
        await this.showAgentClients();
        break;
      case 'add_client':
        await this.startAddClient();
        break;
      case 'add_purchase':
        await this.startAddPurchase(data);
        break;
      case 'show_referral':
        await this.showReferral();
        break;
      case 'check_status':
        await this.checkApplicationStatus();
        break;
      case 'show_qr':
        await this.showQR(data);
        break;
      case 'logout':
        this.auth.logout();
        this._currentPhone = null;
        this.goToWelcome();
        break;
      case 'select_type':
        this.registrationData.registration_type = data;
        this.registrationStep.set(6);
        await this.confirmRegistration();
        break;
      case 'confirm_register':
        await this.submitRegistration();
        break;
      case 'edit_register':
        const savedRef = this.registrationData.referral_code;
        this.registrationData = {
          phone: this._currentPhone || '',
          email: '',
          city: '',
          full_name: '',
          registration_type: '',
          referral_code: savedRef,
          inn: ''
        };
        this.registrationStep.set(2);
        this.state.set('checking_phone');
        await this.addBotMessage(`Давайте заполним анкету заново.\n\n👤 **Шаг 1: Укажите ваше ФИО:**`);
        this.state.set('agent_registration');
        break;
      case 'cancel_register':
        this.goToWelcome();
        break;
    }
  }

  // ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

  private async _loginWithRole(phone: string, role: 'agent' | 'client'): Promise<void> {
    this.state.set('checking_phone');
    await this.addBotMessage(`🔄 Выполняю вход в роли: ${role === 'agent' ? 'Агент' : 'Клиент'}...`);
    try {
      const loginRes = await firstValueFrom(this.api.login({ phone, role }));
      if (loginRes?.access_token) await this._handleSuccessfulLogin(loginRes, phone);
      else throw new Error('Не удалось получить токен');
    } catch (error: any) {
      await this.addBotMessage(`⚠️ Не удалось войти в выбранной роли.`);
      this.state.set('asking_phone');
    }
  }

  private async _switchToClient(): Promise<void> {
    const phone = this.auth.phone() || this._currentPhone;
    if (!phone) { this.goToWelcome(); return; }

    this.state.set('checking_phone');
    await this.addBotMessage('🔄 Переключаю в режим Клиента...');
    try {
      const loginRes = await firstValueFrom(this.api.login({ phone, role: 'client' }));
      await this._handleSuccessfulLogin(loginRes, phone);
    } catch (e) {
      await this.addBotMessage('❌ Не удалось переключиться.');
      await this.showAgentMenu();
    }
  }

  private async _switchToAgent(): Promise<void> {
    const phone = this.auth.phone() || this._currentPhone;
    if (!phone) { this.goToWelcome(); return; }

    this.state.set('checking_phone');
    await this.addBotMessage('🔄 Переключаю в режим Агента...');
    try {
      const loginRes = await firstValueFrom(this.api.login({ phone, role: 'agent' }));
      await this._handleSuccessfulLogin(loginRes, phone);
    } catch (e) {
      await this.addBotMessage('❌ Не удалось переключиться.');
      await this.showClientMenu(this.currentUser as Client);
    }
  }

  private async _handleSuccessfulLogin(loginRes: any, phone: string): Promise<void> {
    localStorage.setItem('loyalty_token', loginRes.access_token)
    if (loginRes.role === 'agent') {
      const agent = await firstValueFrom(this.api.getMyProfile());
      this.auth.setAuth(loginRes.access_token, agent, phone, 'agent');
      this.currentUser = agent;
      await this.delay(400);
      await this.addBotMessage(`Рады видеть вас снова, ${agent.email?.split('@')[0] || 'Агент'}! 👋`);
      await this.showAgentMenu();
    }
    else if (loginRes.role === 'client') {
      const client = await firstValueFrom(this.api.getMyClientProfile());
      this.auth.setAuth(loginRes.access_token, client, phone, 'client');
      this.currentUser = client;
      await this.delay(400);
      await this.addBotMessage(`Добро пожаловать, ${client.full_name || 'Клиент'}! 🎉`);
      await this.showClientMenu(client);
    }
  }

  // ==================== AGENT REGISTRATION FLOW ====================

  private async startAgentRegistration(): Promise<void> {
    const savedRef = this.registrationData.referral_code;

    this.registrationData = {
      phone: this._currentPhone || '',
      email: '',
      city: '',
      full_name: '',
      registration_type: '',
      referral_code: savedRef,
      inn: ''
    };

    this.registrationStep.set(2);
    this.state.set('checking_phone');

    await this.addBotMessage(`Отлично! Номер **${this._currentPhone}** сохранен.\n\n👤 **Шаг 1: Укажите ваше ФИО:**`);
    this.state.set('agent_registration');
  }


  async submitRegStep(step: number, value: string): Promise<void> {
    this.addUserMessage(value);
    this.state.set('checking_phone');

    // ИЗМЕНЕНО: Логика сдвинута на 1 шаг, так как мы начинаем с шага 2
    if (step === 2) {
      this.registrationData.full_name = value;
      await this.addBotMessage('✅ ФИО принято!\n\n📧 **Шаг 2: Укажите ваш email:**');
      this.registrationStep.set(3);
      this.state.set('agent_registration');
    } else if (step === 3) {
      this.registrationData.email = value;
      await this.addBotMessage('✅ Email принят!\n\n🏙️ **Шаг 3: Укажите ваш город:**');
      this.registrationStep.set(4);
      this.state.set('agent_registration');
    } else if (step === 4) {
      this.registrationData.city = value;
      await this.addBotMessage('✅ Город принят!\n\n🏢 **Шаг 4: Выберите ваш статус:**');
      this.registrationStep.set(5);
      this.state.set('agent_registration');
      await this.addBotMessage('', {
        type: 'buttons',
        buttons: [
          { id: 't1', label: 'Самозанятый', action: 'select_type', variant: 'outline', data: 'self_employed' },
          { id: 't2', label: 'ИП', action: 'select_type', variant: 'outline', data: 'ip' },
          { id: 't3', label: 'Юридическое лицо', action: 'select_type', variant: 'outline', data: 'legal_entity' }
        ]
      });
    }
  }

  private async confirmRegistration(): Promise<void> {
    const typeLabels: any = { 'self_employed': 'Самозанятый', 'ip': 'Индивидуальный предприниматель', 'legal_entity': 'Юридическое лицо' };
    await this.addBotMessage(`📋 **Шаг 5: Проверьте данные**\n\n👤 ФИО: ${this.registrationData.full_name}\n📱 Телефон: ${this.registrationData.phone}\n📧 Email: ${this.registrationData.email}\n🏙️ Город: ${this.registrationData.city}\n🏢 Статус: ${typeLabels[this.registrationData.registration_type]}\n\nВсё верно?`);
    await this.addBotMessage('', {
      type: 'buttons',
      buttons: [
        { id: 'c1', label: 'Отправить заявку', action: 'confirm_register', variant: 'primary' },
        { id: 'c2', label: 'Изменить', action: 'edit_register', variant: 'outline' },
        { id: 'c3', label: 'Отменить', action: 'cancel_register', variant: 'danger' }
      ]
    });
  }


  private async submitRegistration(): Promise<void> {
    await this.addBotMessage('Отправляю заявку...');
    try {
      const maxUserId = this.phoneToId(this.registrationData.phone);
      const app = await firstValueFrom(this.api.registerAgent({
        max_user_id: maxUserId,
        full_name: this.registrationData.full_name,
        phone: this.registrationData.phone,
        email: this.registrationData.email,
        city: this.registrationData.city,
        registration_type: this.registrationData.registration_type,
        referral_code: this.registrationData.referral_code
      }));
      this.currentApplication = app;
      await this.addBotMessage(`✅ **Заявка успешно отправлена!**\n\nНомер заявки: #${app.id}\nМы рассмотрим её в ближайшее время.`);
      this.state.set('agent_pending');
      await this.showPendingStatus();
    } catch (e: any) {
      this.toast.error(e.error?.detail || 'Ошибка при подаче заявки');
      await this.addBotMessage(`❌ Произошла ошибка: ${e.error?.detail || 'попробуйте ещё раз'}`);
    }
  }
  // ==================== CLIENT REGISTRATION FLOW ====================



  private async startClientRegistration(): Promise<void> {
    this.registrationStep.set(1);
    // Сохраняем известный номер телефона, чтобы он был готов к отправке на шаге 4
    this.registrationData.phone = this._currentPhone || '';
    this.state.set('checking_phone');
    await this.addBotMessage('📝 Давайте зарегистрируем вас как клиента.\n\n🔢 Введите **ИНН** (10 или 12 цифр):');
    this.state.set('client_registration');
  }

  async submitClientStep(step: number, value: string): Promise<void> {
    this.addUserMessage(value);
    this.state.set('checking_phone');

    if (step === 1) {
      this.registrationData.inn = value;
      await this.addBotMessage('✅ ИНН принят!\n\n📧 Введите ваш email:'); // Email логичнее спросить перед ФИО
      this.registrationStep.set(2);
      this.state.set('client_registration');
    } else if (step === 2) {
      this.registrationData.email = value;
      await this.addBotMessage('👤 Введите ваше ФИО:');
      this.registrationStep.set(3);
      this.state.set('client_registration');
    } else if (step === 3) {
      this.registrationData.full_name = value;
      await this.addBotMessage(`✅ Данные получены! Создаю ваш профиль клиента...`);

      try {
        const client = await firstValueFrom(this.api.registerClient({
          full_name: this.registrationData.full_name,
          inn: this.registrationData.inn,
          phone: this.registrationData.phone, // Здесь уже будет предзаполненный номер!
          email: this.registrationData.email,
          referral_code: this.registrationData.referral_code,
          client_type: 'individual'
        }));

        this.toast.success('Клиент успешно зарегистрирован!');
        this.currentUser = client.client || client;

        if (client.access_token) {
          this.auth.setAuth(client.access_token, client.client || client, this.registrationData.phone, 'client');
        }

        await this.showClientMenu(client.client || client);
      } catch (e: any) {
        this.toast.error(e.error?.detail || 'Ошибка при регистрации клиента');
        await this.addBotMessage(`❌ Произошла ошибка: ${e.error?.detail || 'попробуйте ещё раз'}`);
        this.state.set('client_registration');
      }
    }
  }


  // ==================== MENUS ====================

  private async showAgentMenu(): Promise<void> {
    this.state.set('agent_menu');

    let isAlsoClient = false;
    const phone = this.auth.phone() || this._currentPhone;
    if (phone) {
      try {
        const res = await firstValueFrom(this.api.login({ phone, role: 'client' }));
        if (res?.access_token) {
          isAlsoClient = true;
        }
      } catch (e) {
        isAlsoClient = false;
      }
    }

    const buttons: any[] = [];

    if (isAlsoClient) {
      buttons.push({
        id: 'switch_to_client',
        label: 'Переключить в режим Клиента',
        action: 'switch_to_client',
        variant: 'secondary',
        icon: '🔄'
      });
    }

    buttons.push(
      { id: 'm1', label: 'Статистика', action: 'show_stats', variant: 'primary', icon: '📊' },
      { id: 'm4', label: 'Реферальная ссылка', action: 'show_referral', variant: 'primary', icon: '🔗' },
      { id: 'm6', label: 'Выйти', action: 'logout', variant: 'danger', icon: '🚪' }
    );

    await this.addBotMessage('', {
      type: 'menu',
      text: '🏠 **Главное меню АГЕНТА**\n\nВыберите действие:',
      menuData: { buttons }
    });
  }
  private async showClientMenu(client: Client): Promise<void> {
    this.state.set('client_menu');

    let isAlsoAgent = false;
    const phone = this.auth.phone() || this._currentPhone;
    if (phone) {
      try {
        const res = await firstValueFrom(this.api.login({ phone, role: 'agent' }));
        if (res?.access_token) {
          isAlsoAgent = true;
        }
      } catch (e) {
        isAlsoAgent = false;
      }
    }

    const buttons: any[] = [];

    if (isAlsoAgent) {
      buttons.push({
        id: 'switch_to_agent',
        label: 'Переключить в режим Агента',
        action: 'switch_to_agent',
        variant: 'secondary',
        icon: '🔄'
      });
    }

    buttons.push(
      { id: 'c1', label: 'Мой QR-код', action: 'show_qr', variant: 'primary', icon: '🎫', data: client },
      { id: 'c2', label: 'История покупок', action: 'show_history', variant: 'primary', icon: '📜', data: client },
      // { id: 'c3', label: 'Мой профиль', action: 'show_profile', variant: 'outline', icon: '👤', data: client },
      { id: 'c4', label: 'Выйти', action: 'logout', variant: 'danger', icon: '🚪' }
    );

    await this.addBotMessage('', {
      type: 'menu',
      text: `**Меню КЛИЕНТА**\n\n${client.full_name}\n${client.phone}`,
      menuData: { buttons }
    });
  }

  private async showPendingStatus(): Promise<void> {
    this.state.set('agent_pending');
    await this.addBotMessage('', {
      type: 'buttons',
      buttons: [
        { id: 's1', label: 'Обновить статус', action: 'check_status', variant: 'primary' },
        { id: 's2', label: '← Назад', action: 'back', variant: 'outline' }
      ]
    });
  }

  private async showAgentStats(): Promise<void> {
    this.state.set('agent_stats');
    await this.addBotMessage('📊 Загружаю вашу статистику...');
    try {
      const stats = await firstValueFrom(this.api.getMyStats());

      // Вспомогательная функция для красивого форматирования денег (например: 125 000.50)
      const formatMoney = (amount: number) =>
        amount.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

      const statsMessage = `📈 **Ваша реферальная статистика**

👥 **Всего приглашено клиентов:** ${stats.total_referred_clients}
✅ **Из них активных (совершили покупки):** ${stats.active_referred_clients}

🛒 **Всего покупок рефералами:** ${stats.total_referred_purchases_count}
💰 **Общая сумма покупок:** ${formatMoney(stats.total_referred_purchases_amount)} ₽
💸 **Ваш заработанный бонус:** ${formatMoney(stats.total_referred_commission_earned)} ₽`;

      await this.addBotMessage(statsMessage);
      await this.addBackButton();
    } catch (e) {
      console.error('Ошибка загрузки статистики:', e);
      this.toast.error('Не удалось загрузить статистику');
      await this.addBackButton();
    }
  }

  private async showAgentClients(): Promise<void> {
    this.state.set('agent_clients');
    await this.addBotMessage('Загружаю список ваших клиентов...');
    try {
      const clients = await firstValueFrom(this.api.getClients());
      if (clients.length === 0) {
        await this.addBotMessage('У вас пока нет клиентов. Добавьте первого!');
      } else {
        await this.addBotMessage('', { type: 'card', cardData: { type: 'clients_list', data: clients } });
      }
      await this.addBotMessage('', {
        type: 'buttons',
        buttons: [
          { id: 'a1', label: 'Добавить клиента', action: 'add_client', variant: 'primary' },
          { id: 'a2', label: '← Назад в меню', action: 'back', variant: 'outline' }
        ]
      });
    } catch (e) {
      this.toast.error('Ошибка загрузки клиентов');
      await this.addBackButton();
    }
  }

  private async showReferral(): Promise<void> {
    this.state.set('referral');
    await this.addBotMessage('Формирую вашу реферальную ссылку...');
    try {
      const stats = await firstValueFrom(this.api.getReferralStats());
      const agent = this.auth.agent();
      if (!agent || !agent.referral_code) {
        this.toast.error('Не удалось получить реферальный код');
        await this.addBackButton();
        return;
      }
      const url = `${window.location.origin}?ref=${agent.referral_code}`;
      await this.addBotMessage('', { type: 'card', cardData: { type: 'referral', data: stats, url } });
      await this.addBackButton();
    } catch (e) {
      this.toast.error('Ошибка');
      await this.addBackButton();
    }
  }

  private async showQR(client: Client): Promise<void> {
    this.state.set('qr_display');
    await this.addBotMessage('', { type: 'card', cardData: { type: 'qr', data: client } });
    await this.addBackButton();
  }

  private async checkApplicationStatus(): Promise<void> {
    await this.addBotMessage('Проверяю статус...');
    if (this.auth.agent()) {
      try {
        const status = await firstValueFrom(this.api.getMyStatus());
        await this.addBotMessage(`Текущий статус: **${status.status}**\n${status.is_approved ? 'Заявка одобрена!' : ''}`);
      } catch (e) {
        this.toast.error('Не удалось проверить статус');
      }
    } else if (this.currentApplication) {
      await this.addBotMessage(`Статус заявки #${this.currentApplication.id}: **${this.currentApplication.status}**`);
    }
    await this.addBackButton();
  }

  private async startAddClient(): Promise<void> {
    this.state.set('add_client');
    await this.addBotMessage('', { type: 'card', cardData: { type: 'add_client_form' } });
  }

  private async startAddPurchase(client: Client): Promise<void> {
    this.state.set('add_purchase');
    await this.addBotMessage('', { type: 'card', cardData: { type: 'add_purchase_form', data: client } });
  }

  private async addBackButton(): Promise<void> {
    await this.addBotMessage('', {
      type: 'buttons',
      buttons: [{ id: 'back', label: '← Назад в меню', action: 'back_to_menu', variant: 'outline' }]
    });
  }

  async handleBackToMenu(): Promise<void> {
    if (this.auth.agent()) {
      await this.showAgentMenu();
    } else {
      await this.showClientMenu(this.currentUser as Client);
    }
  }

  private goToWelcome(): void {
    this.messages.set([]);
    this.currentUser = null;
    this.currentApplication = null;
    this._currentPhone = null; // Очищаем при сбросе
    this.initFlow();
  }

  private phoneToId(phone: string): number {
    let hash = 0;
    for (let i = 0; i < phone.length; i++) {
      hash = ((hash << 5) - hash) + phone.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }
}
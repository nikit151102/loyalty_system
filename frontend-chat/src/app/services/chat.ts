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

  // Registration flow state
  registrationStep = signal(1);
  registrationData: any = {
    phone: '',
    email: '',
    registration_type: '',
    referral_code: null
  };

  constructor() {
    this.initFlow();
  }

  private async initFlow(): Promise<void> {
    await this.addBotMessage(`Привет! 👋 Я ${this.config.BOT_NAME} — помощник программы лояльности.`);
    await this.delay(600);
    await this.addBotMessage('Введите ваш номер телефона, чтобы продолжить:');
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


  async submitPhone(phone: string): Promise<void> {
    this.addUserMessage(phone);
    this.state.set('checking_phone');

    await this.addBotMessage('🔍 Проверяю данные в базе...');

    try {
        // 1. Сначала проверяем, существует ли клиент
        const client = await firstValueFrom(this.api.getClientByPhone(phone));
        
        if (client) {
            // Клиент найден
            this.currentUser = client;
            await this.delay(500);
            await this.addBotMessage(`Добро пожаловать! Вы уже являетесь клиентом программы. 🎉`);
            this.showClientMenu(client);
            return;
        }

        // 2. Если клиент не найден, пробуем найти агента
        const maxUserId = this.phoneToId(phone);
        
        try {
            const loginRes = await firstValueFrom(this.api.login(maxUserId));
            
            if (loginRes?.access_token) {
                // Агент найден и авторизован
                const agent = await firstValueFrom(this.api.getMyProfile());
                this.auth.setAuth(loginRes.access_token, agent, phone);
                this.currentUser = agent;

                if (agent.status === 'active') {
                    await this.delay(400);
                    await this.addBotMessage(`Рады видеть вас снова, ${agent.email?.split('@')[0] || 'Агент'}! 👋`);
                    this.showAgentMenu();
                } else if (agent.status === 'blocked') {
                    await this.addBotMessage(`⚠️ Ваш аккаунт заблокирован. Обратитесь в поддержку.`);
                    this.state.set('agent_rejected');
                }
                return;
            }
        } catch (loginError: any) {
            // Агент не найден или ошибка авторизации - продолжаем
            console.log('Agent not found, checking application...');
        }

        // 3. Проверяем статус заявки
        try {
            const app = await firstValueFrom(this.api.getApplicationByPhone(phone));
            
            if (app) {
                this.currentApplication = app;
                
                if (app.status === 'pending') {
                    await this.addBotMessage(`📋 У вас уже есть заявка на рассмотрении. Статус: **⏳ На рассмотрении**`);
                    this.showPendingStatus();
                    return;
                } else if (app.status === 'rejected') {
                    await this.addBotMessage(`❌ Ваша заявка была отклонена. Причина: ${app.rejection_reason || 'не указана'}`);
                    await this.addBotMessage('Хотите подать новую заявку?');
                    this.state.set('agent_rejected');
                    this.addBotMessage('', {
                        type: 'buttons',
                        buttons: [
                            { id: 'reregister', label: '🔄 Подать заявку снова', action: 'reregister', variant: 'primary' },
                            { id: 'back', label: '← Назад', action: 'back', variant: 'outline' }
                        ]
                    });
                    return;
                } else if (app.status === 'approved') {
                    // Заявка одобрена, но пользователь еще не агент
                    await this.addBotMessage(`✅ Ваша заявка одобрена! Вы можете войти в систему.`);
                    // Можно предложить войти или зарегистрироваться как агент
                    this.showAgentMenu();
                    return;
                }
            }
        } catch (appError: any) {
            // Заявка не найдена - продолжаем
            console.log('Application not found, starting registration...');
        }

        // 4. Ничего не найдено - начинаем регистрацию
        const urlParams = new URLSearchParams(window.location.search);
        const referralCode = urlParams.get('ref');

        if (referralCode) {
            this.registrationData.referral_code = referralCode;
            await this.addBotMessage(`🎁 Вы перешли по реферальной ссылке! Давайте оформим вас как клиента программы.`);
            this.startClientRegistration();
        } else {
            await this.addBotMessage(`Вы впервые в нашей программе. Хотите стать агентом?`);
            this.state.set('agent_registration');
            this.addBotMessage('', {
                type: 'buttons',
                buttons: [
                    { id: 'start_register', label: '🚀 Стать агентом', action: 'start_register', variant: 'primary' },
                    { id: 'learn_more', label: '❓ Узнать больше', action: 'learn_more', variant: 'outline' }
                ]
            });
        }
        
    } catch (error: any) {
        console.error('Error in submitPhone:', error);
        await this.addBotMessage('⚠️ Произошла ошибка при проверке данных. Попробуйте еще раз.');
        this.state.set('asking_phone');
    }
}

  async handleButtonAction(action: string, data?: any): Promise<void> {
    switch (action) {
      case 'start_register':
        this.startAgentRegistration();
        break;
      case 'reregister':
        this.auth.logout();
        this.startAgentRegistration();
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
        this.startAddClient();
        break;
      case 'add_purchase':
        this.startAddPurchase(data);
        break;
      case 'show_referral':
        await this.showReferral();
        break;
      case 'check_status':
        await this.checkApplicationStatus();
        break;
      case 'show_qr':
        this.showQR(data);
        break;
      case 'logout':
        this.auth.logout();
        this.goToWelcome();
        break;
      case 'select_type':
        this.registrationData.registration_type = data;
        this.registrationStep.set(4);
        await this.confirmRegistration();
        break;
      case 'confirm_register':
        await this.submitRegistration();
        break;
      case 'edit_register':
        this.registrationStep.set(1);
        this.startAgentRegistration();
        break;
      case 'cancel_register':
        this.goToWelcome();
        break;
    }
  }

  // ==================== AGENT REGISTRATION FLOW ====================

  private async startAgentRegistration(): Promise<void> {
    this.registrationStep.set(1);
    this.registrationData = { phone: '', email: '', registration_type: '', referral_code: null };
    this.state.set('agent_registration');
    await this.addBotMessage('Отлично! Давайте заполним анкету. Шаг 1 из 4.\n\n📱 **Ваш номер телефона:**');
  }

  async submitRegStep(step: number, value: string): Promise<void> {
    this.addUserMessage(value);

    if (step === 1) {
      this.registrationData.phone = value;
      this.registrationStep.set(2);
      await this.addBotMessage('✅ Отлично!\n\n📧 **Шаг 2: Укажите ваш email:**');
    } else if (step === 2) {
      this.registrationData.email = value;
      this.registrationStep.set(3);
      await this.addBotMessage('✅ Email принят!\n\n🏢 **Шаг 3: Выберите ваш статус:**');
      this.addBotMessage('', {
        type: 'buttons',
        buttons: [
          { id: 't1', label: '👨‍💼 Самозанятый', action: 'select_type', variant: 'outline', data: 'self_employed' },
          { id: 't2', label: '💼 ИП', action: 'select_type', variant: 'outline', data: 'ip' },
          { id: 't3', label: '🏛 Юридическое лицо', action: 'select_type', variant: 'outline', data: 'legal_entity' }
        ]
      });
    }
  }

  private async confirmRegistration(): Promise<void> {
    const typeLabels: any = {
      'self_employed': '👨‍💼 Самозанятый',
      'ip': '💼 Индивидуальный предприниматель',
      'legal_entity': '🏛 Юридическое лицо'
    };
    await this.addBotMessage(`📋 **Шаг 4: Проверьте данные**\n\n📱 Телефон: ${this.registrationData.phone}\n📧 Email: ${this.registrationData.email}\n🏢 Статус: ${typeLabels[this.registrationData.registration_type]}\n\nВсё верно?`);
    this.addBotMessage('', {
      type: 'buttons',
      buttons: [
        { id: 'c1', label: '✅ Отправить заявку', action: 'confirm_register', variant: 'success' },
        { id: 'c2', label: '✏️ Изменить', action: 'edit_register', variant: 'outline' },
        { id: 'c3', label: '❌ Отменить', action: 'cancel_register', variant: 'danger' }
      ]
    });
  }

  private async submitRegistration(): Promise<void> {
    await this.addBotMessage('⏳ Отправляю заявку...');
    try {
      const maxUserId = this.phoneToId(this.registrationData.phone);
      const app = await firstValueFrom(this.api.registerAgent({
        max_user_id: maxUserId,
        phone: this.registrationData.phone,
        email: this.registrationData.email,
        registration_type: this.registrationData.registration_type,
        referral_code: this.registrationData.referral_code
      }));
      this.currentApplication = app;
      await this.addBotMessage(`✅ **Заявка успешно отправлена!** 🎉\n\nНомер заявки: #${app.id}\nМы рассмотрим её в ближайшее время.\n\nВы можете проверять статус в любой момент.`);
      this.state.set('agent_pending');
      this.showPendingStatus();
    } catch (e: any) {
      this.toast.error(e.error?.detail || 'Ошибка при подаче заявки');
      await this.addBotMessage(`❌ Произошла ошибка: ${e.error?.detail || 'попробуйте ещё раз'}`);
    }
  }

  // ==================== CLIENT REGISTRATION FLOW ====================

  private async startClientRegistration(): Promise<void> {
    this.state.set('client_registration');
    await this.addBotMessage('📝 Давайте зарегистрируем вас как клиента.\n\n🔢 Введите **ИНН** (10 или 12 цифр):');
  }

  async submitClientStep(step: number, value: string): Promise<void> {
    this.addUserMessage(value);
    if (step === 1) {
      this.registrationData.inn = value;
      await this.addBotMessage('✅ ИНН принят!\n\n📱 Введите ваш номер телефона:');
    } else if (step === 2) {
      this.registrationData.phone = value;
      await this.addBotMessage('📧 Введите ваш email:');
    } else if (step === 3) {
      this.registrationData.email = value;
      await this.addBotMessage(`✅ Данные получены! Создаю ваш профиль клиента...`);
      // Here would be client creation via referral
      this.toast.success('Клиент зарегистрирован! (демо)');
    }
  }

  // ==================== MENUS ====================

  private showAgentMenu(): void {
    this.state.set('agent_menu');
    this.addBotMessage('', {
      type: 'menu',
      text: '🏠 **Главное меню агента**\n\nВыберите действие:',
      menuData: {
        buttons: [
          { id: 'm1', label: '📊 Статистика', action: 'show_stats', variant: 'primary', icon: '📊' },
          { id: 'm2', label: '👥 Мои клиенты', action: 'show_clients', variant: 'primary', icon: '👥' },
          { id: 'm3', label: '➕ Добавить клиента', action: 'add_client', variant: 'primary', icon: '➕' },
          { id: 'm4', label: '🔗 Реферальная ссылка', action: 'show_referral', variant: 'primary', icon: '🔗' },
          { id: 'm5', label: '📋 Статус заявки', action: 'check_status', variant: 'outline', icon: '📋' },
          { id: 'm6', label: '🚪 Выйти', action: 'logout', variant: 'danger', icon: '🚪' }
        ]
      }
    });
  }

  private showClientMenu(client: Client): void {
    this.state.set('client_menu');
    this.addBotMessage('', {
      type: 'menu',
      text: `🏠 **Меню клиента**\n\n👤 ${client.full_name}\n📱 ${client.phone}`,
      menuData: {
        buttons: [
          { id: 'c1', label: '🎫 Мой QR-код', action: 'show_qr', variant: 'primary', icon: '🎫', data: client },
          { id: 'c2', label: '📜 История покупок', action: 'show_history', variant: 'primary', icon: '📜', data: client },
          { id: 'c3', label: '👤 Мой профиль', action: 'show_profile', variant: 'outline', icon: '👤', data: client },
          { id: 'c4', label: '🚪 Выйти', action: 'logout', variant: 'danger', icon: '🚪' }
        ]
      }
    });
  }

  private showPendingStatus(): void {
    this.state.set('agent_pending');
    this.addBotMessage('', {
      type: 'buttons',
      buttons: [
        { id: 's1', label: '🔄 Обновить статус', action: 'check_status', variant: 'primary' },
        { id: 's2', label: '← Назад', action: 'back', variant: 'outline' }
      ]
    });
  }

  private async showAgentStats(): Promise<void> {
    this.state.set('agent_stats');
    await this.addBotMessage('📊 Загружаю вашу статистику...');
    try {
      const stats = await firstValueFrom(this.api.getMyStats());
      this.addBotMessage('', {
        type: 'card',
        cardData: { type: 'stats', data: stats }
      });
      this.addBackButton();
    } catch (e) {
      this.toast.error('Не удалось загрузить статистику');
      this.addBackButton();
    }
  }

  private async showAgentClients(): Promise<void> {
    this.state.set('agent_clients');
    await this.addBotMessage('👥 Загружаю список ваших клиентов...');
    try {
      const clients = await firstValueFrom(this.api.getClients());
      if (clients.length === 0) {
        await this.addBotMessage('У вас пока нет клиентов. Добавьте первого!');
      } else {
        this.addBotMessage('', {
          type: 'card',
          cardData: { type: 'clients_list', data: clients }
        });
      }
      this.addBotMessage('', {
        type: 'buttons',
        buttons: [
          { id: 'a1', label: '➕ Добавить клиента', action: 'add_client', variant: 'primary' },
          { id: 'a2', label: '← Назад в меню', action: 'back', variant: 'outline' }
        ]
      });
    } catch (e) {
      this.toast.error('Ошибка загрузки клиентов');
      this.addBackButton();
    }
  }

  private async showReferral(): Promise<void> {
    this.state.set('referral');
    await this.addBotMessage('🔗 Формирую вашу реферальную ссылку...');
    try {
      const stats = await firstValueFrom(this.api.getReferralStats());
      const agent = this.auth.agent();
      const url = `${window.location.origin}?ref=${agent?.referral_code}`;
      this.addBotMessage('', {
        type: 'card',
        cardData: { type: 'referral', data: stats, url }
      });
      this.addBackButton();
    } catch (e) {
      this.toast.error('Ошибка');
      this.addBackButton();
    }
  }

  private showQR(client: Client): void {
    this.state.set('qr_display');
    this.addBotMessage('', {
      type: 'card',
      cardData: { type: 'qr', data: client }
    });
    this.addBackButton();
  }

  private async checkApplicationStatus(): Promise<void> {
    await this.addBotMessage('🔍 Проверяю статус...');
    if (this.auth.agent()) {
      try {
        const status = await firstValueFrom(this.api.getMyStatus());
        await this.addBotMessage(`📋 Текущий статус: **${status.status}**\n${status.is_approved ? '✅ Заявка одобрена!' : ''}`);
      } catch (e) {
        this.toast.error('Не удалось проверить статус');
      }
    } else if (this.currentApplication) {
      await this.addBotMessage(`📋 Статус заявки #${this.currentApplication.id}: **${this.currentApplication.status}**`);
    }
    this.addBackButton();
  }

  private startAddClient(): void {
    this.state.set('add_client');
    this.addBotMessage('', {
      type: 'card',
      cardData: { type: 'add_client_form' }
    });
  }

  private startAddPurchase(client: Client): void {
    this.state.set('add_purchase');
    this.addBotMessage('', {
      type: 'card',
      cardData: { type: 'add_purchase_form', data: client }
    });
  }

  private addBackButton(): void {
    this.addBotMessage('', {
      type: 'buttons',
      buttons: [
        { id: 'back', label: '← Назад в меню', action: 'back_to_menu', variant: 'outline' }
      ]
    });
  }

  async handleBackToMenu(): Promise<void> {
    if (this.auth.agent()) {
      this.showAgentMenu();
    } else {
      this.goToWelcome();
    }
  }

  private goToWelcome(): void {
    this.messages.set([]);
    this.currentUser = null;
    this.currentApplication = null;
    this.initFlow();
  }

  private phoneToId(phone: string): number {
    // Simple deterministic hash for demo purposes
    let hash = 0;
    for (let i = 0; i < phone.length; i++) {
      hash = ((hash << 5) - hash) + phone.charCodeAt(i);
      hash |= 0;
    }
    return Math.abs(hash);
  }
}

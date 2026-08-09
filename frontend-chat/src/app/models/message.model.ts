export type MessageSender = 'bot' | 'user';

export interface Message {
  id: string;
  sender: MessageSender;
  text?: string;
  html?: string;
  type: 'text' | 'buttons' | 'input' | 'card' | 'menu' | 'status';
  timestamp: Date;
  buttons?: ChatButton[];
  cardData?: any;
  menuData?: any;
  statusData?: any;
  isLoading?: boolean;
}

export interface ChatButton {
  id: string;
  label: string;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'outline' | 'success';
  action: string;
  data?: any;
  disabled?: boolean;
}

export type AppState =
  | 'welcome'
  | 'asking_phone'
  | 'checking_phone'
  | 'agent_menu'
  | 'agent_pending'
  | 'agent_rejected'
  | 'client_menu'
  | 'agent_registration'
  | 'client_registration'
  | 'agent_stats'
  | 'agent_clients'
  | 'add_client'
  | 'add_purchase'
  | 'referral'
  | 'qr_display'
  | 'status_check';
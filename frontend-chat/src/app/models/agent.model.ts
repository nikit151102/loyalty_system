export interface Agent {
  id: number;
  max_user_id: number;
  phone: string;
  email: string;
  registration_type: string;
  status: string;
  referral_code: string;
  balance: number;
  total_clients: number;
  total_purchases_amount: number;
  total_commission_earned: number;
  total_referrals_count: number;
  created_at: string;
  approved_at?: string;
}

export interface AgentStats {
  total_referred_clients: number;
  active_referred_clients: number;
  total_referred_purchases_count: number;
  total_referred_purchases_amount: number;
  total_referred_commission_earned: number;
}

export interface Application {
  id: number;
  max_user_id: number;
  phone: string;
  email: string;
  registration_type: string;
  status: 'pending' | 'approved' | 'rejected';
  rejection_reason?: string;
  created_at: string;
}


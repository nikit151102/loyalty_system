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
  agent_id: number;
  total_commission_earned: number;
  balance: number;
  total_clients: number;
  total_purchases_amount: number;
  total_referrals: number;
  level1_referrals: number;
  level2_referrals: number;
  average_commission_rate: number;
  commission_by_rate: Record<string, number>;
  top_clients: any[];
  monthly_earnings: { month: string; amount: number }[];
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
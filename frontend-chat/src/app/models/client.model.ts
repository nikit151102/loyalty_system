export interface Client {
  id: number;
  agent_id: number;
  full_name: string;
  phone: string;
  email?: string;
  inn?: string;
  client_type: string;
  qr_code_base64?: string;
  referral_code?: string;
  total_purchases_amount: number;
  purchases_count: number;
  created_at: string;
  max_user_id?: number;
}

export interface Purchase {
  id: number;
  client_id: number;
  agent_id: number;
  amount: number;
  order_number?: string;
  comment?: string;
  commission_amount: number;
  commission_rate: number;
  created_at: string;
}
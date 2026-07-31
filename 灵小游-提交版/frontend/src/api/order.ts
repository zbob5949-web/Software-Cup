import request from './request';

export interface OrderItem {
  id: number;
  order_no: string;
  ticket_id: number;
  ticket_name?: string;
  ticket_type?: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  visitor_name: string;
  visitor_phone: string;
  order_status: string;
  remark?: string;
  created_at?: string;
  updated_at?: string;
}

export async function getMyOrders(): Promise<OrderItem[]> {
  const response = await request.get('/api/orders');
  const body = response.data as { data?: { orders?: OrderItem[] } };
  return body.data?.orders ?? [];
}

export async function getMyOrderDetail(orderNo: string): Promise<OrderItem> {
  const response = await request.get(`/api/orders/${encodeURIComponent(orderNo)}`);
  const body = response.data as { data?: { order?: OrderItem } };
  if (!body.data?.order) throw new Error('订单不存在');
  return body.data.order;
}

export async function refundOrder(orderNo: string): Promise<void> {
  await request.post(`/api/orders/${encodeURIComponent(orderNo)}/refund`);
}

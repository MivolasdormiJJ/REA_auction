import { Alert, Button, Card, Empty, List, Segmented, Spin, Tag, Typography } from 'antd';
import { BellOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import client from '../api/client';

type Notice = {
  id: string; auction_id: number; auction_title: string;
  type: 'auction_won' | 'auction_lost' | 'auction_owner_closed';
  title: string; message: string;
  your_bid_kopecks: number | null; payment_kopecks: number | null;
  created_at: string | null;
};
const money = (n: number) => (n / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });

export function NotificationsPage() {
  const [items, setItems] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [filter, setFilter] = useState<'all' | 'auction_won' | 'auction_lost'>('all');

  const refresh = async () => {
    setFailed(false);
    try {
      const { data } = await client.get<{ count: number; results: Notice[] }>('/notifications/');
      setItems(data.results);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void refresh(); const timer = window.setInterval(() => { void refresh(); }, 30000); return () => window.clearInterval(timer); }, []);

  const visible = filter === 'all' ? items : items.filter(item => item.type === filter);
  return <div>
    <header className="rea-page-heading">
      <div>
        <div className="rea-page-kicker">РЕЗУЛЬТАТЫ ТОРГОВ</div>
        <h1>Уведомления</h1>
        <p>Узнайте, где вы победили, кто выиграл в остальных аукционах и чем завершились ваши заказы.</p>
      </div>
      <Button icon={<BellOutlined />} onClick={() => { setLoading(true); void refresh(); }}>Обновить</Button>
    </header>
    <div className="rea-info-strip">
      Результаты появляются после официального закрытия аукциона сервером. Пока торги идут, победитель ещё не определён.
    </div>
    {failed && <Alert showIcon type="error" message="Не удалось получить уведомления" style={{ marginBottom: 16 }} />}
    <Card>
      <Segmented
        style={{ marginBottom: 24 }}
        value={filter}
        onChange={value => setFilter(value as typeof filter)}
        options={[{ label: 'Все результаты', value: 'all' }, { label: 'Победы', value: 'auction_won' }, { label: 'Не победил', value: 'auction_lost' }]}
      />
      {loading ? <Spin style={{ display: 'block', margin: '35px auto' }} /> : visible.length === 0
        ? <Empty description="Новых результатов пока нет. Они появятся здесь после завершения торгов." />
        : <List
            itemLayout="horizontal"
            dataSource={visible}
            renderItem={item => (
              <List.Item actions={[<Link key="auction" to={`/auctions/${item.auction_id}`}>Открыть аукцион</Link>]}>
                <List.Item.Meta
                  avatar={item.type === 'auction_won'
                    ? <CheckCircleOutlined style={{ color: '#dd761b', fontSize: 26 }} />
                    : item.type === 'auction_lost'
                    ? <CloseCircleOutlined style={{ color: '#537eaf', fontSize: 26 }} />
                    : <ClockCircleOutlined style={{ color: '#287b8c', fontSize: 26 }} />}
                  title={<span>{item.title} <Tag color={item.type === 'auction_won' ? 'orange' : 'blue'}>{item.type === 'auction_won' ? 'Победа' : item.type === 'auction_lost' ? 'Участие' : 'Заказчик'}</Tag></span>}
                  description={<div>
                    <Typography.Text strong>{item.auction_title}</Typography.Text>
                    <p style={{ margin: '6px 0' }}>{item.message}</p>
                    {item.your_bid_kopecks !== null && <div>Ваша ставка: {money(item.your_bid_kopecks)}</div>}
                    {item.payment_kopecks !== null && <div>Итоговая цена: {money(item.payment_kopecks)}</div>}
                    {item.created_at && <Typography.Text type="secondary" style={{ fontSize: 12 }}>{new Date(item.created_at).toLocaleString('ru-RU')}</Typography.Text>}
                  </div>}
                />
              </List.Item>
            )}
          />}
    </Card>
  </div>;
}

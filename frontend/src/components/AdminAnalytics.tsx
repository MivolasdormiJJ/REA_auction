import { Alert, Button, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Table, Typography } from 'antd';
import { DownloadOutlined, ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import client from '../api/client';

type Analytics = {
  summary: {
    users_total: number;
    users_active: number;
    auctions_total: number;
    auctions_open: number;
    auctions_review: number;
    auctions_closed: number;
    bids_total: number;
    unique_bidders: number;
    auctions_with_bids: number;
    completed_tasks: number;
    payment_total_kopecks: number;
    budgets_closed_total_kopecks: number;
  };
  by_status: { status: string; count: number }[];
  by_category: { category_id: number; category: string; count: number; bids_count: number }[];
  by_month: { month: string; closed_count: number; payment_kopecks: number }[];
  generated_at: string;
};

const rubles = (kopecks: number) =>
  (kopecks / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
const statusLabels: Record<string, string> = {
  draft: 'Черновики', review: 'На модерации', rejected: 'Отклонены',
  open: 'Открыты', closed: 'Завершены', paused: 'Приостановлены',
};

export function AdminAnalytics() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function refresh() {
    setLoading(true);
    setError('');
    try {
      const { data } = await client.get<Analytics>('/admin/analytics/');
      setAnalytics(data);
    } catch {
      setError('Не удалось загрузить аналитику. Требуются права суперпользователя.');
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { void refresh(); }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 36 }}><Spin size="large" /></div>;
  if (!analytics) return <Alert type="error" showIcon message={error || 'Данные недоступны'} action={<Button size="small" onClick={() => void refresh()}>Повторить</Button>} />;

  const { summary: s } = analytics;
  const maxMonthly = Math.max(1, ...analytics.by_month.map(x => x.closed_count));
  const maxStatus = Math.max(1, ...analytics.by_status.map(x => x.count));

  return <div>
    <Space wrap style={{ marginBottom: 20 }}>
      <Button icon={<ReloadOutlined />} onClick={() => void refresh()}>Обновить</Button>
      <Button icon={<DownloadOutlined />} href="/api/admin/reports/?kind=auctions">Аукционы · CSV</Button>
      <Button icon={<DownloadOutlined />} href="/api/admin/reports/?kind=users">Пользователи · CSV</Button>
      <Button icon={<DownloadOutlined />} href="/api/admin/reports/?kind=bids">Ставки · CSV</Button>
    </Space>
    <Row gutter={[14, 14]} style={{ marginBottom: 22 }}>
      <Col xs={12} lg={6}><Card><Statistic title="Пользователей" value={s.users_total} /><Typography.Text type="secondary">Активных: {s.users_active}</Typography.Text></Card></Col>
      <Col xs={12} lg={6}><Card><Statistic title="Аукционов" value={s.auctions_total} /><Typography.Text type="secondary">Открытых: {s.auctions_open}</Typography.Text></Card></Col>
      <Col xs={12} lg={6}><Card><Statistic title="Всего ставок" value={s.bids_total} /><Typography.Text type="secondary">Уникальных участников: {s.unique_bidders}</Typography.Text></Card></Col>
      <Col xs={12} lg={6}><Card><Statistic title="Выполнено заданий" value={s.completed_tasks} /><Typography.Text type="secondary">Подтверждено заказчиками</Typography.Text></Card></Col>
    </Row>
    <Row gutter={[16, 16]} style={{ marginBottom: 22 }}>
      <Col xs={24} md={12}><Card title="Состояния аукционов">
        {analytics.by_status.map(item => <div key={item.status} style={{ marginBottom: 11 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>{statusLabels[item.status] || item.status}</span><strong>{item.count}</strong>
          </div>
          <Progress percent={Math.round(item.count / maxStatus * 100)} showInfo={false} strokeColor={item.status === 'closed' ? '#267ba6' : '#e97521'} />
        </div>)}
      </Card></Col>
      <Col xs={24} md={12}><Card title="Результаты торгов">
        <Row gutter={[12, 20]}>
          <Col span={12}><Statistic title="Завершено аукционов" value={s.auctions_closed} /></Col>
          <Col span={12}><Statistic title="На модерации" value={s.auctions_review} /></Col>
          <Col span={12}><Statistic title="Аукционов со ставками" value={s.auctions_with_bids} /></Col>
          <Col span={12}><Statistic title="Сумма итоговых цен" value={rubles(s.payment_total_kopecks)} valueStyle={{ fontSize: 19 }} /></Col>
        </Row>
        <Typography.Paragraph type="secondary" style={{ marginTop: 18, marginBottom: 0 }}>
          Итоговые цены — расчётные суммы по правилу второй цены, а не реальные денежные поступления.
        </Typography.Paragraph>
      </Card></Col>
    </Row>
    <Card title="Завершение аукционов по месяцам" style={{ marginBottom: 22 }}>
      {analytics.by_month.length === 0 ? <Empty description="Завершённых аукционов пока нет" />
        : <Row gutter={[12, 18]}>
          {analytics.by_month.map(month => <Col xs={12} sm={8} lg={4} key={month.month}>
            <div style={{ display: 'flex', gap: 8, flexDirection: 'column', alignItems: 'center' }}>
              <Typography.Text strong>{month.closed_count}</Typography.Text>
              <div style={{ height: 120, width: '100%', display: 'flex', alignItems: 'end', justifyContent: 'center', borderBottom: '1px solid #d9e7f0' }}>
                <div title={rubles(month.payment_kopecks)} style={{ height: Math.max(5, month.closed_count / maxMonthly * 100) + '%', width: '48%', background: 'linear-gradient(0deg,#e97521,#f5ae66)', borderRadius: '5px 5px 0 0' }} />
              </div>
              <Typography.Text>{month.month}</Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>{rubles(month.payment_kopecks)}</Typography.Text>
            </div>
          </Col>)}
        </Row>}
    </Card>
    <Card title="Популярные направления подготовки">
      <Table rowKey="category_id" pagination={false} size="small" scroll={{ x: 450 }}
        dataSource={analytics.by_category}
        columns={[
          { title: 'Направление', dataIndex: 'category' },
          { title: 'Аукционов', dataIndex: 'count', align: 'right' },
          { title: 'Ставок', dataIndex: 'bids_count', align: 'right' },
        ]} />
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        Данные актуальны на {new Date(analytics.generated_at).toLocaleString('ru-RU')}. Отчёты доступны только администратору.
      </Typography.Text>
    </Card>
  </div>;
}

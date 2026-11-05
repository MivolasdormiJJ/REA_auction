import { Alert, Card, Input, Space, Spin, Table, Tabs, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import type { Auction, PaginatedResponse } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';

type AdminUser = {
  id: number; username: string; email: string; email_verified: boolean;
  is_active: boolean; is_staff: boolean; is_superuser: boolean; date_joined: string;
};

const currency = (n: number) => (n / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });

export function AdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [userPage, setUserPage] = useState(1);
  const [auctionPage, setAuctionPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [auctionTotal, setAuctionTotal] = useState(0);
  const [error, setError] = useState('');
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingAuctions, setLoadingAuctions] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let alive = true;
    setLoadingUsers(true);
    client.get<PaginatedResponse<AdminUser>>('/admin/users/', { params: { page: userPage } })
      .then(({ data }) => { if (alive) { setUsers(data.results); setUserTotal(data.count); } })
      .catch(() => { if (alive) setError('Не удалось загрузить пользователей. Проверьте административные права.'); })
      .finally(() => { if (alive) setLoadingUsers(false); });
    return () => { alive = false; };
  }, [userPage]);

  useEffect(() => {
    let alive = true;
    setLoadingAuctions(true);
    client.get<PaginatedResponse<Auction>>('/admin/auctions/', { params: { page: auctionPage } })
      .then(({ data }) => { if (alive) { setAuctions(data.results); setAuctionTotal(data.count); } })
      .catch(() => { if (alive) setError('Не удалось загрузить список аукционов.'); })
      .finally(() => { if (alive) setLoadingAuctions(false); });
    return () => { alive = false; };
  }, [auctionPage]);

  const filteredUsers = users.filter(u => [u.username, u.email].some(v => v.toLowerCase().includes(search.toLowerCase())));
  const filteredAuctions = auctions.filter(a => [a.title, a.description].some(v => v.toLowerCase().includes(search.toLowerCase())));

  return <div>
    <header className="rea-page-heading">
      <div><div className="rea-page-kicker">УПРАВЛЕНИЕ ПЛАТФОРМОЙ</div><h1>Панель администратора</h1><p>Все пользователи и аукционы, включая черновики и заявки на проверке.</p></div>
    </header>
    <div className="rea-info-strip">Доступ только для суперпользователя Django. Пароли и их хэши никогда не передаются в браузер. Для решений по модерации используйте страницу модератора.</div>
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 20 }} />}
    <Card>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Input.Search allowClear placeholder="Поиск на текущей странице" onChange={e => setSearch(e.target.value)} style={{ maxWidth: 360 }} />
        <Tabs items={[
          { key: 'users', label: `Пользователи (${userTotal})`, children: loadingUsers ? <Spin /> : <Table
            rowKey="id" size="middle" scroll={{ x: 700 }} dataSource={filteredUsers}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: 'Логин', dataIndex: 'username' },
              { title: 'Email', dataIndex: 'email' },
              { title: 'Роль', render: (_, u: AdminUser) => u.is_superuser ? <Tag color="purple">Админ</Tag> : u.is_staff ? <Tag color="geekblue">Сотрудник</Tag> : <Tag>Участник</Tag> },
              { title: 'Активен', dataIndex: 'is_active', render: (value: boolean) => value ? <Tag color="green">Да</Tag> : <Tag color="red">Нет</Tag> },
              { title: 'Создан', dataIndex: 'date_joined', render: (value: string) => new Date(value).toLocaleDateString('ru-RU') },
            ]}
            pagination={{ current: userPage, pageSize: 20, total: userTotal, onChange: setUserPage, showSizeChanger: false }}
          /> },
          { key: 'auctions', label: `Аукционы (${auctionTotal})`, children: loadingAuctions ? <Spin /> : <Table
            rowKey="id" size="middle" scroll={{ x: 680 }} dataSource={filteredAuctions}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: 'Задача', dataIndex: 'title', render: (value: string, a: Auction) => <Link to={`/auctions/${a.id}`}>{value}</Link> },
              { title: 'Заказчик', dataIndex: 'owner_id', render: (id: number) => `#${id}` },
              { title: 'Бюджет', dataIndex: 'budget_kopecks', render: currency },
              { title: 'Статус', dataIndex: 'status', render: (value: Auction['status']) => <StatusBadge status={value} /> },
            ]}
            pagination={{ current: auctionPage, pageSize: 20, total: auctionTotal, onChange: setAuctionPage, showSizeChanger: false }}
          /> },
        ]} />
      </Space>
    </Card>
    <Typography.Paragraph type="secondary" style={{ marginTop: 18, fontSize: 12 }}>Поиск фильтрует только записи загруженной страницы. Просмотр остальных записей доступен через пагинацию.</Typography.Paragraph>
  </div>;
}

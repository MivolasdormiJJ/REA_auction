import { Alert, Button, Empty, Input, Pagination, Select, Space, Spin, Tag } from 'antd';
import { ArrowRightOutlined, ClockCircleOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuctions, getCategories } from '../api/auctions';
import type { Auction, AuctionFilters, AuctionStatus, Category } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import '../app-theme.css';

const money = (value: number) => (value / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
const STATUSES: { value: AuctionStatus; label: string }[] = [
  { value: 'open', label: 'Активные' },
  { value: 'closed', label: 'Завершённые' },
  { value: 'review', label: 'На модерации' },
  { value: 'draft', label: 'Черновики' },
  { value: 'rejected', label: 'Отклонённые' },
  { value: 'paused', label: 'Приостановленные' },
];

function AuctionTile({ auction, category }: { auction: Auction; category?: string }) {
  return (
    <article className="rea-auction-tile">
      <div className="rea-auction-tile-top">
        <span className="rea-category-icon">{(category ?? 'З').slice(0, 1).toUpperCase()}</span>
        <StatusBadge status={auction.status} />
      </div>
      <div><Tag color="geekblue" style={{ borderRadius: 7 }}>{category ?? 'Задача'}</Tag></div>
      <h3><Link to={`/auctions/${auction.id}`} style={{ color: 'inherit' }}>{auction.title}</Link></h3>
      <p>{auction.description.length > 150 ? auction.description.slice(0, 150) + '…' : auction.description}</p>
      <div style={{ color: '#8796b1', fontSize: 12 }}><ClockCircleOutlined /> Торги до {new Date(auction.ends_at).toLocaleString('ru-RU')}</div>
      <div className="rea-auction-tile-foot">
        <div><span className="rea-tile-sub">Максимальный бюджет</span><div className="rea-tile-budget">{money(auction.budget_kopecks)}</div></div>
        <Link to={`/auctions/${auction.id}`}><Button type="primary">Подробнее <ArrowRightOutlined /></Button></Link>
      </div>
    </article>
  );
}

export function CatalogPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [count, setCount] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filters, setFilters] = useState<AuctionFilters>({ status: 'open', page: 1 });
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [categoryError, setCategoryError] = useState(false);

  useEffect(() => {
    let alive = true;
    getCategories().then(data => { if (alive) setCategories(data); })
      .catch(() => { if (alive) setCategoryError(true); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    // ПРОБЛЕМА: быстрые переключения фильтров могли возвращать неактуальные результаты.
    // РЕШЕНИЕ: старые ответы не могут перезаписывать данные новой страницы.
    let alive = true;
    setLoading(true);
    setError('');
    getAuctions(filters).then(data => {
      if (!alive) return;
      setAuctions(data.results);
      setCount(data.count);
    }).catch(() => { if (alive) setError('Не удалось получить аукционы. Проверьте подключение к Django API.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [filters]);

  return (
    <div>
      <header className="rea-page-heading">
        <div><div className="rea-page-kicker">НАЙДИТЕ ПОДХОДЯЩУЮ ЗАДАЧУ</div><h1>Каталог аукционов<span style={{ color: '#e97724' }}>.</span></h1><p>Изучайте задачи, сравнивайте бюджеты и участвуйте в открытых торгах.</p></div>
        <Link to="/auctions/new"><Button type="primary" size="large" icon={<PlusOutlined />}>Создать заказ</Button></Link>
      </header>
      <section className="rea-feature-band">
        <div><h2>Ваши навыки — новые возможности ✦</h2><p>Выберите интересную задачу и предложите одну открытую ставку. Побеждает минимальная, а итог определяется правилом второй цены.</p></div>
        <Link to="/design-preview"><Button size="large">Как работают торги <ArrowRightOutlined /></Button></Link>
      </section>
      <div className="rea-info-strip">📊 Суммы и авторы ставок видны всем вошедшим участникам. Изменить отправленную ставку нельзя.</div>
      <div className="rea-filter-card">
        <Space wrap size="middle" style={{ width: '100%' }}>
          <Input.Search style={{ width: 310, maxWidth: '100%' }} size="large" allowClear prefix={<SearchOutlined />} placeholder="Поиск по названию или описанию" value={query} onChange={e => setQuery(e.target.value)} onSearch={value => setFilters(prev => ({ ...prev, search: value.trim() || undefined, page: 1 }))} />
          <Select size="large" style={{ width: 190 }} allowClear value={filters.status} placeholder="Все статусы" options={STATUSES} onChange={value => setFilters(prev => ({ ...prev, status: value, page: 1 }))} />
          <Select size="large" style={{ width: 210 }} allowClear value={filters.category} placeholder="Все категории" options={categories.map(c => ({ value: c.id, label: c.name }))} onChange={value => setFilters(prev => ({ ...prev, category: value, page: 1 }))} />
          <Button size="large" onClick={() => { setQuery(''); setFilters({ status: 'open', page: 1 }); }}>Сбросить</Button>
        </Space>
      </div>
      {categoryError && <Alert style={{ marginBottom: 15 }} type="warning" showIcon message="Не удалось загрузить категории" />}
      {error && <Alert style={{ marginBottom: 15 }} type="error" showIcon message={error} action={<Button onClick={() => setFilters(prev => ({ ...prev }))}>Повторить</Button>} />}
      <div className="rea-page-heading" style={{ marginBottom: 16 }}>
        <div><h2 style={{ margin: 0, fontSize: 21 }}>Доступные задачи</h2></div>
        <span style={{ color: '#8796b0', fontSize: 12 }}>Всего: {count}</span>
      </div>
      {loading ? <Spin size="large" style={{ display: 'block', margin: '60px auto' }} /> : error ? null : auctions.length === 0 ? <Empty description="По выбранным фильтрам задач не найдено" /> : (
        <>
          <div className="rea-auction-grid">
            {auctions.map(a => <AuctionTile key={a.id} auction={a} category={categories.find(c => c.id === a.category)?.name} />)}
          </div>
          <Pagination style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 27 }} current={filters.page ?? 1} pageSize={20} total={count} showSizeChanger={false} showTotal={value => `Всего: ${value}`} onChange={page => setFilters(prev => ({ ...prev, page }))} />
        </>
      )}
    </div>
  );
}

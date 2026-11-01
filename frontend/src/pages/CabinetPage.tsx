import { Badge, Button, Col, Empty, Pagination, Row, Space, Spin, Tabs, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuctions } from '../api/auctions';
import type { Auction, AuctionStatus } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';

function kopecksToRubles(k: number) {
  return (k / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
}

const CABINET_STATUSES: AuctionStatus[] = ['draft', 'rejected', 'review', 'open', 'closed', 'paused'];

function AuctionRow({ auction }: { auction: Auction }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '8px 0',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <StatusBadge status={auction.status} />
      <Link to={`/auctions/${auction.id}`} style={{ flex: 1 }}>
        {auction.title}
      </Link>
      <Typography.Text type="secondary">{kopecksToRubles(auction.budget_kopecks)}</Typography.Text>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        до {new Date(auction.ends_at).toLocaleDateString('ru-RU')}
      </Typography.Text>
    </div>
  );
}

export function CabinetPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    // ПРОБЛЕМА: кабинет показывал только первую страницу аукционов (20 записей).
    // РЕШЕНИЕ: добавляем постраничную навигацию по серверному count.
    getAuctions({ mine: true, page })
      .then((res) => { setAuctions(res.results); setTotal(res.count); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [page]);

  if (loading) return <Spin style={{ display: 'block', margin: '64px auto' }} />;

  const grouped = CABINET_STATUSES.reduce<Record<AuctionStatus, Auction[]>>(
    (acc, s) => {
      acc[s] = auctions.filter((a) => a.status === s);
      return acc;
    },
    {} as Record<AuctionStatus, Auction[]>,
  );

  const statusLabels: Record<AuctionStatus, string> = {
    draft: 'Черновики',
    rejected: 'Отклонённые',
    review: 'На модерации',
    open: 'Открытые',
    closed: 'Закрытые',
    paused: 'Приостановлены',
  };

  const tabItems = CABINET_STATUSES.filter((s) => grouped[s].length > 0).map((s) => ({
    key: s,
    label: (
      <Space>
        {statusLabels[s]}
        <Badge count={grouped[s].length} style={{ backgroundColor: '#1677ff' }} />
      </Space>
    ),
    children:
      grouped[s].length === 0 ? (
        <Empty description="Нет задач" />
      ) : (
        grouped[s].map((a) => <AuctionRow key={a.id} auction={a} />)
      ),
  }));

  return (
    <div>
      <header className="rea-page-heading"><div><div className="rea-page-kicker">МОЁ РАБОЧЕЕ ПРОСТРАНСТВО</div><h1>Мои заказы</h1><p>Черновики, заявки на проверке, активные и завершённые аукционы.</p></div><Link to="/auctions/new"><Button size="large" type="primary" icon={<PlusOutlined />}>Создать заказ</Button></Link></header>
      <div className="rea-info-strip">Здесь отображаются только заказы, которые вы создали. Свои ставки на чужие аукционы можно увидеть в карточках этих аукционов; общего списка ставок текущий API пока не предоставляет.</div>
      <Row gutter={24}>
        <Col xs={24}>
          {tabItems.length === 0 ? (
            <Empty description="У вас пока нет задач" />
          ) : (
            <><Tabs items={tabItems} /><Pagination current={page} pageSize={20} total={total} onChange={setPage} /></>
          )}
        </Col>
      </Row>
    </div>
  );
}

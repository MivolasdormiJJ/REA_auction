import { Button, Empty, Spin, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAuctions } from '../api/auctions';
import type { Auction } from '../api/types';

function kopecksToRubles(k: number) {
  return (k / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
}

export function ModerationPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const load = () => {
    setLoading(true);
    // ПРОБЛЕМА: API возвращает лишь 20 записей, остальные заявки модераторы не видели.
    // РЕШЕНИЕ: передаём номер страницы и используем общее число записей.
    getAuctions({ status: 'review', page })
      .then((res) => { setAuctions(res.results); setTotal(res.count); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [page]);

  const columns: ColumnsType<Auction> = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
    },
    {
      title: 'Заголовок',
      dataIndex: 'title',
      render: (title: string, record) => (
        <Link to={`/auctions/${record.id}`}>{title}</Link>
      ),
    },
    {
      title: 'Бюджет',
      dataIndex: 'budget_kopecks',
      render: (v: number) => kopecksToRubles(v),
      width: 140,
    },
    {
      title: 'Торги до',
      dataIndex: 'ends_at',
      render: (v: string) => new Date(v).toLocaleString('ru-RU'),
      width: 180,
    },
    {
      title: 'Действие',
      render: (_, record) => (
        <Link to={`/auctions/${record.id}`}>
          <Button size="small" type="primary">
            Рассмотреть
          </Button>
        </Link>
      ),
      width: 120,
    },
  ];

  return (
    <div>
      <header className="rea-page-heading"><div><div className="rea-page-kicker">КОНТРОЛЬ КАЧЕСТВА</div><h1>Очередь модерации</h1><p>Проверяйте условия задач перед публикацией для исполнителей.</p></div><Button size="large" onClick={load} loading={loading}>Обновить список</Button></header>
      <div className="rea-info-strip">Каждое решение требует причины. Вы не можете модерировать собственные заказы.</div>

      {loading ? (
        <Spin style={{ display: 'block', margin: '64px auto' }} />
      ) : auctions.length === 0 ? (
        <Empty description="Очередь пуста" />
      ) : (
        <Table
          dataSource={auctions}
          columns={columns}
          rowKey="id"
          pagination={{ current: page, pageSize: 20, total, onChange: setPage }}
        />
      )}
    </div>
  );
}

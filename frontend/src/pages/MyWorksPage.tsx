import { Alert, Button, Card, Empty, Pagination, Space, Spin, Tabs, Tag, Typography } from 'antd';
import { CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import client from '../api/client';
import type { PaginatedResponse } from '../api/types';

type WorkStatus = 'not_started' | 'in_progress' | 'submitted' | 'revision_requested' | 'accepted';
type WorkItem = {
  auction_id: number;
  title: string;
  description: string;
  category: string;
  status: WorkStatus;
  payment_kopecks: number | null;
  due_at: string;
  closed_at: string | null;
  accepted_at: string | null;
  is_overdue: boolean;
  latest_result: string | null;
  latest_feedback: string | null;
  latest_revision: number | null;
};
type Section = 'active' | 'accepted';
const statusText: Record<WorkStatus, string> = {
  not_started: 'Ещё не начата',
  in_progress: 'В работе',
  submitted: 'Ожидает приёмки',
  revision_requested: 'Требует доработки',
  accepted: 'Принята',
};
const money = (kopecks: number | null) => kopecks === null ? '—'
  : (kopecks / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' });

export function MyWorksPage() {
  const [section, setSection] = useState<Section>('active');
  const [page, setPage] = useState(1);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [data, setData] = useState<PaginatedResponse<WorkItem> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    client.get<PaginatedResponse<WorkItem>>('/my/works/', { params: { status: section, page } })
      .then(({ data: response }) => { if (active) setData(response); })
      .catch(() => { if (active) { setData(null); setError('Не удалось загрузить ваши работы. Попробуйте обновить страницу.'); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [section, page, refreshVersion]);

  function changeSection(value: string) {
    setSection(value as Section);
    setPage(1);
    setExpandedId(null);
  }
  return <div>
    <header className="rea-page-heading">
      <div>
        <div className="rea-page-kicker">ПОРТФОЛИО И ВЫПОЛНЕНИЕ</div>
        <h1>Мои работы</h1>
        <p>Выигранные вами заказы: текущие задачи, отправленные результаты и уже принятые работы.</p>
      </div>
    </header>
    <div className="rea-info-strip">
      В этом разделе отображаются работы, где вы стали исполнителем-победителем.
      Ваши собственные заказы находятся в разделе «Мои заказы».
    </div>
    <Space wrap style={{ marginBottom: 16 }}>
      <Button icon={<ReloadOutlined />} onClick={() => setRefreshVersion(n => n + 1)}>Обновить</Button>
      <Link to="/auctions"><Button>Найти новые задания</Button></Link>
    </Space>
    <Tabs activeKey={section} onChange={changeSection} items={[
      { key: 'active', label: <Space><ClockCircleOutlined />В процессе</Space> },
      { key: 'accepted', label: <Space><CheckCircleOutlined />Принятые работы</Space> },
    ]} />
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 16 }} />}
    {loading ? <Spin style={{ display: 'block', margin: '48px auto' }} />
      : data?.results.length ? <>
        <div style={{ display: 'grid', gap: 16 }}>
          {data.results.map(work => <Card key={work.auction_id} title={
            <Space wrap>
              <FileTextOutlined />
              <Link to={`/auctions/${work.auction_id}`}>{work.title}</Link>
              <Tag color={work.status === 'accepted' ? 'success' : work.status === 'revision_requested' ? 'warning' : 'processing'}>
                {statusText[work.status]}
              </Tag>
              {work.is_overdue && <Tag color="error">Срок прошёл</Tag>}
            </Space>
          }>
            <Space wrap style={{ marginBottom: 12 }}>
              <Typography.Text type="secondary">{work.category}</Typography.Text>
              <Typography.Text type="secondary">Итоговая цена: {money(work.payment_kopecks)}</Typography.Text>
              <Typography.Text type="secondary">Срок: {new Date(work.due_at).toLocaleDateString('ru-RU')}</Typography.Text>
              {work.accepted_at && <Typography.Text type="success">Принято: {new Date(work.accepted_at).toLocaleDateString('ru-RU')}</Typography.Text>}
            </Space>
            <Typography.Paragraph ellipsis={{ rows: 2, expandable: false }}>{work.description}</Typography.Paragraph>
            {work.latest_feedback && work.status === 'revision_requested' &&
              <Alert type="warning" showIcon style={{ marginBottom: 12 }} message="Замечания заказчика" description={work.latest_feedback} />}
            <Space wrap>
              <Link to={`/auctions/${work.auction_id}`}>
                <Button type="primary">{work.status === 'accepted' ? 'Открыть принятую работу' : 'Перейти к выполнению'}</Button>
              </Link>
              {work.latest_result && <Button onClick={() => setExpandedId(expandedId === work.auction_id ? null : work.auction_id)}>
                {expandedId === work.auction_id ? 'Скрыть результат' : 'Посмотреть результат'}
              </Button>}
            </Space>
            {expandedId === work.auction_id && work.latest_result && <div style={{
              marginTop: 16, padding: 16, borderRadius: 8, background: '#f5f7fa',
              whiteSpace: 'pre-wrap', overflowWrap: 'anywhere',
            }}>
              <Typography.Text strong>Версия №{work.latest_revision ?? 1}</Typography.Text>
              <div style={{ marginTop: 8 }}>{work.latest_result}</div>
              <Typography.Paragraph type="secondary" style={{ marginTop: 12, marginBottom: 0 }}>
                Полная история версий, замечаний и приёмки — в карточке заказа.
              </Typography.Paragraph>
            </div>}
          </Card>)}
        </div>
        <Pagination style={{ marginTop: 22 }} current={page} pageSize={12} total={data.count}
          showSizeChanger={false} onChange={setPage} />
      </> : !error && <Empty style={{ marginTop: 36 }}
        description={section === 'accepted' ? 'У вас пока нет принятых заказчиком работ' : 'У вас пока нет работ в процессе'}>
        <Link to="/auctions"><Button type="primary">Перейти в каталог</Button></Link>
      </Empty>}
  </div>;
}

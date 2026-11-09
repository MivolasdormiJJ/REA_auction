import { ArrowLeftOutlined, CheckCircleOutlined, TrophyOutlined, UserOutlined } from '@ant-design/icons';
import { Alert, Avatar, Button, Card, Col, Empty, Progress, Rate, Row, Space, Spin, Statistic, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import client from '../api/client';
import type { PerformerReputation } from '../api/types';

export function PerformerProfilePage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PerformerReputation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    client.get<PerformerReputation>(`/performers/${id}/reputation/`)
      .then(response => { if (active) setData(response.data); })
      .catch(() => { if (active) setError(true); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (loading) return <Spin style={{ display: 'block', margin: '64px auto' }} />;
  if (error || !data) return <Alert type="error" showIcon message="Профиль исполнителя не найден" />;

  const maxDistribution = Math.max(1, ...Object.values(data.rating_distribution));
  return <div>
    <div style={{ marginBottom: 18 }}><Link to="/auctions"><Button icon={<ArrowLeftOutlined />}>К аукционам</Button></Link></div>
    <div className="rea-profile-hero">
      <Avatar size={72} icon={<UserOutlined />}>{data.performer.username.slice(0, 2).toUpperCase()}</Avatar>
      <div>
        <div className="rea-page-kicker" style={{ color: '#ffd7b8' }}>ПРОФИЛЬ ИСПОЛНИТЕЛЯ</div>
        <h2>{data.performer.username}</h2>
        <Space wrap><Rate disabled allowHalf value={data.average_rating ?? 0} /><strong>{data.average_rating?.toFixed(1) ?? 'Новый исполнитель'}</strong><span>· {data.reviews_count} отзывов</span></Space>
      </div>
    </div>

    <Row gutter={[20, 20]}>
      <Col xs={24} lg={8}>
        <Card title="Репутация">
          <Row gutter={[12, 18]}>
            <Col span={12}><Statistic title="Средняя оценка" value={data.average_rating ?? 0} precision={1} suffix="/ 5" /></Col>
            <Col span={12}><Statistic title="Отзывов" value={data.reviews_count} /></Col>
            <Col span={12}><Statistic title="Выполнено работ" value={data.completed_tasks_count} prefix={<CheckCircleOutlined />} /></Col>
            <Col span={12}><Statistic title="Побед в торгах" value={data.wins_count} prefix={<TrophyOutlined />} /></Col>
          </Row>
          <div style={{ marginTop: 22 }}>
            {[5, 4, 3, 2, 1].map(score => <div key={score} style={{ display: 'grid', gridTemplateColumns: '36px 1fr 28px', gap: 8, alignItems: 'center', marginBottom: 8 }}>
              <span>{score} ★</span>
              <Progress percent={(data.rating_distribution[String(score)] / maxDistribution) * 100} showInfo={false} strokeColor="#ee7b27" />
              <span>{data.rating_distribution[String(score)]}</span>
            </div>)}
          </div>
        </Card>
      </Col>
      <Col xs={24} lg={16}>
        <Card title={`Отзывы заказчиков (${data.reviews_count})`}>
          {data.reviews.length === 0 ? <Empty description="У исполнителя пока нет отзывов" /> : data.reviews.map(review => <div key={review.id} className="rea-review-item">
            <Space wrap><Rate disabled value={review.rating} /><Typography.Text strong>{review.rating}.0</Typography.Text><Typography.Text type="secondary">{new Date(review.created_at).toLocaleDateString('ru-RU')}</Typography.Text></Space>
            <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', margin: '12px 0 9px', lineHeight: 1.7 }}>{review.comment}</Typography.Paragraph>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>Заказчик: {review.reviewer_username} · <Link to={`/auctions/${review.auction_id}`}>{review.auction_title}</Link></Typography.Text>
          </div>)}
        </Card>
      </Col>
    </Row>
  </div>;
}

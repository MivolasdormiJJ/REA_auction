import { Alert, Avatar, Button, Card, Col, Descriptions, Row, Space, Spin, Statistic, Tag, Typography } from 'antd';
import { BookOutlined, CheckCircleOutlined, LockOutlined, PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import client from '../api/client';
import { useAuth } from '../context/AuthContext';
import '../app-theme.css';

type UserStatistics = {
  bids_count: number;
  wins_count: number;
  completed_tasks_count: number;
  active_bids_count: number;
  auctions_created_count: number;
  auctions_closed_count: number;
  win_rate_percent: number;
};

export function ProfilePage() {
  const [stats, setStats] = useState<UserStatistics | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);
  useEffect(() => {
    let active = true;
    client.get<UserStatistics>('/my/statistics/')
      .then(({ data }) => { if (active) setStats(data); })
      .catch(() => { if (active) setStatsError(true); })
      .finally(() => { if (active) setStatsLoading(false); });
    return () => { active = false; };
  }, []);
  const { user } = useAuth();
  if (!user) return null;
  return (
    <div>
      <div className="rea-page-heading"><div>
        <div className="rea-page-kicker">ЛИЧНЫЙ ПРОФИЛЬ</div>
        <h1>Мой профиль</h1>
        <p>Информация об учётной записи и быстрый доступ к вашим действиям.</p>
      </div></div>
      <div className="rea-profile-hero">
        <Avatar size={72}>{user.username.slice(0, 2).toUpperCase()}</Avatar>
        <div><h2>{user.username}</h2><p>{user.can_moderate ? 'Участник и модератор REA Auction' : 'Участник REA Auction'}</p></div>
      </div>
      <Card title="Моя статистика" style={{ marginBottom: 20 }}>
        {statsError && <Alert type="error" showIcon message="Не удалось загрузить статистику" />}
        {statsLoading ? <Spin /> : stats && <>
          <Row gutter={[16, 20]}>
            <Col xs={12} md={6}><Statistic title="Сделано ставок" value={stats.bids_count} /></Col>
            <Col xs={12} md={6}><Statistic title="Побед в торгах" value={stats.wins_count} /></Col>
            <Col xs={12} md={6}><Statistic title="Выполнено заданий" value={stats.completed_tasks_count} /></Col>
            <Col xs={12} md={6}><Statistic title="Процент побед" value={stats.win_rate_percent} suffix="%" precision={1} /></Col>
          </Row>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 16, marginBottom: 0 }}>
            Создано заказов: {stats.auctions_created_count} · Завершено торгов по вашим заказам: {stats.auctions_closed_count} · Активных ставок: {stats.active_bids_count}.
            Выполненным считается только задание, результат которого подтвердил заказчик после окончания торгов.
          </Typography.Paragraph>
        </>}
      </Card>
      <Row gutter={[20, 20]}>
        <Col xs={24} lg={15}>
          <Card title="Данные аккаунта">
            {/* ПРОБЛЕМА: текущий Django API возвращает только id, username и права.
                РЕШЕНИЕ: отображаем подтверждённые данные, не выдумываем email,
                рейтинг, баланс и не добавляем несуществующее сохранение профиля. */}
            <Descriptions bordered column={1} size="middle">
              <Descriptions.Item label="Имя пользователя">{user.username}</Descriptions.Item>
              <Descriptions.Item label="ID участника">#{user.id}</Descriptions.Item>
              <Descriptions.Item label="Статус"><Tag color="success" icon={<CheckCircleOutlined />}>Аккаунт активен</Tag></Descriptions.Item>
              <Descriptions.Item label="Права">{user.can_moderate ? <Tag color="geekblue">Модератор</Tag> : 'Участник торгов'}</Descriptions.Item>
              <Descriptions.Item label="Безопасность"><Space><LockOutlined /> Ставки участников открыты</Space></Descriptions.Item>
            </Descriptions>
          </Card>

        </Col>
        <Col xs={24} lg={9}>
          <Card title="Быстрые действия">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Link to="/cabinet"><Button block size="large">Посмотреть мои заказы</Button></Link>
              <Link to="/auctions/new"><Button block type="primary" size="large" icon={<PlusOutlined />}>Создать задачу</Button></Link>
              <Link to="/design-preview"><Button block size="large" icon={<BookOutlined />}>Как работают торги</Button></Link>
              {user.can_moderate && <Link to="/moderation"><Button block size="large" icon={<SafetyCertificateOutlined />}>Открыть модерацию</Button></Link>}
            </Space>
          </Card>
          <Card style={{ marginTop: 20 }} title="Что важно знать">
            <Typography.Paragraph type="secondary">
              Исполнитель может отправить одну неизменяемую открытую ставку на аукцион.
              Побеждает минимальная ставка, а итоговая цена при двух и более ставках равна второй минимальной.
            </Typography.Paragraph>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

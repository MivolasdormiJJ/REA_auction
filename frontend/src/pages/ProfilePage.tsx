import { Avatar, Button, Card, Col, Descriptions, Row, Space, Tag, Typography } from 'antd';
import { BookOutlined, CheckCircleOutlined, LockOutlined, PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import '../app-theme.css';

export function ProfilePage() {
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

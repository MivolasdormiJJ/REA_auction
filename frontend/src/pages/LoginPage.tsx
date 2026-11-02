import { BrandLogo } from '../components/BrandLogo';
import { Alert, Button, Form, Input, Typography } from 'antd';
import { ArrowRightOutlined, LockOutlined, SafetyCertificateOutlined, UserOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { login } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import '../app-theme.css';

export function LoginPage() {
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: { username: string; password: string }) => {
    setLoading(true);
    setError('');
    try {
      const user = await login(values.username, values.password);
      setUser(user);
      navigate('/auctions', { replace: true });
    } catch (err: unknown) {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })?.response;
      // ПРОБЛЕМА: для отсутствующего Django API нельзя сообщать "неверный пароль".
      // РЕШЕНИЕ: отличаем ошибку подключения от ответа сервера.
      setError(response?.data?.detail ?? (response ? 'Не удалось войти. Проверьте учётные данные.' : 'Сервер авторизации недоступен. Запустите Django backend.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="rea-login-shell">
      <section className="rea-login-aside">
        <BrandLogo />
        <div>
          <div className="rea-login-pill">✦ REA AUCTION PLATFORM</div>
          <h1 style={{ marginTop: 25 }}>Делаем сложные торги простыми.</h1>
          <p>Публикуйте задачи, находите исполнителей и участвуйте в прозрачных обратных аукционах с открытыми предложениями.</p>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', color: '#e3e8ff', fontSize: 12, marginTop: 25 }}>
            <span><SafetyCertificateOutlined /> Прозрачные правила</span>
            <span><LockOutlined /> Открытые ставки</span>
          </div>
        </div>
        <Link style={{ color: '#e8eeff', fontSize: 13 }} to="/design-preview">Узнать, как работают торги <ArrowRightOutlined /></Link>
      </section>
      <section className="rea-login-form-wrap">
        <div className="rea-login-card">
          <div className="rea-page-kicker">ДОБРО ПОЖАЛОВАТЬ</div>
          <h2>Вход в аккаунт</h2>
          <p>Введите данные своей учётной записи, чтобы перейти к настоящим аукционам.</p>
          {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 23 }} />}
          <Form layout="vertical" size="large" onFinish={onFinish} requiredMark={false}>
            <Form.Item name="username" label="Имя пользователя" rules={[{ required: true, message: 'Введите имя пользователя' }]}>
              <Input autoComplete="username" prefix={<UserOutlined style={{ color: '#98a4bb' }} />} placeholder="Ваш логин" />
            </Form.Item>
            <Form.Item name="password" label="Пароль" rules={[{ required: true, message: 'Введите пароль' }]}>
              <Input.Password autoComplete="current-password" prefix={<LockOutlined style={{ color: '#98a4bb' }} />} placeholder="Введите пароль" />
            </Form.Item>
            <Form.Item style={{ marginBottom: 15 }}>
              <Button type="primary" htmlType="submit" block loading={loading}>Войти <ArrowRightOutlined /></Button>
            </Form.Item>
          </Form>
          <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>
            Ещё нет аккаунта? <Link to="/register" style={{ color: '#d46d20', fontWeight: 750 }}>Зарегистрироваться</Link>
          </Typography.Paragraph>
          <div style={{ borderTop: '1px solid #eef1f8', paddingTop: 20, marginTop: 17 }}>
            <Link to="/design-preview" style={{ color: '#d46d20', fontSize: 13, fontWeight: 750 }}>Сначала посмотреть демонстрацию →</Link>
          </div>
        </div>
      </section>
    </main>
  );
}

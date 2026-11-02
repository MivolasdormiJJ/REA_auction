import { Alert, Button, Form, Input } from 'antd';
import { ArrowRightOutlined, LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import { Link } from 'react-router-dom';
import { useState } from 'react';
import { register } from '../api/auth';
import '../app-theme.css';

type RegistrationForm = { username: string; email: string; password: string; confirm: string };

function getError(err: unknown): string {
  const response = (err as { response?: { data?: { detail?: string; username?: string[]; email?: string[]; password?: string[] } } })?.response;
  if (!response) return 'Не удалось подключиться к серверу. Попробуйте позднее.';
  const data = response.data;
  return data?.detail || data?.username?.join(' ') || data?.email?.join(' ') || data?.password?.join(' ') || 'Не удалось зарегистрироваться. Проверьте введённые данные.';
}

export function RegisterPage() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const submit = async (values: RegistrationForm) => {
    setPending(true);
    setError('');
    try {
      await register(values.username.trim(), values.email.trim(), values.password);
      setSuccess(true);
    } catch (err) {
      setError(getError(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="rea-login-shell">
      <section className="rea-login-aside">
        <Link to="/design-preview" aria-label="РЭУ им. Г. В. Плеханова"><img className="rea-anniversary-logo" src={`${import.meta.env.BASE_URL}rea-logo.svg`} alt="120 лет РЭУ им. Г. В. Плеханова" /></Link>
        <div>
          <div className="rea-login-pill">✦ ДОБРО ПОЖАЛОВАТЬ В REA AUCTION</div>
          <h1 style={{ marginTop: 25 }}>Создайте аккаунт. Начните участвовать.</h1>
          <p>Один аккаунт — чтобы размещать заказы и участвовать в аукционах. Суммы ставок открыты для участников аукциона.</p>
        </div>
        <Link style={{ color: '#e8eeff', fontSize: 13 }} to="/design-preview">Узнать, как работают торги <ArrowRightOutlined /></Link>
      </section>
      <section className="rea-login-form-wrap">
        <div className="rea-login-card">
          <div className="rea-page-kicker">ПРИСОЕДИНЯЙТЕСЬ</div>
          <h2>Регистрация</h2>
          {success ? (
            <>
              <Alert type="success" showIcon message="Аккаунт создан" description="Подтверждение email не требуется. Теперь можно войти с вашим логином и паролем." style={{ marginBottom: 22 }} />
              <Link to="/login"><Button size="large" block type="primary">Перейти ко входу</Button></Link>
            </>
          ) : (
            <>
              <p>Введите логин, адрес электронной почты и надёжный пароль. Подтверждение почты не требуется.</p>
              {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 20 }} />}
              <Form<RegistrationForm> layout="vertical" size="large" requiredMark={false} onFinish={submit}>
                <Form.Item name="username" label="Имя пользователя" rules={[{ required: true, message: 'Укажите логин' }, { min: 3, message: 'Не менее 3 символов' }]}>
                  <Input autoComplete="username" maxLength={150} prefix={<UserOutlined />} placeholder="Например, alex2026" />
                </Form.Item>
                <Form.Item name="email" label="Email" rules={[{ required: true, message: 'Введите email' }, { type: 'email', message: 'Некорректный email' }]}>
                  <Input autoComplete="email" maxLength={254} prefix={<MailOutlined />} placeholder="name@example.com" />
                </Form.Item>
                <Form.Item name="password" label="Пароль" rules={[{ required: true, message: 'Введите пароль' }, { min: 12, message: 'Не менее 12 символов' }]}>
                  <Input.Password autoComplete="new-password" maxLength={128} prefix={<LockOutlined />} placeholder="Минимум 12 символов" />
                </Form.Item>
                <Form.Item name="confirm" label="Повторите пароль" dependencies={['password']} rules={[{ required: true, message: 'Повторите пароль' }, ({ getFieldValue }) => ({ validator(_, value: string) { return value === getFieldValue('password') ? Promise.resolve() : Promise.reject(new Error('Пароли не совпадают')); } })]}>
                  <Input.Password autoComplete="new-password" prefix={<LockOutlined />} placeholder="Подтверждение пароля" />
                </Form.Item>
                {/* ПРОБЛЕМА: регистрации раньше требовалось письмо.
                    РЕШЕНИЕ: после успешного создания аккаунта предлагаем сразу войти. */}
                <Button type="primary" htmlType="submit" block loading={pending}>Создать аккаунт <ArrowRightOutlined /></Button>
              </Form>
            </>
          )}
          <p style={{ marginTop: 22, marginBottom: 0, textAlign: 'center' }}>Уже зарегистрированы? <Link to="/login" style={{ color: '#d46d20', fontWeight: 750 }}>Войти</Link></p>
        </div>
      </section>
    </main>
  );
}

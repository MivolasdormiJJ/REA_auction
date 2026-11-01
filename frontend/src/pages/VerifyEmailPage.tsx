import { Alert, Button, Spin } from 'antd';
import { Link, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { verifyEmail } from '../api/auth';
import '../app-theme.css';

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const uid = params.get('uid') ?? '';
  const token = params.get('token') ?? '';
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState('');
  useEffect(() => {
    // ПРОБЛЕМА: запрос GET по почтовой ссылке может быть вызван ботом-проверяльщиком.
    // РЕШЕНИЕ: токен активируется только через POST с CSRF. Запрос повторно безопасен.
    let cancelled = false;
    if (!uid || !token) {
      setStatus('error');
      setError('Некорректная ссылка подтверждения');
      return;
    }
    verifyEmail(uid, token).then(() => {
      if (!cancelled) setStatus('success');
    }).catch((err: unknown) => {
      if (cancelled) return;
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail || 'Срок действия ссылки истёк или подтверждение недоступно.');
      setStatus('error');
    });
    return () => { cancelled = true; };
  }, [uid, token]);

  return <main className="rea-login-form-wrap" style={{ minHeight: '100vh', background: '#f7f9ff' }}>
    <section className="rea-login-card">
      <div className="rea-page-kicker">ПОДТВЕРЖДЕНИЕ ПОЧТЫ</div>
      <h2>Подтверждение email</h2>
      {status === 'loading' && <div><Spin /> <p>Проверяем вашу ссылку...</p></div>}
      {status === 'success' && <Alert type="success" showIcon message="Email подтверждён" description="Теперь вы можете войти и участвовать в аукционах." style={{ marginBottom: 22 }} />}
      {status === 'error' && <Alert type="error" showIcon message={error} style={{ marginBottom: 22 }} />}
      {status !== 'loading' && <Link to="/login"><Button type="primary" block size="large">Перейти ко входу</Button></Link>}
    </section>
  </main>;
}

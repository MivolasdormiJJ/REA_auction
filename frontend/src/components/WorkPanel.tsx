import { Alert, Button, Card, Divider, Input, Space, Spin, Tag, Timeline, Typography, message } from 'antd';
import { useEffect, useRef, useState } from 'react';
import client from '../api/client';
import type { Auction } from '../api/types';

type Submission = {
  id: number; revision_number: number; result_text: string; created_at: string;
  review_status: 'pending' | 'revision' | 'accepted'; feedback: string; reviewed_at: string | null;
};
type Work = {
  auction_id: number; owner_id: number; winner_id: number | null;
  status: 'not_started' | 'in_progress' | 'submitted' | 'revision_requested' | 'accepted';
  started_at: string | null; accepted_at: string | null; due_at: string;
  is_overdue: boolean; submissions: Submission[];
};
const labels: Record<Work['status'], string> = {
  not_started: 'Ожидает начала работы', in_progress: 'Исполнитель работает',
  submitted: 'Результат на приёмке', revision_requested: 'Ожидает доработки', accepted: 'Работа принята',
};

export function WorkPanel({ auction, userId }: { auction: Auction; userId: number | undefined }) {
  const [work, setWork] = useState<Work | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState('');
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');
  const pendingSubmission = useRef<{ text: string; key: string } | null>(null);
  const winner = userId === auction.winner_id;
  const owner = userId === auction.owner_id;

  async function refresh() {
    const { data } = await client.get<Work>(`/auctions/${auction.id}/work/`);
    setWork(data);
  }
  useEffect(() => {
    let alive = true;
    setLoading(true);
    client.get<Work>(`/auctions/${auction.id}/work/`)
      .then(({ data }) => { if (alive) setWork(data); })
      .catch(() => { if (alive) setError('Не удалось загрузить выполнение заказа'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [auction.id]);

  async function perform(action: 'start' | 'submit' | 'accept' | 'request-revision') {
    if (pending) return;
    if (action === 'accept' && !window.confirm('Принять результат и подтвердить выполнение задания?')) return;
    if (action === 'submit' && (result.trim().length < 20 || result.trim().length > 10000)) {
      setError('Опишите результат работы: от 20 до 10000 символов'); return;
    }
    if (action === 'request-revision' && (feedback.trim().length < 5 || feedback.trim().length > 2000)) {
      setError('Укажите причину доработки: от 5 до 2000 символов'); return;
    }
    setPending(true);
    setError('');
    try {
      const headers: Record<string,string> = {};
      if (action === 'submit') {
        const text = result.trim();
        if (pendingSubmission.current?.text !== text) pendingSubmission.current = { text, key: crypto.randomUUID() };
        headers['Idempotency-Key'] = pendingSubmission.current.key;
      }
      const payload = action === 'submit' ? { result_text: result.trim() }
        : action === 'request-revision' ? { feedback: feedback.trim() } : {};
      const { data } = await client.post<Work>(`/auctions/${auction.id}/work/${action}/`, payload, { headers });
      pendingSubmission.current = null;
      setWork(data);
      if (action === 'submit') setResult('');
      if (action === 'request-revision') setFeedback('');
      message.success({
        start: 'Заказ взят в работу', submit: 'Результат отправлен заказчику',
        accept: 'Работа принята. Статистика обновлена.',
        'request-revision': 'Отправлено на доработку',
      }[action]);
    } catch (err: unknown) {
      const response = (err as { response?: { status?: number; data?: { detail?: string } } })?.response;
      setError(response?.data?.detail ?? 'Не удалось выполнить действие. Проверьте подключение и повторите попытку.');
      if (response?.status === 409) {
        pendingSubmission.current = null;
        void refresh().catch(() => {});
      }
    } finally {
      setPending(false);
    }
  }

  if (!owner && !winner) return null;
  return <Card title="Выполнение заказа и приёмка работы" style={{ marginTop: 20 }}>
    {loading ? <Spin /> : <>
      {error && <Alert type="error" showIcon style={{ marginBottom: 12 }} message={error} />}
      {work && <>
        <Space wrap style={{ marginBottom: 16 }}>
          <Tag color={work.status === 'accepted' ? 'success' : work.status === 'revision_requested' ? 'warning' : 'processing'}>
            {labels[work.status]}
          </Tag>
          <Typography.Text type="secondary">Срок: {new Date(work.due_at).toLocaleString('ru-RU')}</Typography.Text>
          {work.is_overdue && <Tag color="error">Срок выполнения прошёл</Tag>}
        </Space>
        {work.status === 'not_started' && (
          winner
            ? <Button type="primary" loading={pending} onClick={() => void perform('start')}>Взять заказ в работу</Button>
            : <Alert showIcon type="info" message="Ожидаем, когда победитель начнёт работу" />
        )}
        {winner && (work.status === 'in_progress' || work.status === 'revision_requested') && <>
          <Typography.Paragraph type="secondary">
            Опишите выполненную работу, что было сделано и где заказчик может найти результат.
            При доработке отправьте новую версию; предыдущие останутся в истории.
          </Typography.Paragraph>
          <Input.TextArea value={result} onChange={event => setResult(event.target.value)}
            placeholder="Подробно опишите результат и способ проверки (20–10000 символов)"
            autoSize={{ minRows: 4, maxRows: 8 }} maxLength={10000} showCount />
          <Button style={{ marginTop: 14 }} type="primary" loading={pending}
            disabled={result.trim().length < 20} onClick={() => void perform('submit')}>
            Отправить результат на приёмку
          </Button>
        </>}
        {owner && work.status === 'submitted' && <>
          <Alert type="info" showIcon message="Исполнитель отправил работу. Проверьте результат перед решением." style={{ marginBottom: 12 }} />
          <Button type="primary" loading={pending} onClick={() => void perform('accept')}>Принять работу</Button>
          <Divider>Запросить доработку</Divider>
          <Input.TextArea value={feedback} onChange={event => setFeedback(event.target.value)}
            placeholder="Что необходимо исправить? (от 5 символов)"
            maxLength={2000} showCount autoSize={{ minRows: 2, maxRows: 5 }} />
          <Button style={{ marginTop: 12 }} loading={pending}
            disabled={feedback.trim().length < 5} onClick={() => void perform('request-revision')}>
            Вернуть на доработку
          </Button>
        </>}
        {work.status === 'submitted' && winner && <Alert type="info" showIcon message="Результат отправлен. Ожидаем решения заказчика." />}
        {work.status === 'revision_requested' && owner && <Alert type="warning" showIcon message="Запрос на доработку отправлен исполнителю." />}
        {work.status === 'accepted' && <Alert type="success" showIcon message="Работа принята заказчиком" description={work.accepted_at ? `Дата приёмки: ${new Date(work.accepted_at).toLocaleString('ru-RU')}` : undefined} />}
        {work.submissions.length > 0 && <>
          <Divider>История версий и решений</Divider>
          <Timeline items={work.submissions.map(item => ({
            color: item.review_status === 'accepted' ? 'green' : item.review_status === 'revision' ? 'orange' : 'blue',
            children: <div>
              <Typography.Text strong>Версия {item.revision_number} · {new Date(item.created_at).toLocaleString('ru-RU')}</Typography.Text>
              <div style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', marginTop: 7 }}>{item.result_text}</div>
              <Tag style={{ marginTop: 8 }} color={item.review_status === 'accepted' ? 'success' : item.review_status === 'revision' ? 'warning' : 'processing'}>
                {item.review_status === 'accepted' ? 'Принята' : item.review_status === 'revision' ? 'На доработку' : 'На приёмке'}
              </Tag>
              {item.feedback && <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>Комментарий заказчика: {item.feedback}</Typography.Paragraph>}
            </div>,
          }))} />
        </>}
      </>}
    </>}
  </Card>;
}

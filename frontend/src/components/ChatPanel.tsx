import { Alert, Avatar, Button, Card, Empty, Input, Spin, Typography, message } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { useCallback, useEffect, useRef, useState } from 'react';
import client from '../api/client';

type ChatMessage = {
  id: number;
  auction_id: number;
  sender_id: number;
  sender_username: string;
  body: string;
  created_at: string;
};

type ChatPayload = {
  auction_id: number;
  owner: { id: number; username: string };
  winner: { id: number; username: string };
  results: ChatMessage[];
};

function mergeMessages(current: ChatMessage[], incoming: ChatMessage[]) {
  const byId = new Map(current.map(item => [item.id, item]));
  incoming.forEach(item => byId.set(item.id, item));
  return [...byId.values()].sort((left, right) => left.id - right.id);
}

export function ChatPanel({ auctionId, userId }: { auctionId: number; userId: number }) {
  const [chat, setChat] = useState<ChatPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [body, setBody] = useState('');
  const [error, setError] = useState('');
  const lastId = useRef(0);
  const pending = useRef<{ body: string; key: string } | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const refresh = useCallback(async (initial = false) => {
    try {
      const params = !initial && lastId.current ? { after: lastId.current } : undefined;
      const { data } = await client.get<ChatPayload>(`/auctions/${auctionId}/chat/`, { params });
      if (data.results.length) lastId.current = data.results[data.results.length - 1].id;
      setChat(current => current ? { ...data, results: mergeMessages(current.results, data.results) } : data);
      setError('');
    } catch {
      if (initial) setError('Не удалось загрузить чат');
    } finally {
      if (initial) setLoading(false);
    }
  }, [auctionId]);

  useEffect(() => {
    let active = true;
    client.get<ChatPayload>(`/auctions/${auctionId}/chat/`)
      .then(({ data }) => {
        if (!active) return;
        if (data.results.length) lastId.current = data.results[data.results.length - 1].id;
        setChat(data);
        setError('');
      })
      .catch(() => { if (active) setError('Не удалось загрузить чат'); })
      .finally(() => { if (active) setLoading(false); });
    const timer = window.setInterval(() => { if (active) void refresh(); }, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [auctionId, refresh]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [chat?.results.length]);

  async function send() {
    const text = body.trim();
    if (!text || text.length > 2000 || sending) return;
    setSending(true);
    setError('');
    if (!pending.current || pending.current.body !== text) {
      pending.current = { body: text, key: crypto.randomUUID() };
    }
    try {
      const { data } = await client.post<ChatMessage>(
        `/auctions/${auctionId}/chat/`,
        { body: text },
        { headers: { 'Idempotency-Key': pending.current.key } },
      );
      pending.current = null;
      lastId.current = Math.max(lastId.current, data.id);
      setChat(current => current ? { ...current, results: mergeMessages(current.results, [data]) } : current);
      setBody('');
      message.success('Сообщение отправлено');
    } catch (err: unknown) {
      const response = (err as { response?: { status?: number; data?: { detail?: string; body?: string[] } } })?.response;
      setError(response?.data?.detail ?? response?.data?.body?.[0] ?? 'Не удалось отправить сообщение');
      if (response?.status === 409) pending.current = null;
      void refresh();
    } finally {
      setSending(false);
    }
  }

  const partner = chat ? (chat.owner.id === userId ? chat.winner : chat.owner) : null;
  return <Card title="Чат по заказу" extra={partner ? <Typography.Text type="secondary">Собеседник: {partner.username}</Typography.Text> : null} style={{ marginTop: 20 }}>
    {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 12 }} />}
    {loading ? <Spin /> : <>
      <div className="rea-chat-messages" aria-live="polite">
        {!chat?.results.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Сообщений пока нет. Обсудите детали выполнения заказа." /> : chat.results.map(item => {
          const mine = item.sender_id === userId;
          return <div key={item.id} className={`rea-chat-row ${mine ? 'mine' : ''}`}>
            {!mine && <Avatar size={32}>{item.sender_username.slice(0, 2).toUpperCase()}</Avatar>}
            <div className="rea-chat-bubble">
              <div className="rea-chat-meta">{item.sender_username} · {new Date(item.created_at).toLocaleString('ru-RU')}</div>
              <div className="rea-chat-body">{item.body}</div>
            </div>
          </div>;
        })}
        <div ref={endRef} />
      </div>
      <Input.TextArea
        value={body}
        onChange={event => setBody(event.target.value)}
        onPressEnter={event => {
          if (!event.shiftKey) { event.preventDefault(); void send(); }
        }}
        placeholder="Напишите сообщение. Enter — отправить, Shift+Enter — новая строка"
        maxLength={2000}
        showCount
        autoSize={{ minRows: 2, maxRows: 5 }}
        style={{ marginTop: 14 }}
      />
      <Button type="primary" icon={<SendOutlined />} loading={sending} disabled={!body.trim()} onClick={() => void send()} style={{ marginTop: 12 }}>
        Отправить
      </Button>
      <Typography.Paragraph type="secondary" style={{ fontSize: 11, margin: '10px 0 0' }}>
        Чат доступен только заказчику и победителю. История сообщений сохраняется и не редактируется.
      </Typography.Paragraph>
    </>}
  </Card>;
}

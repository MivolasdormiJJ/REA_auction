import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Modal,
  Row,
  Space,
  Spin,
  Typography,
  message,
} from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  approveAuction,
  getAuction,
  getMyBids,
  placeBid,
  rejectAuction,
  submitAuction,
} from '../api/auctions';
import type { Auction, Bid } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { KopecksInput } from '../components/KopecksInput';
import { useAuth } from '../context/AuthContext';

function kopecksToRubles(k: number | null) {
  if (k == null) return '—';
  return (k / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 });
}

export function AuctionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const auctionId = Number(id);
  const { user } = useAuth();
  const navigate = useNavigate();

  const [auction, setAuction] = useState<Auction | null>(null);
  const [myBid, setMyBid] = useState<Bid | null>(null);
  const [allBids, setAllBids] = useState<Bid[]>([]);
  const [loading, setLoading] = useState(true);
  const [bidAmount, setBidAmount] = useState<number | null>(null);
  const [bidding, setBidding] = useState(false);
  const [moderateLoading, setModerateLoading] = useState(false);
  const [reasonModal, setReasonModal] = useState<'approve' | 'reject' | null>(null);
  const [reason, setReason] = useState('');

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // ПРОБЛЕМА: при потере ответа повторная ставка получала новый Idempotency-Key.
  // РЕШЕНИЕ: для той же суммы храним исходный ключ до подтверждения результата.
  const pendingBidRef = useRef<{ amount: number; key: string } | null>(null);

  const loadAuction = async () => {
    try {
      const [a, bids] = await Promise.all([
        getAuction(auctionId),
        getMyBids(auctionId).catch(() => [] as Bid[]),
      ]);
      setAuction(a);
      setAllBids(bids);
      setMyBid(bids.find(b => b.bidder_id === user?.id) ?? null);
    } catch {
      // handled by empty state
    }
  };

  useEffect(() => {
    setLoading(true);
    loadAuction().finally(() => setLoading(false));
  }, [auctionId]);

  // Poll every 5 seconds when auction is open
  useEffect(() => {
    if (auction?.status === 'open') {
      pollRef.current = setInterval(loadAuction, 5000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [auction?.status]);

  const isOwner = user && auction && user.id === auction.owner_id;
  const isModerator = user?.can_moderate;
  const canBid =
    user &&
    auction?.status === 'open' &&
    !isOwner &&
    new Date(auction.ends_at) > new Date() &&
    !myBid;
  const canSubmit = isOwner && (auction?.status === 'draft' || auction?.status === 'rejected');
  const canEdit = isOwner && (auction?.status === 'draft' || auction?.status === 'rejected');
  const canModerate =
    isModerator && auction?.status === 'review' && !isOwner;

  const serverClosed = auction?.status === 'open' && new Date(auction.ends_at) < new Date();

  const handleBid = async () => {
    // ПРОБЛЕМА: двойной клик до изменения state мог вызвать два запроса.
    // РЕШЕНИЕ: не принимаем новый клик во время активной отправки.
    if (!bidAmount || bidding) return;
    setBidding(true);
    try {
      if (!pendingBidRef.current || pendingBidRef.current.amount !== bidAmount) {
        pendingBidRef.current = { amount: bidAmount, key: crypto.randomUUID() };
      }
      const bid = await placeBid(auctionId, bidAmount, pendingBidRef.current.key);
      pendingBidRef.current = null;
      setMyBid(bid);
      void loadAuction();
      message.success('Ставка принята');
      setBidAmount(null);
    } catch (err: unknown) {
      const status = (err as { response?: { status: number } })?.response?.status;
      if (status === 409) {
        pendingBidRef.current = null;
        message.warning('Конфликт: обновите карточку');
        void loadAuction();
      } else {
        // ПРОБЛЕМА: сетевой сбой не означает, что ставка не была сохранена.
        // РЕШЕНИЕ: запрашиваем фактическое состояние; ключ сохраняется для повтора.
        void loadAuction();
        const detail = (err as { response?: { data?: { amount_kopecks?: string[]; detail?: string } } })
          ?.response?.data;
        message.error(detail?.amount_kopecks?.[0] ?? detail?.detail ?? 'Ошибка ставки');
      }
    } finally {
      setBidding(false);
    }
  };

  const handleSubmit = async () => {
    if (!auction) return;
    try {
      const updated = await submitAuction(auction.id);
      setAuction(updated);
      message.success('Отправлено на модерацию');
    } catch {
      message.error('Ошибка отправки');
    }
  };

  const handleModerate = async (action: 'approve' | 'reject') => {
    if (!auction || !reason.trim()) return;
    setModerateLoading(true);
    try {
      const updated =
        action === 'approve'
          ? await approveAuction(auction.id, reason)
          : await rejectAuction(auction.id, reason);
      setAuction(updated);
      setReasonModal(null);
      setReason('');
      message.success(action === 'approve' ? 'Опубликовано' : 'Отклонено');
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail ?? 'Ошибка модерации');
    } finally {
      setModerateLoading(false);
    }
  };

  if (loading) return <Spin style={{ display: 'block', margin: '64px auto' }} />;
  if (!auction) return <Alert type="error" message="Аукцион не найден или недоступен" />;

  return (
    <div>
      <div className="rea-page-heading">
        <div><div className="rea-page-kicker">КАРТОЧКА АУКЦИОНА · №{auction.id}</div><h1>{auction.title}</h1><p>Все условия задачи, сроки и ваша ставка в одном месте.</p></div>
        <StatusBadge status={auction.status} />
      </div>
      <div className="rea-info-strip">
        📊 Ставки и имена исполнителей открыты всем вошедшим участникам. Побеждает минимальная ставка, а итоговая цена при двух и более предложениях — вторая минимальная.
        {' '}<a href={`${import.meta.env.BASE_URL}design-preview#ladder`} style={{ color: '#d87224', fontWeight: 750 }}>Посмотреть пример →</a>
      </div>
      <Space style={{ marginBottom: 16 }}>
        <Button onClick={() => navigate(-1)}>← Назад</Button>
        {canEdit && (
          <Button onClick={() => navigate(`/auctions/${auction.id}/edit`)}>Редактировать</Button>
        )}
        {canSubmit && (
          <Button type="primary" onClick={handleSubmit}>
            Отправить на модерацию
          </Button>
        )}
      </Space>

      <Row gutter={24}>
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <StatusBadge status={auction.status} />
                <Typography.Title level={4} style={{ margin: 0 }}>
                  {auction.title}
                </Typography.Title>
              </Space>
            }
          >
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Бюджет">{kopecksToRubles(auction.budget_kopecks)}</Descriptions.Item>
              <Descriptions.Item label="Торги до">
                {new Date(auction.ends_at).toLocaleString('ru-RU')}
              </Descriptions.Item>
              <Descriptions.Item label="Срок выполнения">
                {new Date(auction.due_at).toLocaleString('ru-RU')}
              </Descriptions.Item>
              {auction.moderation_reason && (
                <Descriptions.Item label="Причина модерации">
                  {auction.moderation_reason}
                </Descriptions.Item>
              )}
              {auction.winner_id != null && (
                <Descriptions.Item label="Победитель">
                  ID {auction.winner_id} — {kopecksToRubles(auction.payment_kopecks)}
                </Descriptions.Item>
              )}
              {auction.closed_at && (
                <Descriptions.Item label="Закрыт">
                  {new Date(auction.closed_at).toLocaleString('ru-RU')}
                </Descriptions.Item>
              )}
            </Descriptions>

            <Typography.Paragraph style={{ marginTop: 16, whiteSpace: 'pre-wrap' }}>
              {auction.description}
            </Typography.Paragraph>

            {serverClosed && (
              <Alert
                type="info"
                message="Ожидаем завершения сервером…"
                style={{ marginTop: 8 }}
              />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title={`Все ставки (${allBids.length})`} style={{ marginBottom: 16 }}>
            {allBids.length === 0 ? <Typography.Text type="secondary">Предложений пока нет.</Typography.Text> : allBids.map((bid, index) => (
              <div key={bid.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '12px 0', borderBottom: '1px solid #eef1f8' }}>
                <span>{index + 1}. {bid.bidder_username || `Участник #${bid.bidder_id}`}{bid.bidder_id === user?.id ? ' (вы)' : ''}</span>
                <Typography.Text strong>{kopecksToRubles(bid.amount_kopecks)}</Typography.Text>
              </div>
            ))}
            <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}>
              Предложения отсортированы от минимальной цены к максимальной. Обновление каждые пять секунд.
            </Typography.Paragraph>
          </Card>
          {myBid && (
            <Card title="Ваша ставка" style={{ marginBottom: 16 }}>
              <Typography.Text strong style={{ fontSize: 20 }}>
                {kopecksToRubles(myBid.amount_kopecks)}
              </Typography.Text>
              <br />
              <Typography.Text type="secondary">
                {new Date(myBid.created_at).toLocaleString('ru-RU')}
              </Typography.Text>
            </Card>
          )}

          {canBid && (
            <Card title="Сделать открытую ставку">
              <Alert type="info" showIcon style={{ marginBottom: 16 }} message="Ставку можно отправить только один раз" description="После отправки изменить сумму нельзя. Остальные участники увидят ваше имя и цену." />
              <Form layout="vertical">
                <Form.Item label="Сумма (не выше бюджета)">
                  <KopecksInput
                    value={bidAmount ?? undefined}
                    onChange={setBidAmount}
                    max={auction.budget_kopecks}
                    min={100}
                  />
                </Form.Item>
                <Button
                  type="primary"
                  block
                  loading={bidding}
                  disabled={!bidAmount}
                  onClick={handleBid}
                >
                  Поставить ставку
                </Button>
              </Form>
            </Card>
          )}

          {canModerate && (
            <Card title="Модерация">
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  block
                  onClick={() => setReasonModal('approve')}
                >
                  Опубликовать
                </Button>
                <Button danger block onClick={() => setReasonModal('reject')}>
                  Отклонить
                </Button>
              </Space>
            </Card>
          )}
        </Col>
      </Row>

      <Modal
        title={reasonModal === 'approve' ? 'Причина публикации' : 'Причина отклонения'}
        open={reasonModal !== null}
        onCancel={() => { setReasonModal(null); setReason(''); }}
        onOk={() => reasonModal && handleModerate(reasonModal)}
        confirmLoading={moderateLoading}
        okButtonProps={{ disabled: !reason.trim() }}
        okText={reasonModal === 'approve' ? 'Опубликовать' : 'Отклонить'}
        okType={reasonModal === 'approve' ? 'primary' : 'danger'}
      >
        <Form.Item label="Причина (обязательно)">
          <input
            className="ant-input"
            style={{ width: '100%', padding: '4px 11px' }}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Введите причину..."
          />
        </Form.Item>
      </Modal>
    </div>
  );
}

import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRightOutlined, CheckCircleFilled,
  InfoCircleOutlined, LockOutlined, SafetyCertificateOutlined,
  ThunderboltFilled,
} from '@ant-design/icons';
import './DesignPreviewPage.css';

type Role = 'owner' | 'bidder';
type Example = { name: string; amount: number; color: string };
const BASE_BUDGET = 10000;
const STARTING_BIDS: Example[] = [
  { name: 'Исполнитель А', amount: 7000, color: 'purple' },
  { name: 'Исполнитель Б', amount: 8500, color: 'sky' },
  { name: 'Исполнитель В', amount: 9500, color: 'mint' },
];

const rub = (value: number) => new Intl.NumberFormat('ru-RU').format(value) + ' ₽';

export function DesignPreviewPage() {
  const [role, setRole] = useState<Role>('bidder');
  const [bids, setBids] = useState<Example[]>(STARTING_BIDS);
  const [closed, setClosed] = useState(false);
  const [showExplanation, setShowExplanation] = useState(true);

  const ordered = useMemo(() => [...bids].sort((a, b) => a.amount - b.amount), [bids]);
  const winner = ordered[0];
  const price = ordered.length > 1 ? ordered[1].amount : BASE_BUDGET;
  const addBid = () => {
    // ПРОБЛЕМА: демонстрационная кнопка не должна случайно создавать настоящую ставку.
    // РЕШЕНИЕ: меняем только локальные данные макета; Django API здесь не вызывается.
    if (closed || bids.some(b => b.name === 'Вы (пример)')) return;
    setBids(current => [...current, { name: 'Вы (пример)', amount: 6500, color: 'amber' }]);
  };
  const reset = () => { setBids(STARTING_BIDS); setClosed(false); };

  return <div className="rea-design">
    <div className="rea-layout">
      <aside className="rea-sidebar">
        <Link to="/design-preview" className="rea-brand"><span className="rea-logo"><ThunderboltFilled /></span><span>rea<span className="rea-dot">.</span><small>AUCTION PLATFORM</small></span></Link>
        <div className="rea-nav-label">НАВИГАЦИЯ</div>
        <a className="rea-nav active" href="#intro">✦ &nbsp; Главная</a>
        <a className="rea-nav" href="#how">◫ &nbsp; Как это работает</a>
        <a className="rea-nav" href="#ladder">▥ &nbsp; Лестница ставок</a>
        <a className="rea-nav" href="#questions">? &nbsp; Частые вопросы</a>
        <div className="rea-sidebar-note"><strong>Всё просто!</strong><p>Сначала разберитесь в правилах на примере, а потом участвуйте в настоящих торгах.</p><a href="#ladder">Попробовать пример <ArrowRightOutlined /></a></div>
        <div className="rea-sidebar-footer">REA Auction · Дизайн-макет</div>
      </aside>
      <main className="rea-main">
        <header className="rea-header"><span>Обзор <b>/</b> Как работают торги</span><span className="rea-demo-tag"><span /> Интерактивная демонстрация</span></header>
        <div className="rea-content">
          {showExplanation && <div className="rea-notice"><InfoCircleOutlined /><span><strong>Это обучающий макет.</strong> Все суммы и участники ниже вымышленные. Никаких реальных заказов и ставок эта страница не создаёт.</span><button aria-label="Скрыть сообщение" onClick={() => setShowExplanation(false)}>×</button></div>}
          <section className="rea-intro" id="intro">
            <div className="rea-kicker">ПЛАТФОРМА ОБРАТНЫХ АУКЦИОНОВ</div>
            <h1>Найдите исполнителя.<br /><span>Без сложных торгов.</span></h1>
            <p>Вы рассказываете, что нужно сделать. Исполнители предлагают цену. Побеждает самое выгодное предложение — а итоговая сумма определяется по специальному правилу.</p>
            <div className="rea-intro-actions"><a className="rea-primary" href="#how">Как это работает <ArrowRightOutlined /></a><a className="rea-secondary" href="#ladder">Показать на примере</a></div>
            <div className="rea-hero-decoration" aria-hidden="true"><div className="rea-decoration-circle"><ThunderboltFilled /></div><span className="rea-floating one">✓ Прозрачные правила</span><span className="rea-floating two">↘ Предложения по цене</span></div>
          </section>
          <section className="rea-how" id="how">
            <div className="rea-section-header"><div><span className="rea-kicker">ВСЁ ПО ШАГАМ</span><h2>Как работает REA Auction?</h2><p>Выберите, кто вы, чтобы увидеть процесс со своей стороны.</p></div><div className="rea-role" role="group" aria-label="Выбор роли"><button className={role === 'owner' ? 'selected' : ''} aria-pressed={role === 'owner'} onClick={() => setRole('owner')}>Я заказчик</button><button className={role === 'bidder' ? 'selected' : ''} aria-pressed={role === 'bidder'} onClick={() => setRole('bidder')}>Я исполнитель</button></div></div>
            <div className="rea-steps">{(role === 'owner'
              ? [
                ['01','Опишите задачу','Укажите, что нужно сделать, максимальный бюджет и срок приёма предложений.'],
                ['02','Дождитесь публикации','Модератор проверит задачу. После одобрения исполнители смогут предлагать цены.'],
                ['03','Дождитесь окончания','Когда срок истечёт, система определит победителя по самой низкой ставке.'],
                ['04','Узнайте итог','Вы увидите победителя и итоговую расчётную сумму по правилу второй цены.'],
              ] : [
                ['01','Найдите задачу','Выберите подходящий заказ, внимательно прочитайте требования и максимальный бюджет.'],
                ['02','Предложите свою цену','Отправьте одну ставку. Её сумму увидят другие участники.'],
                ['03','Дождитесь завершения','Изменять ставку и делать вторую нельзя. Все предложения видны во время торгов.'],
                ['04','Посмотрите результат','Побеждает минимальная ставка. Итоговая цена зависит от следующей по величине ставки.'],
              ]).map(([n,title,desc]) => <div className="rea-step" key={n}><span className="rea-step-number">{n}</span><h3>{title}</h3><p>{desc}</p></div>)}</div>
          </section>
          <section className="rea-ladder-section" id="ladder">
            <div className="rea-section-header"><div><span className="rea-kicker">НА ПОНЯТНОМ ПРИМЕРЕ</span><h2>Как работает лестница ставок?</h2><p>Представим заказ с максимальным бюджетом 10 000 ₽.</p></div><span className="rea-illustration-label">Пример, не реальные торги</span></div>
            <div className="rea-ladder-grid">
              <div className="rea-ladder-card">
                <div className="rea-budget"><div><small>МАКСИМАЛЬНЫЙ БЮДЖЕТ ЗАКАЗЧИКА</small><strong>10 000 ₽</strong></div><span className="rea-budget-icon">₽</span></div>
                <div className="rea-card-top"><strong>Условная лестница предложений</strong><span>{bids.length} ставки</span></div>
                {/* ПРОБЛЕМА: горизонтальные шкалы выглядели как статистика, а не лестница.
                    РЕШЕНИЕ: настоящие ступени идут сверху вниз по возрастанию цены;
                    первая и вторая выделены цветом, чтобы правило второй цены было очевидно. */}
                <div className="rea-stair-guide">Чем <strong>ниже цена</strong>, тем выше место в рейтинге.</div>
                <div className="rea-vertical-stairs" aria-label="Учебная лестница ставок от самой низкой к высокой">
                  {ordered.map((bid, index) => (
                    <div className={`rea-stair-item ${index === 0 ? 'is-winning' : index === 1 ? 'is-pricing' : 'is-other'}`} key={bid.name}>
                      <span className="rea-stair-rank">{index + 1}</span>
                      <div className={`rea-stair-card ${bid.color}`}>
                        <span className="rea-stair-person">{bid.name}</span>
                        <strong>{rub(bid.amount)}</strong>
                        <span className="rea-stair-caption">{index === 0 ? 'Победитель — минимальная ставка' : index === 1 ? 'Вторая ставка — итоговая цена' : 'Другое предложение'}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="rea-privacy"><LockOutlined /><span><strong>Важно:</strong> эта лестница — только учебный пример. В реальном аукционе участники видят предложения и суммы во время торгов.</span></div>
                <div className="rea-demo-buttons"><button type="button" onClick={addBid} disabled={closed || bids.some(b => b.name === 'Вы (пример)')}>Добавить мою ставку 6 500 ₽</button><button type="button" onClick={() => setClosed(true)} disabled={closed}>Завершить пример</button><button type="button" className="rea-reset" onClick={reset}>Сначала</button></div>
              </div>
              <div className="rea-result">
                <div className="rea-result-tag"><CheckCircleFilled /> {closed ? 'УЧЕБНЫЙ ПРИМЕР ЗАВЕРШЁН' : 'ЕСЛИ ТОРГИ ЗАВЕРШАТСЯ СЕЙЧАС'}</div>
                <h3>Кто победит?</h3><p>Система выберет участника, предложившего <strong>самую низкую цену.</strong></p>
                <div className="rea-result-winner"><small>ПОБЕДИТЕЛЬ</small><strong>{winner.name}</strong><span>Его ставка: {rub(winner.amount)}</span></div>
                <div className="rea-result-divider" />
                <h3>Сколько составит итоговая цена?</h3><p>При двух и более ставках итог равен <strong>второй самой низкой</strong> ставке, а не ставке победителя.</p>
                <div className="rea-result-price"><small>ИТОГОВАЯ СУММА</small><strong>{rub(price)}</strong></div>
                <p className="rea-result-note"><InfoCircleOutlined /> Если участвует только один исполнитель, итоговая сумма равна максимальному бюджету заказчика. При одинаковых минимальных ставках выигрывает тот, кто отправил её раньше.</p>
              </div>
            </div>
            <div className="rea-takeaway"><SafetyCertificateOutlined /><div><strong>Почему победитель получает не обязательно ту сумму, которую указал?</strong><p>У нас используется механизм «второй цены». Ставка определяет, кто выигрывает. Сумма для победителя определяется следующим по выгодности предложением (а если ставка одна — бюджетом). Поэтому важно предлагать цену, за которую вы действительно готовы выполнить работу. Это правило показано заранее, чтобы оно не стало неожиданностью.</p></div></div>
          </section>
          <section className="rea-faq" id="questions"><div className="rea-section-header"><div><span className="rea-kicker">ОТВЕТЫ БЕЗ СЛОЖНЫХ ТЕРМИНОВ</span><h2>Частые вопросы</h2></div></div>
            <details><summary>Другие видят, сколько я предложил?</summary><p>Да. Имена участников и предложенные суммы видны всем вошедшим пользователям. Эта лестница — учебный пример.</p></details>
            <details><summary>Можно ли изменить свою цену?</summary><p>Нет. В текущей версии один исполнитель может отправить только одну неизменяемую ставку на каждый аукцион. Перед отправкой проверьте сумму.</p></details>
            <details><summary>Почему выигрывает 7 000 ₽, а итог составляет 8 500 ₽?</summary><p>7 000 ₽ — самая низкая ставка, поэтому её автор становится победителем. 8 500 ₽ — следующая по величине ставка, поэтому она определяет итоговую сумму по правилу второй цены.</p></details>
            <details><summary>Что будет, если заявку подаст только один исполнитель?</summary><p>При одной допустимой ставке итоговая сумма устанавливается на уровне максимального бюджета заказа. Поэтому заказчик должен заранее указывать бюджет, с которым согласен.</p></details>
            <details><summary>А если две минимальные ставки одинаковые?</summary><p>Побеждает тот, кто сделал такую ставку раньше. Если время совпало, система использует стабильный порядок записей.</p></details>
            <details><summary>Когда становится известен победитель?</summary><p>После окончания срока торгов и обработки закрытия сервером. В текущем проекте фоновый процесс проверяет просроченные торги примерно каждые 10 секунд.</p></details>
          </section>
          <section className="rea-endcap"><div><span className="rea-kicker">ТЕПЕРЬ ВСЁ ПОНЯТНО?</span><h2>Попробуйте найти подходящую задачу.</h2><p>Перейдите к настоящему каталогу. Участие возможно после входа в учётную запись.</p></div><Link to="/auctions" className="rea-primary">Перейти к аукционам <ArrowRightOutlined /></Link></section>
          <footer className="rea-footer"><span>REA Auction · Демонстрационный дизайн</span><span>React + TypeScript · Django REST API</span></footer>
        </div>
      </main>
    </div>
  </div>;
}

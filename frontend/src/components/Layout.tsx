import { Avatar, Button, Dropdown, Layout, Menu, Typography } from 'antd';
import { AppstoreOutlined, BellOutlined, BookOutlined, DashboardOutlined, LogoutOutlined, MenuOutlined, PlusOutlined, SafetyCertificateOutlined, CrownOutlined, UserOutlined } from '@ant-design/icons';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { logout } from '../api/auth';
import '../app-theme.css';

const { Sider, Content } = Layout;

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, setUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const pathname = location.pathname;
  const selectedKey = pathname.startsWith('/notifications') ? 'notifications'
    : pathname.startsWith('/profile') ? 'profile'
    : pathname.startsWith('/cabinet') ? 'cabinet'
    : pathname.startsWith('/admin') ? 'admin'
    : pathname.startsWith('/moderation') ? 'moderation'
    : 'catalog';

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      // ПРОБЛЕМА: при временной сетевой ошибке нельзя притворяться, что сервер завершил сессию.
      // РЕШЕНИЕ: остаёмся на странице, пользователь сможет попробовать ещё раз.
      return;
    }
    setUser(null);
    navigate('/login', { replace: true });
  };

  const items = [
    { key: 'catalog', icon: <AppstoreOutlined />, label: <Link to="/auctions">Каталог аукционов</Link> },
    { key: 'cabinet', icon: <DashboardOutlined />, label: <Link to="/cabinet">Мои заказы</Link> },
    { key: 'profile', icon: <UserOutlined />, label: <Link to="/profile">Мой профиль</Link> },
    { key: 'notifications', icon: <BellOutlined />, label: <Link to="/notifications">Уведомления</Link> },
    ...(user?.is_admin ? [{ key: 'admin', icon: <CrownOutlined />, label: <Link to="/admin">Администратор</Link> }] : []),
    ...(user?.can_moderate ? [{ key: 'moderation', icon: <SafetyCertificateOutlined />, label: <Link to="/moderation">Модерация</Link> }] : []),
  ];

  return (
    <Layout className="rea-app">
      <Sider width={248} theme="light" className="rea-app-sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
        <Link to="/auctions" className="rea-app-brand rea-app-brand-logo" aria-label="РЭУ — REA Auction"><img src={`${import.meta.env.BASE_URL}rea-logo.svg`} alt="120 лет РЭУ им. Г. В. Плеханова" /></Link>
        <div className="rea-app-section-label">РАБОЧЕЕ ПРОСТРАНСТВО</div>
        <nav className="rea-app-nav" aria-label="Основная навигация">
          <Menu mode="inline" selectedKeys={[selectedKey]} items={items} />
        </nav>
        <div className="rea-app-section-label" style={{ marginTop: 29 }}>ПОМОЩЬ</div>
        <nav className="rea-app-nav" aria-label="Помощь">
          <Menu mode="inline" selectable={false} items={[{ key: 'guide', icon: <BookOutlined />, label: <Link to="/design-preview">Как работают торги</Link> }]} />
        </nav>
        <div className="rea-app-sidebar-bottom" style={{ marginTop: 40 }}>
          <strong>Впервые на аукционе?</strong>
          <p>Узнайте, как предложить цену и почему победитель определяется по принципу второй цены.</p>
          <Link to="/design-preview">Посмотреть пример →</Link>
        </div>
        <div className="rea-app-user">
          <Avatar className="rea-app-avatar">{user?.username.slice(0, 2).toUpperCase()}</Avatar>
          <div><div className="rea-app-user-name">{user?.username}</div><div className="rea-app-user-role">{user?.is_admin ? 'Администратор' : user?.can_moderate ? 'Модератор' : 'Участник'}</div></div>
        </div>
      </Sider>
      <Layout style={{ background: 'transparent', minWidth: 0 }}>
        <header className="rea-app-topbar">
          <span className="rea-app-breadcrumb">Рабочее пространство / <strong>{selectedKey === 'notifications' ? 'Уведомления' : selectedKey === 'profile' ? 'Профиль' : selectedKey === 'cabinet' ? 'Мои заказы' : selectedKey === 'moderation' ? 'Модерация' : selectedKey === 'admin' ? 'Администратор' : 'Аукционы'}</strong></span>
          <div className="rea-app-top-actions">
            {/* ПРОБЛЕМА: на телефоне сайдбар скрыт, и профиль/кабинет были недоступны.
                РЕШЕНИЕ: мобильное выпадающее меню с теми же маршрутами. */}
            <Dropdown menu={{ items: [
              { key: 'catalog', label: <Link to="/auctions">Каталог аукционов</Link> },
              { key: 'cabinet', label: <Link to="/cabinet">Мои заказы</Link> },
              { key: 'profile', label: <Link to="/profile">Мой профиль</Link> },
              { key: 'notifications', label: <Link to="/notifications">Уведомления</Link> },
              { key: 'guide', label: <Link to="/design-preview">Как работают торги</Link> },
              ...(user?.is_admin ? [{ key: 'admin', label: <Link to="/admin">Администратор</Link> }] : []),
              ...(user?.can_moderate ? [{ key: 'moderation', label: <Link to="/moderation">Модерация</Link> }] : []),
            ] }}>
              <Button className="rea-mobile-menu" icon={<MenuOutlined />}>Меню</Button>
            </Dropdown>
            <Button icon={<BellOutlined />} onClick={() => navigate('/notifications')}>Уведомления</Button>
            <Button icon={<BookOutlined />} onClick={() => navigate('/design-preview')}>Правила</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/auctions/new')}>Новая задача</Button>
            <Button icon={<LogoutOutlined />} onClick={handleLogout}>Выйти</Button>
          </div>
        </header>
        {/* ПРОБЛЕМА: тёмное меню и узкий контент отличались от согласованного светлого SaaS-макета.
            РЕШЕНИЕ: единая оболочка с читаемой навигацией и адаптивной рабочей областью. */}
        <Content className="rea-app-content">{children}</Content>
        <footer style={{ textAlign: 'center', padding: '0 20px 24px', color: '#a2adc1', fontSize: 11 }}>
          <Typography.Text type="secondary">REA Auction · Ставки участников открыты</Typography.Text>
        </footer>
      </Layout>
    </Layout>
  );
}

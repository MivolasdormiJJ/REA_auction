import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider locale={ruRU} theme={{ token: { colorPrimary: "#e97521", colorInfo: "#2b7da8", colorLink: "#cf631a", colorSuccess: "#15866a", colorWarning: "#f29c38", borderRadius: 10, fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" }, components: { Menu: { itemSelectedBg: "#fff1e4", itemSelectedColor: "#bc5517" }, Segmented: { itemSelectedBg: "#ffe8d3" } } }}>
      <App />
    </ConfigProvider>
  </StrictMode>,
);

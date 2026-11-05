import { ThunderboltFilled } from '@ant-design/icons';
import { Link } from 'react-router-dom';

/**
 * Одна версия логотипа на всех публичных страницах.
 * Текст и векторная иконка не зависят от внешнего изображения, поэтому
 * браузер не покажет значок «битой картинки».
 */
export function BrandLogo({ variant = 'auth' }: { variant?: 'auth' | 'preview' }) {
  return (
    <Link
      to="/design-preview"
      aria-label="REA Auction — главная"
      className={variant === 'preview' ? 'rea-brand' : 'rea-auth-brand'}
    >
      <span className={variant === 'preview' ? 'rea-logo' : 'rea-auth-brand-icon'} aria-hidden="true">
        <ThunderboltFilled />
      </span>
      <span className="rea-brand-word"><span>rea<span className="rea-dot">.</span></span>
        <small>AUCTION PLATFORM</small>
      </span>
    </Link>
  );
}

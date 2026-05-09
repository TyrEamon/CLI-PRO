import type { CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { IconRefreshCw } from '@/components/ui/icons';
import { FEATURES } from '@/config/features';

type QuotaCardHeaderActionProps = {
  quotaStatus: string;
  canRefresh: boolean;
  onRefresh?: () => void;
};

type QuotaCachedTimeProps = {
  quotaStatus: string;
  cachedAt?: number;
};

const refreshButtonStyle: CSSProperties = {
  marginLeft: 'auto',
  padding: 4,
  background: 'transparent',
  border: '1px solid var(--border-color)',
  borderRadius: 4,
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'var(--text-secondary)',
  flexShrink: 0,
};

const cachedTimeStyle: CSSProperties = {
  marginTop: 8,
  paddingTop: 8,
  borderTop: '1px solid var(--border-color)',
  fontSize: 12,
  color: 'var(--text-secondary)',
  textAlign: 'right',
};

const formatCachedTime = (timestamp: number, t: (key: string, options?: Record<string, number>) => string): string => {
  const diff = Date.now() - timestamp;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return t('quota_management.just_now');
  if (minutes < 60) return t('quota_management.minutes_ago', { count: minutes });
  if (hours < 24) return t('quota_management.hours_ago', { count: hours });
  return t('quota_management.days_ago', { count: days });
};

export function QuotaCardHeaderAction({
  quotaStatus,
  canRefresh,
  onRefresh,
}: QuotaCardHeaderActionProps): ReactNode {
  const { t } = useTranslation();
  if (!FEATURES.QUOTA_SINGLE_REFRESH || quotaStatus !== 'success' || !onRefresh) return null;

  return (
    <button
      type="button"
      style={{ ...refreshButtonStyle, opacity: canRefresh ? 1 : 0.5, cursor: canRefresh ? 'pointer' : 'not-allowed' }}
      onClick={onRefresh}
      disabled={!canRefresh}
      title={t('quota_management.refresh_single')}
      aria-label={t('quota_management.refresh_single')}
    >
      <IconRefreshCw size={14} />
    </button>
  );
}

export function QuotaCachedTime({ quotaStatus, cachedAt }: QuotaCachedTimeProps): ReactNode {
  const { t } = useTranslation();
  if (!FEATURES.QUOTA_CACHE_TIMESTAMP || quotaStatus !== 'success' || !cachedAt) return null;

  return (
    <div style={cachedTimeStyle}>
      {t('quota_management.cached_at')}: {formatCachedTime(cachedAt, t)}
    </div>
  );
}

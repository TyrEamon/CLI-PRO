import { useCallback, useMemo, useState, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import {
  clearAppearanceSettings,
  DEFAULT_APPEARANCE_SETTINGS,
  getAppearanceBackgroundCssUrl,
  loadAppearanceSettings,
  saveAppearanceSettings,
  type AppearanceSettings,
} from '@/extensions/appearance/background';
import styles from './AppearanceSettingsCard.module.scss';

type RangeFieldProps = {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix: string;
  onChange: (value: number) => void;
};

function RangeField({ label, value, min, max, step, suffix, onChange }: RangeFieldProps) {
  return (
    <label className={styles.rangeField}>
      <span className={styles.rangeHeader}>
        <span>{label}</span>
        <strong>
          {value}
          {suffix}
        </strong>
      </span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  );
}

const previewBackgroundImage = (value: string): string | undefined => {
  const cssUrl = getAppearanceBackgroundCssUrl(value);
  return cssUrl === 'none' ? undefined : cssUrl;
};

export function AppearanceSettingsCard() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<AppearanceSettings>(() => loadAppearanceSettings());

  const updateSettings = useCallback((patch: Partial<AppearanceSettings>) => {
    setSettings((current) => saveAppearanceSettings({ ...current, ...patch }));
  }, []);

  const handleClear = useCallback(() => {
    setSettings(clearAppearanceSettings());
  }, []);

  const previewStyle = useMemo(
    () =>
      ({
        '--preview-opacity': settings.opacity,
        '--preview-overlay': settings.overlay,
        '--preview-blur': `${settings.blur}px`,
      }) as CSSProperties,
    [settings.blur, settings.opacity, settings.overlay]
  );

  return (
    <section className={styles.card} aria-labelledby="appearance-settings-title">
      <div className={styles.header}>
        <div>
          <div className={styles.eyebrow}>
            {t('appearance_settings.eyebrow', { defaultValue: 'Appearance' })}
          </div>
          <h2 id="appearance-settings-title" className={styles.title}>
            {t('appearance_settings.title', { defaultValue: '\u5916\u89c2\u8bbe\u7f6e' })}
          </h2>
          <p className={styles.description}>
            {t('appearance_settings.description', {
              defaultValue:
                '\u901a\u8fc7\u56fe\u7247\u94fe\u63a5\u8bbe\u7f6e\u767b\u5f55\u540e\u63a7\u5236\u53f0\u80cc\u666f\uff0c\u6548\u679c\u53ea\u4fdd\u5b58\u5728\u5f53\u524d\u6d4f\u89c8\u5668\u3002',
            })}
          </p>
        </div>
        <div className={styles.actions}>
          <Button
            variant={settings.enabled ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => updateSettings({ enabled: !settings.enabled })}
          >
            {settings.enabled
              ? t('appearance_settings.enabled', {
                  defaultValue: '\u80cc\u666f\u5df2\u542f\u7528',
                })
              : t('appearance_settings.enable', { defaultValue: '\u542f\u7528\u80cc\u666f' })}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleClear}>
            {t('appearance_settings.clear', { defaultValue: '\u6e05\u7a7a\u80cc\u666f' })}
          </Button>
        </div>
      </div>

      <div className={styles.urlGrid}>
        <Input
          label={t('appearance_settings.console_url', {
            defaultValue: '\u63a7\u5236\u53f0\u80cc\u666f URL',
          })}
          placeholder="https://example.com/dashboard-wallpaper.webp"
          value={settings.appBackgroundUrl}
          onChange={(event) =>
            updateSettings({ appBackgroundUrl: event.target.value, enabled: true })
          }
          hint={t('appearance_settings.console_hint', {
            defaultValue:
              '\u4f5c\u7528\u4e8e\u767b\u5f55\u540e\u7684\u7ba1\u7406\u63a7\u5236\u53f0\u3002',
          })}
        />
      </div>

      <div className={styles.tuningGrid}>
        <RangeField
          label={t('appearance_settings.opacity', {
            defaultValue: '\u80cc\u666f\u900f\u660e\u5ea6',
          })}
          min={0}
          max={100}
          step={5}
          suffix="%"
          value={Math.round(settings.opacity * 100)}
          onChange={(value) => updateSettings({ opacity: value / 100 })}
        />
        <RangeField
          label={t('appearance_settings.overlay', {
            defaultValue: '\u906e\u7f69\u5f3a\u5ea6',
          })}
          min={0}
          max={90}
          step={5}
          suffix="%"
          value={Math.round(settings.overlay * 100)}
          onChange={(value) => updateSettings({ overlay: value / 100 })}
        />
        <RangeField
          label={t('appearance_settings.blur', {
            defaultValue: '\u80cc\u666f\u6a21\u7cca',
          })}
          min={0}
          max={24}
          step={1}
          suffix="px"
          value={Math.round(settings.blur)}
          onChange={(value) => updateSettings({ blur: value })}
        />
      </div>

      <div className={styles.previewGrid} style={previewStyle}>
        <div
          className={styles.previewTile}
          style={{ backgroundImage: previewBackgroundImage(settings.appBackgroundUrl) }}
        >
          <span>
            {t('appearance_settings.console_preview', {
              defaultValue: '\u63a7\u5236\u53f0\u9884\u89c8',
            })}
          </span>
        </div>
      </div>

      <p className={styles.footnote}>
        {t('appearance_settings.footnote', {
          defaultValue: `\u7559\u7a7a\u7b49\u4e8e\u5173\u95ed\uff1b\u9876\u90e8\u4e3b\u9898\u83dc\u5355\u91cc\u7684\u201c\u81ea\u5b9a\u4e49\u80cc\u666f\u201d\u53ef\u4ee5\u5feb\u901f\u542f\u7528/\u6682\u505c\u3002\u63a8\u8350\u4f7f\u7528 webp/jpg/png \u76f4\u94fe\uff1b\u9ed8\u8ba4\u900f\u660e\u5ea6 ${Math.round(
            DEFAULT_APPEARANCE_SETTINGS.opacity * 100
          )}%\u3002`,
        })}
      </p>
    </section>
  );
}

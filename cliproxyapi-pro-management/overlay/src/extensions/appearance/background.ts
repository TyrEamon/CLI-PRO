export type AppearanceSettings = {
  enabled: boolean;
  appBackgroundUrl: string;
  opacity: number;
  overlay: number;
  blur: number;
};

export const APPEARANCE_STORAGE_KEY = 'cliproxyapi-pro:appearance:v1';
export const APPEARANCE_CHANGE_EVENT = 'cliproxyapi-pro:appearance-change';

export const DEFAULT_APPEARANCE_SETTINGS: AppearanceSettings = {
  enabled: false,
  appBackgroundUrl: '',
  opacity: 0.52,
  overlay: 0.5,
  blur: 0,
};

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const normalizeNumber = (value: unknown, fallback: number, min: number, max: number): number => {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return fallback;
  }
  return clamp(numericValue, min, max);
};

const normalizeUrl = (value: unknown): string => {
  if (typeof value !== 'string') {
    return '';
  }

  return value.trim();
};

const getRenderableUrl = (value: string): string => {
  try {
    const parsed = new URL(value);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:' || parsed.protocol === 'blob:') {
      return value;
    }
  } catch {
    // Fall through to the data URL check below.
  }

  if (/^data:image\/(?:avif|gif|jpe?g|png|webp);base64,[A-Za-z0-9+/=]+$/i.test(value)) {
    return value;
  }

  return '';
};

export const getAppearanceBackgroundCssUrl = (value: string): string => {
  const renderableUrl = getRenderableUrl(value);
  if (!renderableUrl) {
    return 'none';
  }

  return `url("${renderableUrl.replace(/["\\\n\r\f]/g, '\\$&')}")`;
};

export const normalizeAppearanceSettings = (value: unknown): AppearanceSettings => {
  const source = value && typeof value === 'object' ? (value as Partial<AppearanceSettings>) : {};

  return {
    enabled: Boolean(source.enabled),
    appBackgroundUrl: normalizeUrl(source.appBackgroundUrl),
    opacity: normalizeNumber(source.opacity, DEFAULT_APPEARANCE_SETTINGS.opacity, 0, 1),
    overlay: normalizeNumber(source.overlay, DEFAULT_APPEARANCE_SETTINGS.overlay, 0, 0.9),
    blur: normalizeNumber(source.blur, DEFAULT_APPEARANCE_SETTINGS.blur, 0, 24),
  };
};

const emitAppearanceChange = (settings: AppearanceSettings): void => {
  if (typeof window === 'undefined') {
    return;
  }
  window.dispatchEvent(new CustomEvent(APPEARANCE_CHANGE_EVENT, { detail: settings }));
};

export const loadAppearanceSettings = (): AppearanceSettings => {
  if (typeof window === 'undefined') {
    return DEFAULT_APPEARANCE_SETTINGS;
  }

  try {
    const raw = window.localStorage.getItem(APPEARANCE_STORAGE_KEY);
    if (!raw) {
      return DEFAULT_APPEARANCE_SETTINGS;
    }
    return normalizeAppearanceSettings(JSON.parse(raw));
  } catch {
    return DEFAULT_APPEARANCE_SETTINGS;
  }
};

export const saveAppearanceSettings = (settings: AppearanceSettings): AppearanceSettings => {
  const normalized = normalizeAppearanceSettings(settings);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(APPEARANCE_STORAGE_KEY, JSON.stringify(normalized));
  }
  applyAppearanceSettings(normalized);
  emitAppearanceChange(normalized);
  return normalized;
};

export const clearAppearanceSettings = (): AppearanceSettings => {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(APPEARANCE_STORAGE_KEY);
  }
  applyAppearanceSettings(DEFAULT_APPEARANCE_SETTINGS);
  emitAppearanceChange(DEFAULT_APPEARANCE_SETTINGS);
  return DEFAULT_APPEARANCE_SETTINGS;
};

export const applyAppearanceSettings = (settings: AppearanceSettings): void => {
  if (typeof document === 'undefined') {
    return;
  }

  const normalized = normalizeAppearanceSettings(settings);
  const root = document.documentElement;

  root.style.setProperty(
    '--pro-app-wallpaper-image',
    getAppearanceBackgroundCssUrl(normalized.appBackgroundUrl)
  );
  root.style.setProperty('--pro-wallpaper-opacity', normalized.opacity.toFixed(2));
  root.style.setProperty('--pro-wallpaper-overlay', normalized.overlay.toFixed(2));
  root.style.setProperty('--pro-wallpaper-blur', `${Math.round(normalized.blur)}px`);
  root.classList.toggle(
    'pro-app-wallpaper-enabled',
    normalized.enabled && Boolean(getRenderableUrl(normalized.appBackgroundUrl))
  );
  root.classList.toggle('pro-custom-wallpaper-enabled', normalized.enabled);
};

if (typeof window !== 'undefined') {
  applyAppearanceSettings(loadAppearanceSettings());

  window.addEventListener('storage', (event) => {
    if (event.key !== APPEARANCE_STORAGE_KEY) {
      return;
    }
    const settings = loadAppearanceSettings();
    applyAppearanceSettings(settings);
    emitAppearanceChange(settings);
  });
}

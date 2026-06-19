#!/usr/bin/env python3
import json
import re
import shutil
import sys
from pathlib import Path

CUSTOMIZATION_DIR = Path(__file__).resolve().parent
OVERLAY_DIR = CUSTOMIZATION_DIR / 'overlay'
LOCALES_FILE = CUSTOMIZATION_DIR / 'monitoring-locales.json'

QUOTA_LOCALE_KEYS = {
    'en.json': {
        'cached_at': 'Updated',
        'just_now': 'Just now',
        'minutes_ago': '{{count}} minute ago',
        'minutes_ago_plural': '{{count}} minutes ago',
        'hours_ago': '{{count}} hour ago',
        'hours_ago_plural': '{{count}} hours ago',
        'days_ago': '{{count}} day ago',
        'days_ago_plural': '{{count}} days ago',
    },
    'ru.json': {
        'cached_at': 'Обновлено',
        'just_now': 'Только что',
        'minutes_ago': '{{count}} минуту назад',
        'minutes_ago_plural': '{{count}} минут назад',
        'hours_ago': '{{count}} час назад',
        'hours_ago_plural': '{{count}} часов назад',
        'days_ago': '{{count}} день назад',
        'days_ago_plural': '{{count}} дней назад',
    },
    'zh-CN.json': {
        'cached_at': '更新于',
        'just_now': '刚刚',
        'minutes_ago': '{{count}} 分钟前',
        'hours_ago': '{{count}} 小时前',
        'days_ago': '{{count}} 天前',
    },
    'zh-TW.json': {
        'cached_at': '更新於',
        'just_now': '剛剛',
        'minutes_ago': '{{count}} 分鐘前',
        'hours_ago': '{{count}} 小時前',
        'days_ago': '{{count}} 天前',
    },
}

GEMINI_CLI_LOCALE_KEYS = {
    'en.json': {
        'title': 'Gemini CLI Quota',
        'empty_title': 'No Gemini CLI Auth Files',
        'empty_desc': 'Upload a Gemini CLI credential to view remaining quota.',
        'idle': 'Click here to refresh quota',
        'loading': 'Loading quota...',
        'load_failed': 'Failed to load quota: {{message}}',
        'missing_auth_index': 'Auth file missing auth_index',
        'missing_project_id': 'Gemini CLI credential missing project ID',
        'empty_buckets': 'No quota data available',
        'refresh_button': 'Refresh Quota',
        'fetch_all': 'Fetch All',
        'remaining_amount': 'Remaining {{count}}',
        'tier_label': 'Tier',
        'tier_free': 'Free',
        'tier_legacy': 'Legacy',
        'tier_standard': 'Standard',
        'tier_pro': 'Pro',
        'tier_ultra': 'Ultra',
        'credit_label': 'Google One AI Credits',
        'credit_amount': '{{count}} credits',
    },
    'ru.json': {
        'title': 'Квота Gemini CLI',
        'empty_title': 'Файлы авторизации Gemini CLI отсутствуют',
        'empty_desc': 'Загрузите учётные данные Gemini CLI, чтобы увидеть оставшуюся квоту.',
        'idle': 'Не загружено. Нажмите "Обновить квоту".',
        'loading': 'Загрузка квоты...',
        'load_failed': 'Не удалось загрузить квоту: {{message}}',
        'missing_auth_index': 'В файле авторизации отсутствует auth_index',
        'missing_project_id': 'В учётных данных Gemini CLI отсутствует идентификатор проекта',
        'empty_buckets': 'Данные по квоте отсутствуют',
        'refresh_button': 'Обновить квоту',
        'fetch_all': 'Получить все',
        'remaining_amount': 'Осталось {{count}}',
        'tier_label': 'Уровень',
        'tier_free': 'Бесплатный',
        'tier_legacy': 'Устаревший',
        'tier_standard': 'Стандартный',
        'tier_pro': 'Pro',
        'tier_ultra': 'Ultra',
        'credit_label': 'Google One AI кредиты',
        'credit_amount': '{{count}} кредитов',
    },
    'zh-CN.json': {
        'title': 'Gemini CLI 额度',
        'empty_title': '暂无 Gemini CLI 认证',
        'empty_desc': '上传 Gemini CLI 认证文件后即可查看额度。',
        'idle': '点击此处刷新额度',
        'loading': '正在加载额度...',
        'load_failed': '额度获取失败：{{message}}',
        'missing_auth_index': '认证文件缺少 auth_index',
        'missing_project_id': 'Gemini CLI 凭证缺少 Project ID',
        'empty_buckets': '暂无额度数据',
        'refresh_button': '刷新额度',
        'fetch_all': '获取全部',
        'remaining_amount': '剩余 {{count}}',
        'tier_label': '层级',
        'tier_free': '免费版',
        'tier_legacy': '旧版',
        'tier_standard': '标准版',
        'tier_pro': 'Pro',
        'tier_ultra': 'Ultra',
        'credit_label': 'Google One AI 积分',
        'credit_amount': '{{count}} 积分',
    },
    'zh-TW.json': {
        'title': 'Gemini CLI 配額',
        'empty_title': '暫無 Gemini CLI 驗證',
        'empty_desc': '上傳 Gemini CLI 驗證檔案後即可查看配額。',
        'idle': '點擊此處重新整理配額',
        'loading': '正在載入配額...',
        'load_failed': '配額取得失敗：{{message}}',
        'missing_auth_index': '驗證檔案缺少 auth_index',
        'missing_project_id': 'Gemini CLI 憑證缺少 Project ID',
        'empty_buckets': '暫無配額資料',
        'refresh_button': '重新整理配額',
        'fetch_all': '取得全部',
        'remaining_amount': '剩餘 {{count}}',
        'tier_label': '層級',
        'tier_free': '免費版',
        'tier_legacy': '舊版',
        'tier_standard': '標準版',
        'tier_pro': 'Pro',
        'tier_ultra': 'Ultra',
        'credit_label': 'Google One AI 點數',
        'credit_amount': '{{count}} 點數',
    },
}


_writes = {}


def read(path: Path) -> str:
    if path in _writes:
        return _writes[path]
    return path.read_text()


def write(path: Path, text: str) -> None:
    _writes[path] = text


def flush_writes() -> None:
    for path, text in _writes.items():
        path.write_text(text)


def replace_once(path: Path, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f'Pattern not found in {path}: {old[:120]!r}')
    write(path, text.replace(old, new, 1))


def replace_all(path: Path, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        return
    write(path, text.replace(old, new))


def replace_once_in_quota_config(path: Path, store_setter: str, old: str, new: str) -> None:
    text = read(path)
    marker = f"  storeSetter: '{store_setter}',"
    marker_start = text.find(marker)
    if marker_start == -1:
        raise RuntimeError(f'Pattern not found in {path}: {marker!r}')

    success_start = text.find('  buildSuccessState:', marker_start)
    error_start = text.find('  buildErrorState:', success_start)
    if success_start == -1 or error_start == -1:
        raise RuntimeError(f'Pattern not found in {path}: buildSuccessState block for {store_setter}')

    block = text[success_start:error_start]
    if new in block:
        return
    if old not in block:
        raise RuntimeError(f'Pattern not found in {path}: {old[:120]!r}')

    updated = block.replace(old, new, 1)
    write(path, f'{text[:success_start]}{updated}{text[error_start:]}')


def insert_once(path: Path, marker: str, insertion: str, present: str) -> None:
    text = read(path)
    if present in text:
        return
    if marker not in text:
        raise RuntimeError(f'Pattern not found in {path}: {marker[:120]!r}')
    write(path, text.replace(marker, insertion, 1))


def insert_before_once(path: Path, marker: str, insertion: str, present: str) -> None:
    text = read(path)
    if present in text:
        return
    if marker not in text:
        raise RuntimeError(f'Pattern not found in {path}: {marker[:120]!r}')
    write(path, text.replace(marker, insertion + marker, 1))


def ensure_import_members(path: Path, module: str, members: list[str], type_import: bool = False) -> None:
    text = read(path)
    import_prefix = 'import type' if type_import else 'import'
    pattern = re.compile(
        rf"{re.escape(import_prefix)}\s+\{{(?P<body>.*?)\}}\s+from\s+['\"]{re.escape(module)}['\"];",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise RuntimeError(f'Import not found in {path}: {import_prefix} {{ ... }} from {module!r}')

    body = match.group('body')
    existing = {
        item.strip().rstrip(',')
        for item in body.replace('\n', ' ').split(',')
        if item.strip()
    }
    missing = [member for member in members if member not in existing]
    if not missing:
        return

    body_lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    if body_lines:
        if not body_lines[-1].endswith(','):
            body_lines[-1] += ','
        body_lines.extend(f'  {member},' for member in missing)
        new_body = '\n' + '\n'.join(body_lines) + '\n'
    else:
        new_body = '\n' + '\n'.join(f'  {member},' for member in missing) + '\n'

    write(path, text[:match.start('body')] + new_body + text[match.end('body'):])


def ensure_named_import(path: Path, import_statement: str, after: str, present: str) -> None:
    text = read(path)
    if present in text:
        return
    if after not in text:
        raise RuntimeError(f'Pattern not found in {path}: {after[:120]!r}')
    write(path, text.replace(after, after + import_statement, 1))


def ensure_interface_field(path: Path, interface_name: str, field: str, after_field: str = 'errorStatus?: number;', required: bool = True) -> None:
    text = read(path)
    match = re.search(rf'export\s+interface\s+{re.escape(interface_name)}\b[^\{{]*\{{', text)
    if not match:
        if not required:
            return
        raise RuntimeError(f'Interface not found in {path}: {interface_name}')

    brace_start = match.end() - 1
    depth = 0
    for index in range(brace_start, len(text)):
        char = text[index]
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                block = text[match.start():index + 1]
                field_line = field.strip()
                if re.search(rf'^\s*{re.escape(field_line)}\s*$', block, re.MULTILINE):
                    return
                after_match = re.search(rf'^(\s*){re.escape(after_field)}\s*$', block, re.MULTILINE)
                if after_match:
                    insert_at = match.start() + after_match.end()
                    write(path, text[:insert_at] + f'\n{after_match.group(1)}{field_line}' + text[insert_at:])
                    return
                write(path, text[:index] + f'  {field_line}\n' + text[index:])
                return

    raise RuntimeError(f'Interface end not found in {path}: {interface_name}')


GEMINI_CLI_API_TYPES = """export interface GeminiCliQuotaBucket {
  modelId?: string;
  model_id?: string;
  tokenType?: string;
  token_type?: string;
  remainingFraction?: number | string;
  remaining_fraction?: number | string;
  remainingAmount?: number | string;
  remaining_amount?: number | string;
  resetTime?: string;
  reset_time?: string;
}

export interface GeminiCliQuotaPayload {
  buckets?: GeminiCliQuotaBucket[];
}

export interface GeminiCliCredits {
  creditType?: string;
  credit_type?: string;
  creditAmount?: string | number;
  credit_amount?: string | number;
}

export interface GeminiCliUserTier {
  id?: string;
  name?: string;
  description?: string;
  availableCredits?: GeminiCliCredits[];
  available_credits?: GeminiCliCredits[];
}

export interface GeminiCliCodeAssistPayload {
  currentTier?: GeminiCliUserTier | null;
  current_tier?: GeminiCliUserTier | null;
  paidTier?: GeminiCliUserTier | null;
  paid_tier?: GeminiCliUserTier | null;
}

"""


GEMINI_CLI_STATE_TYPES = """export interface GeminiCliQuotaGroupDefinition {
  id: string;
  label: string;
  preferredModelId?: string;
  modelIds: string[];
}

export interface GeminiCliParsedBucket {
  modelId: string;
  tokenType: string | null;
  remainingFraction: number | null;
  remainingAmount: number | null;
  resetTime: string | undefined;
}

export interface GeminiCliQuotaBucketState {
  id: string;
  label: string;
  remainingFraction: number | null;
  remainingAmount: number | null;
  resetTime: string | undefined;
  tokenType: string | null;
  modelIds?: string[];
}

export interface GeminiCliQuotaState {
  status: 'idle' | 'loading' | 'success' | 'error';
  buckets: GeminiCliQuotaBucketState[];
  tierLabel?: string | null;
  tierId?: string | null;
  creditBalance?: number | null;
  error?: string;
  errorStatus?: number;
  cachedAt?: number;
}

"""


GEMINI_CLI_CONSTANTS = """// Gemini CLI API configuration
export const GEMINI_CLI_QUOTA_URL =
  'https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota';

export const GEMINI_CLI_CODE_ASSIST_URL =
  'https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist';

export const GEMINI_CLI_REQUEST_HEADERS = {
  Authorization: 'Bearer $TOKEN$',
  'Content-Type': 'application/json',
};

export const GEMINI_CLI_QUOTA_GROUPS: GeminiCliQuotaGroupDefinition[] = [
  {
    id: 'gemini-flash-lite-series',
    label: 'Gemini Flash Lite Series',
    preferredModelId: 'gemini-2.5-flash-lite',
    modelIds: ['gemini-2.5-flash-lite'],
  },
  {
    id: 'gemini-flash-series',
    label: 'Gemini Flash Series',
    preferredModelId: 'gemini-3-flash-preview',
    modelIds: ['gemini-3-flash-preview', 'gemini-2.5-flash'],
  },
  {
    id: 'gemini-pro-series',
    label: 'Gemini Pro Series',
    preferredModelId: 'gemini-3.1-pro-preview',
    modelIds: ['gemini-3.1-pro-preview', 'gemini-3-pro-preview', 'gemini-2.5-pro'],
  },
];

export const GEMINI_CLI_GROUP_ORDER = new Map(
  GEMINI_CLI_QUOTA_GROUPS.map((group, index) => [group.id, index] as const)
);

export const GEMINI_CLI_GROUP_LOOKUP = new Map(
  GEMINI_CLI_QUOTA_GROUPS.flatMap((group) =>
    group.modelIds.map((modelId) => [modelId, group] as const)
  )
);

export const GEMINI_CLI_IGNORED_MODEL_PREFIXES = ['gemini-2.0-flash'];

"""


GEMINI_CLI_PARSERS = """const GEMINI_CLI_MODEL_SUFFIX = '_vertex';

export function normalizeGeminiCliModelId(value: unknown): string | null {
  const modelId = normalizeStringValue(value);
  if (!modelId) return null;
  if (modelId.endsWith(GEMINI_CLI_MODEL_SUFFIX)) {
    return modelId.slice(0, -GEMINI_CLI_MODEL_SUFFIX.length);
  }
  return modelId;
}

"""


GEMINI_CLI_PARSE_PAYLOADS = """export function parseGeminiCliQuotaPayload(payload: unknown): GeminiCliQuotaPayload | null {
  if (payload === undefined || payload === null) return null;
  if (typeof payload === 'string') {
    const trimmed = payload.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed) as GeminiCliQuotaPayload;
    } catch {
      return null;
    }
  }
  if (typeof payload === 'object') {
    return payload as GeminiCliQuotaPayload;
  }
  return null;
}

export function parseGeminiCliCodeAssistPayload(
  payload: unknown
): GeminiCliCodeAssistPayload | null {
  if (payload === undefined || payload === null) return null;
  if (typeof payload === 'string') {
    const trimmed = payload.trim();
    if (!trimmed) return null;
    try {
      return JSON.parse(trimmed) as GeminiCliCodeAssistPayload;
    } catch {
      return null;
    }
  }
  if (typeof payload === 'object') {
    return payload as GeminiCliCodeAssistPayload;
  }
  return null;
}

"""


GEMINI_CLI_BUILDERS = """export function pickEarlierResetTime(current?: string, next?: string): string | undefined {
  if (!current) return next;
  if (!next) return current;
  const currentTime = new Date(current).getTime();
  const nextTime = new Date(next).getTime();
  if (Number.isNaN(currentTime)) return next;
  if (Number.isNaN(nextTime)) return current;
  return currentTime <= nextTime ? current : next;
}

export function minNullableNumber(current: number | null, next: number | null): number | null {
  if (current === null) return next;
  if (next === null) return current;
  return Math.min(current, next);
}

export function buildGeminiCliQuotaBuckets(
  buckets: GeminiCliParsedBucket[]
): GeminiCliQuotaBucketState[] {
  if (buckets.length === 0) return [];

  type GeminiCliQuotaBucketGroup = {
    id: string;
    label: string;
    tokenType: string | null;
    modelIds: string[];
    preferredModelId?: string;
    preferredBucket?: GeminiCliParsedBucket;
    fallbackRemainingFraction: number | null;
    fallbackRemainingAmount: number | null;
    fallbackResetTime: string | undefined;
  };

  const grouped = new Map<string, GeminiCliQuotaBucketGroup>();

  buckets.forEach((bucket) => {
    if (isIgnoredGeminiCliModel(bucket.modelId)) return;
    const group = GEMINI_CLI_GROUP_LOOKUP.get(bucket.modelId);
    const groupId = group?.id ?? bucket.modelId;
    const label = group?.label ?? bucket.modelId;
    const tokenKey = bucket.tokenType ?? '';
    const mapKey = `${groupId}::${tokenKey}`;
    const existing = grouped.get(mapKey);

    if (!existing) {
      const preferredModelId = group?.preferredModelId;
      const preferredBucket =
        preferredModelId && bucket.modelId === preferredModelId ? bucket : undefined;
      grouped.set(mapKey, {
        id: `${groupId}${tokenKey ? `-${tokenKey}` : ''}`,
        label,
        tokenType: bucket.tokenType,
        modelIds: [bucket.modelId],
        preferredModelId,
        preferredBucket,
        fallbackRemainingFraction: bucket.remainingFraction,
        fallbackRemainingAmount: bucket.remainingAmount,
        fallbackResetTime: bucket.resetTime,
      });
      return;
    }

    existing.fallbackRemainingFraction = minNullableNumber(
      existing.fallbackRemainingFraction,
      bucket.remainingFraction
    );
    existing.fallbackRemainingAmount = minNullableNumber(
      existing.fallbackRemainingAmount,
      bucket.remainingAmount
    );
    existing.fallbackResetTime = pickEarlierResetTime(existing.fallbackResetTime, bucket.resetTime);
    existing.modelIds.push(bucket.modelId);

    if (existing.preferredModelId && bucket.modelId === existing.preferredModelId) {
      existing.preferredBucket = bucket;
    }
  });

  const toGroupOrder = (bucket: GeminiCliQuotaBucketGroup): number => {
    const tokenSuffix = bucket.tokenType ? `-${bucket.tokenType}` : '';
    const groupId = bucket.id.endsWith(tokenSuffix)
      ? bucket.id.slice(0, bucket.id.length - tokenSuffix.length)
      : bucket.id;
    return GEMINI_CLI_GROUP_ORDER.get(groupId) ?? Number.MAX_SAFE_INTEGER;
  };

  return Array.from(grouped.values())
    .sort((a, b) => {
      const orderDiff = toGroupOrder(a) - toGroupOrder(b);
      if (orderDiff !== 0) return orderDiff;
      const tokenTypeA = a.tokenType ?? '';
      const tokenTypeB = b.tokenType ?? '';
      return tokenTypeA.localeCompare(tokenTypeB);
    })
    .map((bucket) => {
      const uniqueModelIds = Array.from(new Set(bucket.modelIds));
      const preferred = bucket.preferredBucket;
      const remainingFraction = preferred
        ? preferred.remainingFraction
        : bucket.fallbackRemainingFraction;
      const remainingAmount = preferred ? preferred.remainingAmount : bucket.fallbackRemainingAmount;
      const resetTime = preferred ? preferred.resetTime : bucket.fallbackResetTime;
      return {
        id: bucket.id,
        label: bucket.label,
        remainingFraction,
        remainingAmount,
        resetTime,
        tokenType: bucket.tokenType,
        modelIds: uniqueModelIds,
      };
    });
}

"""


def copy_overlay(target: Path) -> None:
    for src in OVERLAY_DIR.rglob('*'):
        rel = src.relative_to(OVERLAY_DIR)
        dst = target / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def patch_routes(target: Path) -> None:
    path = target / 'src/router/MainRoutes.tsx'
    replace_once(
        path,
        "import { QuotaPage } from '@/pages/QuotaPage';\n",
        "import { QuotaPage } from '@/pages/QuotaPage';\nimport { MonitoringCenterPage } from '@/pages/MonitoringCenterPage';\nimport { AccountInspectionPage } from '@/pages/AccountInspectionPage';\n",
    )
    replace_once(
        path,
        "  { path: '/quota', element: <QuotaPage /> },\n",
        "  { path: '/quota', element: <QuotaPage /> },\n  { path: '/monitoring', element: <MonitoringCenterPage /> },\n  { path: '/account-inspection', element: <AccountInspectionPage /> },\n",
    )


def patch_layout(target: Path) -> None:
    path = target / 'src/components/layout/MainLayout.tsx'
    insert_once(
        path,
        "import {\n  IconSidebar",
        "import { QuotaPersistenceBootstrap } from '@/extensions/quota/QuotaPersistenceBootstrap';\nimport {\n  IconSidebar",
        "QuotaPersistenceBootstrap",
    )
    insert_once(
        path,
        "  IconSidebarProviders,\n",
        "  IconSidebarMonitor,\n  IconSidebarProviders,\n",
        "  IconSidebarMonitor,\n",
    )
    replace_once(
        path,
        "  oauth: <IconSidebarOauth size={18} />,\n  quota: <IconSidebarQuota size={18} />,\n",
        "  oauth: <IconSidebarOauth size={18} />,\n  quota: <IconSidebarQuota size={18} />,\n  monitoring: <IconSidebarMonitor size={18} />,\n",
    )
    text = read(path)
    if "path: '/monitoring'" not in text:
        flat_quota_item = "    { path: '/quota', label: t('nav.quota_management'), icon: sidebarIcons.quota },\n"
        grouped_quota_item = (
            "        {\n"
            "          path: '/quota',\n"
            "          labelKey: 'nav.quota_management',\n"
            "          metaKey: 'nav_meta.quota_management',\n"
            "          icon: sidebarIcons.quota,\n"
            "        },\n"
        )
        if flat_quota_item in text:
            write(
                path,
                text.replace(
                    flat_quota_item,
                    flat_quota_item
                    + "    { path: '/monitoring', label: t('nav.monitoring_center'), icon: sidebarIcons.monitoring },\n"
                    + "    { path: '/account-inspection', label: t('nav.account_inspection'), icon: sidebarIcons.monitoring },\n",
                    1,
                ),
            )
        elif grouped_quota_item in text:
            write(
                path,
                text.replace(
                    grouped_quota_item,
                    grouped_quota_item
                    + "        {\n"
                    + "          path: '/monitoring',\n"
                    + "          labelKey: 'nav.monitoring_center',\n"
                    + "          metaKey: 'nav_meta.monitoring_center',\n"
                    + "          icon: sidebarIcons.monitoring,\n"
                    + "        },\n"
                    + "        {\n"
                    + "          path: '/account-inspection',\n"
                    + "          labelKey: 'nav.account_inspection',\n"
                    + "          metaKey: 'nav_meta.account_inspection',\n"
                    + "          icon: sidebarIcons.monitoring,\n"
                    + "        },\n",
                    1,
                ),
            )
        else:
            raise RuntimeError(f'Pattern not found in {path}: quota navigation item')
    replace_once(
        path,
        "            <PageTransition\n",
        "            <QuotaPersistenceBootstrap />\n            <PageTransition\n",
    )

def patch_icons(target: Path) -> None:
    path = target / 'src/components/ui/icons.tsx'
    insert_once(
        path,
        "export function IconSidebarLogs({ size = 20, ...props }: IconProps) {\n",
        "export function IconSidebarMonitor({ size = 20, ...props }: IconProps) {\n  return (\n    <svg {...sidebarSvgProps} width={size} height={size} {...props}>\n      <path d=\"M3 12h3l2.2-4.5 4.2 9 2.4-5h6.2\" />\n      <path d=\"M4 19h16\" />\n      <path d=\"M4 5h16\" fill=\"currentColor\" fillOpacity=\"0.08\" />\n    </svg>\n  );\n}\n\nexport function IconSidebarLogs({ size = 20, ...props }: IconProps) {\n",
        "export function IconSidebarMonitor",
    )


def patch_quota_types(target: Path) -> None:
    path = target / 'src/types/quota.ts'
    insert_before_once(
        path,
        "export interface AntigravityQuotaSummaryBucketPayload",
        GEMINI_CLI_API_TYPES,
        "export interface GeminiCliQuotaPayload",
    )
    insert_before_once(
        path,
        "export interface CodexUsageWindow",
        GEMINI_CLI_STATE_TYPES,
        "export interface GeminiCliQuotaState",
    )
    for interface_name in [
        'ClaudeQuotaState',
        'AntigravityQuotaState',
        'CodexQuotaState',
        'KimiQuotaState',
        'XaiQuotaState',
    ]:
        ensure_interface_field(path, interface_name, 'cachedAt?: number;')
    ensure_interface_field(path, 'GeminiCliQuotaState', 'cachedAt?: number;', required=False)


def patch_quota_store(target: Path) -> None:
    path = target / 'src/stores/useQuotaStore.ts'
    ensure_import_members(path, '@/types', ['GeminiCliQuotaState'], type_import=True)
    replace_once(
        path,
        "  codexQuota: Record<string, CodexQuotaState>;\n  kimiQuota: Record<string, KimiQuotaState>;\n",
        "  codexQuota: Record<string, CodexQuotaState>;\n  geminiCliQuota: Record<string, GeminiCliQuotaState>;\n  kimiQuota: Record<string, KimiQuotaState>;\n",
    )
    replace_once(
        path,
        "  setCodexQuota: (updater: QuotaUpdater<Record<string, CodexQuotaState>>) => void;\n  setKimiQuota: (updater: QuotaUpdater<Record<string, KimiQuotaState>>) => void;\n",
        "  setCodexQuota: (updater: QuotaUpdater<Record<string, CodexQuotaState>>) => void;\n  setGeminiCliQuota: (updater: QuotaUpdater<Record<string, GeminiCliQuotaState>>) => void;\n  setKimiQuota: (updater: QuotaUpdater<Record<string, KimiQuotaState>>) => void;\n",
    )
    replace_once(
        path,
        "  codexQuota: {},\n  kimiQuota: {},\n",
        "  codexQuota: {},\n  geminiCliQuota: {},\n  kimiQuota: {},\n",
    )
    replace_once(
        path,
        "  setCodexQuota: (updater) =>\n    set((state) => ({\n      codexQuota: resolveUpdater(updater, state.codexQuota),\n    })),\n  setKimiQuota: (updater) =>\n",
        "  setCodexQuota: (updater) =>\n    set((state) => ({\n      codexQuota: resolveUpdater(updater, state.codexQuota),\n    })),\n  setGeminiCliQuota: (updater) =>\n    set((state) => ({\n      geminiCliQuota: resolveUpdater(updater, state.geminiCliQuota),\n    })),\n  setKimiQuota: (updater) =>\n",
    )
    replace_once(
        path,
        "      codexQuota: {},\n      kimiQuota: {},\n",
        "      codexQuota: {},\n      geminiCliQuota: {},\n      kimiQuota: {},\n",
    )


def patch_gemini_cli_quota_utils(target: Path) -> None:
    constants_path = target / 'src/utils/quota/constants.ts'
    ensure_import_members(constants_path, '@/types', ['GeminiCliQuotaGroupDefinition'], type_import=True)
    insert_before_once(
        constants_path,
        "  aistudio: {\n",
        "  'gemini-cli': {\n    light: { bg: '#e0e8ff', text: '#1e4fa3' },\n    dark: { bg: '#1c3f73', text: '#a8c7ff' },\n  },\n",
        "'gemini-cli':",
    )
    insert_before_once(
        constants_path,
        "// Claude API configuration",
        GEMINI_CLI_CONSTANTS,
        "GEMINI_CLI_QUOTA_URL",
    )

    parsers_path = target / 'src/utils/quota/parsers.ts'
    ensure_import_members(
        parsers_path,
        '@/types',
        ['GeminiCliCodeAssistPayload', 'GeminiCliQuotaPayload'],
        type_import=True,
    )
    insert_once(
        parsers_path,
        "export { normalizeAuthIndex };\n\n",
        "export { normalizeAuthIndex };\n\n" + GEMINI_CLI_PARSERS,
        "normalizeGeminiCliModelId",
    )
    insert_before_once(
        parsers_path,
        "export function parseKimiUsagePayload",
        GEMINI_CLI_PARSE_PAYLOADS,
        "parseGeminiCliQuotaPayload",
    )

    builders_path = target / 'src/utils/quota/builders.ts'
    ensure_import_members(
        builders_path,
        '@/types',
        ['GeminiCliParsedBucket', 'GeminiCliQuotaBucketState'],
        type_import=True,
    )
    ensure_named_import(
        builders_path,
        "import { GEMINI_CLI_GROUP_LOOKUP, GEMINI_CLI_GROUP_ORDER } from './constants';\n",
        "} from '@/types';\n",
        "GEMINI_CLI_GROUP_LOOKUP",
    )
    ensure_named_import(
        builders_path,
        "import { isIgnoredGeminiCliModel } from './validators';\n",
        "import { normalizeQuotaFraction, normalizeStringValue } from './parsers';\n",
        "isIgnoredGeminiCliModel",
    )
    insert_before_once(
        builders_path,
        "const ANTIGRAVITY_BUCKET_WINDOW_ORDER",
        GEMINI_CLI_BUILDERS,
        "buildGeminiCliQuotaBuckets",
    )


GEMINI_CLI_QUOTA_CONFIG_HELPERS = """const GEMINI_CLI_G1_CREDIT_TYPE = 'GOOGLE_ONE_AI';

const GEMINI_CLI_TIER_LABELS: Record<string, string> = {
  'free-tier': 'tier_free',
  'legacy-tier': 'tier_legacy',
  'standard-tier': 'tier_standard',
  'g1-pro-tier': 'tier_pro',
  'g1-ultra-tier': 'tier_ultra',
};

const resolveGeminiCliTierLabel = (
  payload: GeminiCliCodeAssistPayload | null,
  t: TFunction
): string | null => {
  if (!payload) return null;
  const currentTier: GeminiCliUserTier | null | undefined =
    payload.currentTier ?? payload.current_tier;
  const paidTier: GeminiCliUserTier | null | undefined = payload.paidTier ?? payload.paid_tier;
  const rawId = normalizeStringValue(paidTier?.id) ?? normalizeStringValue(currentTier?.id);
  if (!rawId) return null;
  const tierId = rawId.toLowerCase();
  const labelKey = GEMINI_CLI_TIER_LABELS[tierId];
  return labelKey ? t(`gemini_cli_quota.${labelKey}`) : rawId;
};

const resolveGeminiCliTierId = (payload: GeminiCliCodeAssistPayload | null): string | null => {
  if (!payload) return null;
  const currentTier: GeminiCliUserTier | null | undefined =
    payload.currentTier ?? payload.current_tier;
  const paidTier: GeminiCliUserTier | null | undefined = payload.paidTier ?? payload.paid_tier;
  const rawId = normalizeStringValue(paidTier?.id) ?? normalizeStringValue(currentTier?.id);
  return rawId ? rawId.toLowerCase() : null;
};

const resolveGeminiCliCreditBalance = (
  payload: GeminiCliCodeAssistPayload | null
): number | null => {
  if (!payload) return null;
  const paidTier: GeminiCliUserTier | null | undefined = payload.paidTier ?? payload.paid_tier;
  const currentTier: GeminiCliUserTier | null | undefined =
    payload.currentTier ?? payload.current_tier;
  const tier = paidTier ?? currentTier;
  if (!tier) return null;
  const credits: GeminiCliCredits[] = tier.availableCredits ?? tier.available_credits ?? [];
  let total = 0;
  let found = false;
  for (const credit of credits) {
    const creditType = normalizeStringValue(credit.creditType ?? credit.credit_type);
    if (creditType !== GEMINI_CLI_G1_CREDIT_TYPE) continue;
    const amount = normalizeNumberValue(credit.creditAmount ?? credit.credit_amount);
    if (amount !== null) {
      total += amount;
      found = true;
    }
  }
  return found ? total : null;
};

const fetchGeminiCliCodeAssist = async (
  authIndex: string,
  projectId: string,
  t: TFunction
): Promise<{ tierLabel: string | null; tierId: string | null; creditBalance: number | null }> => {
  try {
    const result = await apiCallApi.request({
      authIndex,
      method: 'POST',
      url: GEMINI_CLI_CODE_ASSIST_URL,
      header: { ...GEMINI_CLI_REQUEST_HEADERS },
      data: JSON.stringify({
        cloudaicompanionProject: projectId,
        metadata: {
          ideType: 'IDE_UNSPECIFIED',
          platform: 'PLATFORM_UNSPECIFIED',
          pluginType: 'GEMINI',
          duetProject: projectId,
        },
      }),
    });

    if (result.statusCode < 200 || result.statusCode >= 300) {
      return { tierLabel: null, tierId: null, creditBalance: null };
    }

    const payload = parseGeminiCliCodeAssistPayload(result.body ?? result.bodyText);
    return {
      tierLabel: resolveGeminiCliTierLabel(payload, t),
      tierId: resolveGeminiCliTierId(payload),
      creditBalance: resolveGeminiCliCreditBalance(payload),
    };
  } catch {
    return { tierLabel: null, tierId: null, creditBalance: null };
  }
};

const readGeminiCliSupplementarySnapshot = (
  fileName: string,
  requestId: number
): { tierLabel: string | null; tierId: string | null; creditBalance: number | null } => {
  const cached = geminiCliSupplementaryCache.get(fileName);
  if (!cached || cached.requestId !== requestId) {
    return { tierLabel: null, tierId: null, creditBalance: null };
  }

  return {
    tierLabel: cached.tierLabel,
    tierId: cached.tierId,
    creditBalance: cached.creditBalance,
  };
};

const scheduleGeminiCliSupplementaryRefresh = (
  fileName: string,
  authIndex: string,
  projectId: string,
  t: TFunction
): number => {
  const requestId = (geminiCliSupplementaryRequestIds.get(fileName) ?? 0) + 1;
  geminiCliSupplementaryRequestIds.set(fileName, requestId);
  geminiCliSupplementaryCache.delete(fileName);

  void (async () => {
    const supplementary = await fetchGeminiCliCodeAssist(authIndex, projectId, t);
    if (geminiCliSupplementaryRequestIds.get(fileName) !== requestId) {
      return;
    }

    geminiCliSupplementaryCache.set(fileName, { requestId, ...supplementary });

    useQuotaStore.getState().setGeminiCliQuota((prev) => {
      const current = prev[fileName];
      if (!current || current.status !== 'success') {
        return prev;
      }

      if (
        current.tierLabel === supplementary.tierLabel &&
        current.tierId === supplementary.tierId &&
        current.creditBalance === supplementary.creditBalance
      ) {
        return prev;
      }

      return {
        ...prev,
        [fileName]: {
          ...current,
          tierLabel: supplementary.tierLabel,
          tierId: supplementary.tierId,
          creditBalance: supplementary.creditBalance,
          cachedAt: Date.now(),
        },
      };
    });
  })();

  return requestId;
};

const fetchGeminiCliQuota = async (
  file: AuthFileItem,
  t: TFunction
): Promise<{
  fileName: string;
  supplementaryRequestId: number;
  buckets: GeminiCliQuotaBucketState[];
  tierLabel: string | null;
  tierId: string | null;
  creditBalance: number | null;
}> => {
  const rawAuthIndex = file['auth_index'] ?? file.authIndex;
  const authIndex = normalizeAuthIndex(rawAuthIndex);
  if (!authIndex) {
    throw new Error(t('gemini_cli_quota.missing_auth_index'));
  }

  const projectId = resolveGeminiCliProjectId(file);
  if (!projectId) {
    throw new Error(t('gemini_cli_quota.missing_project_id'));
  }

  const quotaResponse = await apiCallApi.request({
    authIndex,
    method: 'POST',
    url: GEMINI_CLI_QUOTA_URL,
    header: { ...GEMINI_CLI_REQUEST_HEADERS },
    data: JSON.stringify({ project: projectId }),
  });
  if (quotaResponse.statusCode < 200 || quotaResponse.statusCode >= 300) {
    throw createStatusError(getApiCallErrorMessage(quotaResponse), quotaResponse.statusCode);
  }

  const payload = parseGeminiCliQuotaPayload(quotaResponse.body ?? quotaResponse.bodyText);
  const buckets = Array.isArray(payload?.buckets) ? payload?.buckets : [];

  const parsedBuckets = buckets
    .map((bucket) => {
      const modelId = normalizeGeminiCliModelId(bucket.modelId ?? bucket.model_id);
      if (!modelId) return null;
      const tokenType = normalizeStringValue(bucket.tokenType ?? bucket.token_type);
      const remainingFractionRaw = normalizeQuotaFraction(
        bucket.remainingFraction ?? bucket.remaining_fraction
      );
      const remainingAmount = normalizeNumberValue(
        bucket.remainingAmount ?? bucket.remaining_amount
      );
      const resetTime = normalizeStringValue(bucket.resetTime ?? bucket.reset_time) ?? undefined;
      let fallbackFraction: number | null = null;
      if (remainingAmount !== null) {
        fallbackFraction = remainingAmount <= 0 ? 0 : null;
      } else if (resetTime) {
        fallbackFraction = 0;
      }
      const remainingFraction = remainingFractionRaw ?? fallbackFraction;
      return {
        modelId,
        tokenType,
        remainingFraction,
        remainingAmount,
        resetTime,
      };
    })
    .filter((bucket): bucket is GeminiCliParsedBucket => bucket !== null);

  const builtBuckets = buildGeminiCliQuotaBuckets(parsedBuckets);
  const supplementaryRequestId = scheduleGeminiCliSupplementaryRefresh(
    file.name,
    authIndex,
    projectId,
    t
  );
  const supplementarySnapshot = readGeminiCliSupplementarySnapshot(
    file.name,
    supplementaryRequestId
  );

  return {
    fileName: file.name,
    supplementaryRequestId,
    buckets: builtBuckets,
    tierLabel: supplementarySnapshot.tierLabel,
    tierId: supplementarySnapshot.tierId,
    creditBalance: supplementarySnapshot.creditBalance,
  };
};

"""


GEMINI_CLI_RENDER_ITEMS = """const renderGeminiCliItems = (
  quota: GeminiCliQuotaState,
  t: TFunction,
  helpers: QuotaRenderHelpers
): ReactNode => {
  const { styles: styleMap, QuotaProgressBar } = helpers;
  const { createElement: h, Fragment } = React;
  const buckets = Array.isArray(quota.buckets) ? quota.buckets : [];
  const nodes: ReactNode[] = [];

  if (quota.tierLabel || quota.creditBalance !== null) {
    nodes.push(
      h(
        'div',
        { key: 'tier', className: styleMap.codexPlan },
        h('span', { className: styleMap.codexPlanLabel }, t('gemini_cli_quota.tier_label')),
        h('span', { className: styleMap.codexPlanValue }, quota.tierLabel ?? '--')
      )
    );
  }

  if (quota.creditBalance !== undefined && quota.creditBalance !== null) {
    nodes.push(
      h(
        'div',
        { key: 'credits', className: styleMap.codexPlan },
        h('span', { className: styleMap.codexPlanLabel }, t('gemini_cli_quota.credit_label')),
        h('span', { className: styleMap.codexPlanValue }, String(quota.creditBalance))
      )
    );
  }

  if (buckets.length === 0) {
    nodes.push(
      h('div', { key: 'empty', className: styleMap.quotaMessage }, t('gemini_cli_quota.empty_buckets'))
    );
    return h(Fragment, null, ...nodes);
  }

  nodes.push(
    ...buckets.map((bucket) => {
      const remainingFraction = bucket.remainingFraction;
      const remaining =
        remainingFraction === null ? null : Math.max(0, Math.min(100, remainingFraction * 100));
      const percentLabel = remaining === null ? '--' : `${Math.round(remaining)}%`;
      const amountLabel =
        bucket.remainingAmount === null || bucket.remainingAmount === undefined
          ? null
          : String(bucket.remainingAmount);
      const resetLabel = formatQuotaResetTime(bucket.resetTime);

      return h(
        'div',
        { key: bucket.id, className: styleMap.quotaRow },
        h(
          'div',
          { className: styleMap.quotaRowHeader },
          h('span', { className: styleMap.quotaModel }, bucket.label),
          h(
            'div',
            { className: styleMap.quotaMeta },
            h('span', { className: styleMap.quotaPercent }, percentLabel),
            amountLabel ? h('span', { className: styleMap.quotaAmount }, amountLabel) : null,
            h('span', { className: styleMap.quotaReset }, resetLabel)
          )
        ),
        h(QuotaProgressBar, {
          percent: remaining,
          highThreshold: QUOTA_PROGRESS_HIGH_THRESHOLD,
          mediumThreshold: QUOTA_PROGRESS_MEDIUM_THRESHOLD,
        })
      );
    })
  );

  return h(Fragment, null, ...nodes);
};

"""


GEMINI_CLI_CONFIG_BLOCK = """export const GEMINI_CLI_CONFIG: QuotaConfig<
  GeminiCliQuotaState,
  {
    fileName: string;
    supplementaryRequestId: number;
    buckets: GeminiCliQuotaBucketState[];
    tierLabel: string | null;
    tierId: string | null;
    creditBalance: number | null;
  }
> = {
  type: 'gemini-cli',
  i18nPrefix: 'gemini_cli_quota',
  cardIdleMessageKey: 'quota_management.card_idle_hint',
  filterFn: (file) =>
    isGeminiCliFile(file) && !isRuntimeOnlyAuthFile(file) && !isDisabledAuthFile(file),
  fetchQuota: fetchGeminiCliQuota,
  storeSelector: (state) => state.geminiCliQuota,
  storeSetter: 'setGeminiCliQuota',
  buildLoadingState: () => ({
    status: 'loading',
    buckets: [],
    tierLabel: null,
    tierId: null,
    creditBalance: null,
  }),
  buildSuccessState: (data) => {
    const supplementarySnapshot = readGeminiCliSupplementarySnapshot(
      data.fileName,
      data.supplementaryRequestId
    );

    return {
      status: 'success',
      buckets: data.buckets,
      tierLabel: supplementarySnapshot.tierLabel ?? data.tierLabel,
      tierId: supplementarySnapshot.tierId ?? data.tierId,
      creditBalance: supplementarySnapshot.creditBalance ?? data.creditBalance,
      cachedAt: Date.now(),
    };
  },
  buildErrorState: (message, status) => ({
    status: 'error',
    buckets: [],
    error: message,
    errorStatus: status,
  }),
  cardClassName: styles.geminiCliCard,
  controlsClassName: styles.geminiCliControls,
  controlClassName: styles.geminiCliControl,
  gridClassName: styles.geminiCliGrid,
  renderQuotaItems: renderGeminiCliItems,
};

"""


def patch_gemini_cli_quota_configs(path: Path) -> None:
    ensure_import_members(
        path,
        '@/types',
        [
            'GeminiCliCodeAssistPayload',
            'GeminiCliCredits',
            'GeminiCliParsedBucket',
            'GeminiCliQuotaBucketState',
            'GeminiCliQuotaState',
            'GeminiCliUserTier',
        ],
        type_import=True,
    )
    ensure_named_import(
        path,
        "import { useQuotaStore } from '@/stores';\n",
        "} from '@/services/api';\n",
        "useQuotaStore",
    )
    ensure_import_members(
        path,
        '@/utils/quota',
        [
            'GEMINI_CLI_CODE_ASSIST_URL',
            'GEMINI_CLI_QUOTA_URL',
            'GEMINI_CLI_REQUEST_HEADERS',
            'buildGeminiCliQuotaBuckets',
            'isGeminiCliFile',
            'isRuntimeOnlyAuthFile',
            'normalizeGeminiCliModelId',
            'normalizeQuotaFraction',
            'parseGeminiCliCodeAssistPayload',
            'parseGeminiCliQuotaPayload',
            'resolveGeminiCliProjectId',
        ],
    )
    replace_once(
        path,
        "type QuotaType = 'antigravity' | 'claude' | 'codex' | 'kimi' | 'xai';",
        "type QuotaType = 'antigravity' | 'claude' | 'codex' | 'gemini-cli' | 'kimi' | 'xai';",
    )
    replace_once(
        path,
        "  codexQuota: Record<string, CodexQuotaState>;\n  kimiQuota: Record<string, KimiQuotaState>;\n",
        "  codexQuota: Record<string, CodexQuotaState>;\n  geminiCliQuota: Record<string, GeminiCliQuotaState>;\n  kimiQuota: Record<string, KimiQuotaState>;\n",
    )
    replace_once(
        path,
        "  setCodexQuota: (updater: QuotaUpdater<Record<string, CodexQuotaState>>) => void;\n  setKimiQuota: (updater: QuotaUpdater<Record<string, KimiQuotaState>>) => void;\n",
        "  setCodexQuota: (updater: QuotaUpdater<Record<string, CodexQuotaState>>) => void;\n  setGeminiCliQuota: (updater: QuotaUpdater<Record<string, GeminiCliQuotaState>>) => void;\n  setKimiQuota: (updater: QuotaUpdater<Record<string, KimiQuotaState>>) => void;\n",
    )
    insert_once(
        path,
        "const QUOTA_PROGRESS_MEDIUM_THRESHOLD = 30;\n",
        "const QUOTA_PROGRESS_MEDIUM_THRESHOLD = 30;\nconst geminiCliSupplementaryRequestIds = new Map<string, number>();\nconst geminiCliSupplementaryCache = new Map<\n  string,\n  {\n    requestId: number;\n    tierLabel: string | null;\n    tierId: string | null;\n    creditBalance: number | null;\n  }\n>();\n",
        "geminiCliSupplementaryRequestIds",
    )
    insert_before_once(
        path,
        "const formatAntigravityDuration",
        GEMINI_CLI_QUOTA_CONFIG_HELPERS,
        "fetchGeminiCliQuota",
    )
    insert_before_once(
        path,
        "const fetchKimiQuota",
        GEMINI_CLI_CONFIG_BLOCK,
        "export const GEMINI_CLI_CONFIG",
    )
    insert_before_once(
        path,
        "export const GEMINI_CLI_CONFIG",
        GEMINI_CLI_RENDER_ITEMS,
        "const renderGeminiCliItems",
    )
def patch_quota_configs(target: Path) -> None:
    path = target / 'src/components/quota/quotaConfigs.ts'
    patch_gemini_cli_quota_configs(path)
    for store_setter, old, new in [
        (
            'setClaudeQuota',
            "    extraUsage: data.extraUsage,\n    planType: data.planType,\n  }),",
            "    extraUsage: data.extraUsage,\n    planType: data.planType,\n    cachedAt: Date.now(),\n  }),",
        ),
        (
            'setAntigravityQuota',
            "    serverTimeOffsetMs: data.serverTimeOffsetMs,\n  }),",
            "    serverTimeOffsetMs: data.serverTimeOffsetMs,\n    cachedAt: Date.now(),\n  }),",
        ),
        (
            'setCodexQuota',
            "    windows: data.windows,\n    planType: data.planType,\n    subscriptionActiveUntil: data.subscriptionActiveUntil,\n    rateLimitResetCreditsAvailableCount: data.rateLimitResetCreditsAvailableCount,\n  }),",
            "    windows: data.windows,\n    planType: data.planType,\n    subscriptionActiveUntil: data.subscriptionActiveUntil,\n    rateLimitResetCreditsAvailableCount: data.rateLimitResetCreditsAvailableCount,\n    cachedAt: Date.now(),\n  }),",
        ),
        (
            'setGeminiCliQuota',
            "      creditBalance: supplementarySnapshot.creditBalance ?? data.creditBalance,\n    };",
            "      creditBalance: supplementarySnapshot.creditBalance ?? data.creditBalance,\n      cachedAt: Date.now(),\n    };",
        ),
        (
            'setKimiQuota',
            "  buildSuccessState: (rows) => ({ status: 'success', rows }),",
            "  buildSuccessState: (rows) => ({ status: 'success', rows, cachedAt: Date.now() }),",
        ),
        (
            'setXaiQuota',
            "  buildSuccessState: (billing) => ({ status: 'success', billing }),",
            "  buildSuccessState: (billing) => ({ status: 'success', billing, cachedAt: Date.now() }),",
        ),
    ]:
        replace_once_in_quota_config(path, store_setter, old, new)
    for old, new in [
        (
            "  const groups = quota.groups ?? [];\n",
            "  const groups = Array.isArray(quota.groups) ? quota.groups : [];\n",
        ),
        (
            "        ...group.buckets.map((bucket) => {\n",
            "        ...(Array.isArray(group.buckets) ? group.buckets : []).map((bucket) => {\n",
        ),
        (
            "  const buckets = quota.buckets ?? [];\n",
            "  const buckets = Array.isArray(quota.buckets) ? quota.buckets : [];\n",
        ),
    ]:
        replace_all(path, old, new)


def patch_quota_page(target: Path) -> None:
    path = target / 'src/pages/QuotaPage.tsx'
    replace_all(
        path,
        "import { FEATURES } from '@/config/features';\nimport { quotaPersistenceMiddleware } from '@/extensions/quota/persistenceMiddleware';\n",
        "",
    )
    replace_once(
        path,
        "import { useAuthStore } from '@/stores';\n",
        "import { quotaPersistenceMiddleware } from '@/extensions/quota/persistenceMiddleware';\nimport { useAuthStore } from '@/stores';\n",
    )
    replace_once(
        path,
        "  useEffect(() => {\n    loadFiles();\n  }, [loadFiles]);\n",
        "  useEffect(() => {\n    loadFiles();\n    void quotaPersistenceMiddleware.ensureFresh();\n  }, [loadFiles]);\n",
    )
    replace_all(
        path,
        "\n  useEffect(() => {\n    if (!FEATURES.QUOTA_PERSISTENCE) return;\n    quotaPersistenceMiddleware.start();\n    return () => quotaPersistenceMiddleware.stop();\n  }, []);\n",
        "",
    )
    replace_all(
        path,
        "\n  // Initialize persistence middleware\n  useEffect(() => {\n    if (FEATURES.QUOTA_PERSISTENCE) {\n      quotaPersistenceMiddleware.start();\n      return () => quotaPersistenceMiddleware.stop();\n    }\n  }, []);\n",
        "",
    )


def patch_quota_card(target: Path) -> None:
    path = target / 'src/components/quota/QuotaCard.tsx'
    replace_once(
        path,
        "import { TYPE_COLORS } from '@/utils/quota';\n",
        "import { QuotaCachedTime } from '@/extensions/quota/QuotaCardExtras';\nimport { TYPE_COLORS } from '@/utils/quota';\n",
    )
    replace_once(path, "  errorStatus?: number;\n}", "  errorStatus?: number;\n  cachedAt?: number;\n}")
    replace_once(
        path,
        "        ) : quota ? (\n          renderQuotaItems(quota, t, { styles, QuotaProgressBar })\n        ) : (",
        "        ) : quota ? (\n          <>\n            {renderQuotaItems(quota, t, { styles, QuotaProgressBar })}\n            <QuotaCachedTime quotaStatus={quotaStatus} cachedAt={quota.cachedAt} />\n          </>\n        ) : (",
    )


def patch_antigravity_quota_builders(target: Path) -> None:
    path = target / 'src/utils/quota/builders.ts'
    insert_once(
        path,
        "\nfunction getAntigravityWindowOrder(bucket: AntigravityQuotaBucket): number {\n",
        "\nfunction getCanonicalAntigravityGroupId(label: string, description?: string): string {\n  const normalizedLabel = toStableId(label, '');\n  const normalizedDescription = description ? toStableId(description, '') : '';\n  const combined = `${normalizedLabel}-${normalizedDescription}`;\n  if (combined.includes('claude') && (combined.includes('gpt') || combined.includes('gpt-oss') || combined.includes('openai'))) {\n    return 'claude-gpt';\n  }\n  if (combined.includes('gemini')) {\n    return 'gemini';\n  }\n  return normalizedLabel;\n}\n\nfunction getAntigravityWindowOrder(bucket: AntigravityQuotaBucket): number {\n",
        "getCanonicalAntigravityGroupId",
    )
    replace_once(
        path,
        "      const groupId = toStableId(label, `quota-group-${groupIndex + 1}`);\n      const buckets = Array.isArray(group.buckets) ? group.buckets : [];\n",
        "      const description = normalizeStringValue(group.description) ?? undefined;\n      const groupId = getCanonicalAntigravityGroupId(label, description) || `quota-group-${groupIndex + 1}`;\n      const buckets = Array.isArray(group.buckets) ? group.buckets : [];\n",
    )
    replace_once(
        path,
        "        description: normalizeStringValue(group.description) ?? undefined,\n",
        "        description,\n",
    )


def patch_quota_styles(target: Path) -> None:
    path = target / 'src/pages/QuotaPage.module.scss'
    for old, new in [
        (".antigravityGrid,\n.claudeGrid,\n.codexGrid,\n.kimiGrid,\n", ".antigravityGrid,\n.claudeGrid,\n.codexGrid,\n.geminiCliGrid,\n.kimiGrid,\n"),
        (".antigravityControls,\n.claudeControls,\n.codexControls,\n.kimiControls,\n", ".antigravityControls,\n.claudeControls,\n.codexControls,\n.geminiCliControls,\n.kimiControls,\n"),
        (".antigravityControl,\n.claudeControl,\n.codexControl,\n.kimiControl,\n", ".antigravityControl,\n.claudeControl,\n.codexControl,\n.geminiCliControl,\n.kimiControl,\n"),
    ]:
        replace_once(path, old, new)
    insert_once(
        path,
        ".kimiCard {\n  background-image: linear-gradient(180deg, rgba(220, 232, 255, 0.2), rgba(220, 232, 255, 0));\n}\n",
        ".geminiCliCard {\n  background-image: linear-gradient(180deg, rgba(224, 232, 255, 0.2), rgba(224, 232, 255, 0));\n}\n\n.kimiCard {\n  background-image: linear-gradient(180deg, rgba(220, 232, 255, 0.2), rgba(220, 232, 255, 0));\n}\n",
        ".geminiCliCard",
    )


def patch_supporting_api_and_types(target: Path) -> None:
    config_path = target / 'src/types/config.ts'
    replace_once(
        config_path,
        "export interface Config {\n  debug?: boolean;\n",
        "export interface AuthPoolCleanConfig {\n  baseUrl?: string;\n  token?: string;\n  targetType?: string;\n  workers?: number;\n  deleteWorkers?: number;\n  timeout?: number;\n  retries?: number;\n  usedPercentThreshold?: number;\n  sampleSize?: number;\n}\n\nexport interface Config {\n  debug?: boolean;\n",
    )
    replace_once(
        config_path,
        "  quotaExceeded?: QuotaExceededConfig;\n  requestLog?: boolean;\n",
        "  quotaExceeded?: QuotaExceededConfig;\n  clean?: AuthPoolCleanConfig;\n  usageStatisticsEnabled?: boolean;\n  requestLog?: boolean;\n",
    )
    replace_once(
        config_path,
        "  | 'quota-exceeded'\n  | 'request-log'\n",
        "  | 'quota-exceeded'\n  | 'usage-statistics-enabled'\n  | 'request-log'\n",
    )

    auth_file_type_path = target / 'src/types/authFile.ts'
    replace_once(
        auth_file_type_path,
        "export interface AuthFileItem {\n  name: string;\n",
        "export interface AuthFileLastError {\n  code?: string;\n  message?: string;\n  retryable?: boolean;\n  http_status?: number;\n  httpStatus?: number;\n}\n\nexport interface AuthFileItem {\n  name: string;\n",
    )
    replace_once(
        auth_file_type_path,
        "  statusMessage?: string;\n  lastRefresh?: string | number;\n",
        "  statusMessage?: string;\n  lastError?: AuthFileLastError | null;\n  'last_error'?: AuthFileLastError | null;\n  lastRefresh?: string | number;\n",
    )

    auth_file_constants_path = target / 'src/features/authFiles/constants.ts'
    replace_once(
        auth_file_constants_path,
        "export const getAuthFileStatusMessage = (file: AuthFileItem): string => {\n  const raw = file['status_message'] ?? file.statusMessage;\n  if (typeof raw === 'string') return raw.trim();\n  if (raw == null) return '';\n  return String(raw).trim();\n};\n",
        "const normalizeAuthFileMessageValue = (value: unknown): string => {\n  if (typeof value === 'string') return value.trim();\n  if (value == null) return '';\n  return String(value).trim();\n};\n\nconst getAuthFileLastErrorMessage = (file: AuthFileItem): string => {\n  const raw = file['last_error'] ?? file.lastError;\n  if (!raw || typeof raw !== 'object') return '';\n  return normalizeAuthFileMessageValue((raw as { message?: unknown }).message);\n};\n\nexport const getAuthFileStatusMessage = (file: AuthFileItem): string => {\n  const statusMessage = normalizeAuthFileMessageValue(file['status_message'] ?? file.statusMessage);\n  return statusMessage || getAuthFileLastErrorMessage(file);\n};\n",
    )

    auth_files_path = target / 'src/services/api/authFiles.ts'
    replace_once(
        auth_files_path,
        "type AuthFileStatusResponse = { status: string; disabled: boolean };\n",
        "type AuthFileStatusResponse = { status: string; disabled: boolean };\ntype AuthFilePatchPayload = { name: string; disabled?: boolean; [key: string]: unknown };\n",
    )
    insert_once(
        auth_files_path,
        "export const authFilesApi = {\n",
        "const AUTH_FILES_LIST_CACHE_TTL_MS = 2000;\nlet authFilesListCache: { expiresAt: number; response: AuthFilesResponse } | null = null;\nlet authFilesListRequest: Promise<AuthFilesResponse> | null = null;\nlet authFilesListVersion = 0;\n\nconst cloneAuthFilesResponse = (response: AuthFilesResponse): AuthFilesResponse => ({\n  ...response,\n  files: Array.isArray(response.files) ? [...response.files] : [],\n});\n\nconst invalidateAuthFilesListCache = () => {\n  authFilesListVersion += 1;\n  authFilesListCache = null;\n  authFilesListRequest = null;\n};\n\nconst fetchAuthFilesList = async (): Promise<AuthFilesResponse> => {\n  const now = Date.now();\n  if (authFilesListCache && authFilesListCache.expiresAt > now) {\n    return cloneAuthFilesResponse(authFilesListCache.response);\n  }\n  if (!authFilesListRequest) {\n    const requestVersion = authFilesListVersion;\n    authFilesListRequest = apiClient.get<AuthFilesResponse>('/auth-files')\n      .then(dedupeAuthFilesResponse)\n      .then((response) => {\n        if (requestVersion === authFilesListVersion) {\n          authFilesListCache = {\n            expiresAt: Date.now() + AUTH_FILES_LIST_CACHE_TTL_MS,\n            response: cloneAuthFilesResponse(response),\n          };\n        }\n        return response;\n      })\n      .finally(() => {\n        if (requestVersion === authFilesListVersion) {\n          authFilesListRequest = null;\n        }\n      });\n  }\n  return cloneAuthFilesResponse(await authFilesListRequest);\n};\n\nexport const authFilesApi = {\n",
        "AUTH_FILES_LIST_CACHE_TTL_MS",
    )
    replace_once(
        auth_files_path,
        "  list: async () => dedupeAuthFilesResponse(await apiClient.get<AuthFilesResponse>('/auth-files')),\n\n  setStatus: (name: string, disabled: boolean) =>\n    apiClient.patch<AuthFileStatusResponse>('/auth-files/status', { name, disabled }),\n\n",
        "  list: fetchAuthFilesList,\n\n  patchFile: async (payload: AuthFilePatchPayload) => {\n    const response = await apiClient.patch<AuthFileStatusResponse>('/auth-files', payload);\n    invalidateAuthFilesListCache();\n    return response;\n  },\n\n  setStatus: async (name: string, disabled: boolean) => {\n    const response = await apiClient.patch<AuthFileStatusResponse>('/auth-files/status', { name, disabled });\n    invalidateAuthFilesListCache();\n    return response;\n  },\n",
    )
    replace_once(
        auth_files_path,
        "  patchFields: (name: string, fields: AuthFileFieldsPatch) =>\n    apiClient.patch('/auth-files/fields', { name, ...fields }),\n\n",
        "  setStatusWithFallback: async (name: string, disabled: boolean) => {\n    try {\n      return await authFilesApi.patchFile({ name, disabled });\n    } catch {\n      return authFilesApi.setStatus(name, disabled);\n    }\n  },\n\n  patchFields: async (name: string, fields: AuthFileFieldsPatch) => {\n    const response = await apiClient.patch('/auth-files/fields', { name, ...fields });\n    invalidateAuthFilesListCache();\n    return response;\n  },\n\n",
    )
    replace_once(
        auth_files_path,
        "    const payload = await apiClient.postForm<AuthFileBatchUploadResponse>('/auth-files', formData);\n    return normalizeBatchUploadResponse(payload, requestedNames);\n",
        "    const payload = await apiClient.postForm<AuthFileBatchUploadResponse>('/auth-files', formData);\n    invalidateAuthFilesListCache();\n    return normalizeBatchUploadResponse(payload, requestedNames);\n",
    )
    replace_once(
        auth_files_path,
        "    const payload = await apiClient.delete<AuthFileBatchDeleteResponse>('/auth-files', {\n      data: { names: requestedNames },\n    });\n    return normalizeBatchDeleteResponse(payload, requestedNames);\n",
        "    const payload = await apiClient.delete<AuthFileBatchDeleteResponse>('/auth-files', {\n      data: { names: requestedNames },\n    });\n    invalidateAuthFilesListCache();\n    return normalizeBatchDeleteResponse(payload, requestedNames);\n",
    )
    replace_once(
        auth_files_path,
        "  deleteAll: () => apiClient.delete('/auth-files', { params: { all: true } }),\n",
        "  deleteAll: async () => {\n    const response = await apiClient.delete('/auth-files', { params: { all: true } });\n    invalidateAuthFilesListCache();\n    return response;\n  },\n",
    )

    api_index_path = target / 'src/services/api/index.ts'
    replace_once(
        api_index_path,
        "export * from './apiCall';\n",
        "export * from './apiCall';\nexport * from './accountInspection';\n",
    )

    format_path = target / 'src/utils/format.ts'
    insert_once(
        format_path,
        "/**\n * 格式化文件大小\n */",
        "const API_KEY_MASK_REGEX =\n  /(sk-[A-Za-z0-9-_]{6,}|sk-ant-[A-Za-z0-9-_]{6,}|AIza[0-9A-Za-z-_]{8,}|AI[a-zA-Z0-9_-]{6,}|hf_[A-Za-z0-9]{6,}|pk_[A-Za-z0-9]{6,}|rk_[A-Za-z0-9]{6,})/g;\n\nexport function maskSensitiveText(value: string): string {\n  const trimmed = String(value || '').trim();\n  if (!trimmed) {\n    return '';\n  }\n\n  return trimmed.replace(API_KEY_MASK_REGEX, (match) => maskApiKey(match));\n}\n\n/**\n * 格式化文件大小\n */",
        "export function maskSensitiveText(value: string): string",
    )

    select_path = target / 'src/components/ui/Select.tsx'
    if 'triggerClassName?: string;' not in read(select_path):
        replace_once(
            select_path,
            "  placeholder?: string;\n  className?: string;\n  disabled?: boolean;\n",
            "  placeholder?: string;\n  className?: string;\n  triggerClassName?: string;\n  dropdownClassName?: string;\n  disabled?: boolean;\n",
        )
    if 'triggerClassName,' not in read(select_path):
        replace_once(
            select_path,
            "  placeholder,\n  className,\n  disabled = false,\n",
            "  placeholder,\n  className,\n  triggerClassName,\n  dropdownClassName,\n  disabled = false,\n",
        )
    if 'dropdownClassName].filter(Boolean).join' not in read(select_path):
        replace_once(
            select_path,
            "            className={styles.dropdown}\n",
            "            className={[styles.dropdown, dropdownClassName].filter(Boolean).join(' ')}\n",
        )
    if 'triggerClassName].filter(Boolean).join' not in read(select_path):
        text = read(select_path)
        old_simple = "          className={styles.trigger}\n"
        old_sized = "          className={`${styles.trigger} ${size === 'sm' ? styles.triggerSm : ''}`.trim()}\n"
        if old_simple in text:
            write(
                select_path,
                text.replace(
                    old_simple,
                    "          className={[styles.trigger, triggerClassName].filter(Boolean).join(' ')}\n",
                    1,
                ),
            )
        elif old_sized in text:
            write(
                select_path,
                text.replace(
                    old_sized,
                    "          className={[styles.trigger, size === 'sm' ? styles.triggerSm : '', triggerClassName].filter(Boolean).join(' ')}\n",
                    1,
                ),
            )
        else:
            raise RuntimeError(f'Pattern not found in {select_path}: Select trigger className')


def patch_locales(target: Path) -> None:
    monitoring = json.loads(LOCALES_FILE.read_text())
    locales_dir = target / 'src/i18n/locales'
    for locale_path in sorted(locales_dir.glob('*.json')):
        data = json.loads(locale_path.read_text())
        additions = monitoring.get(locale_path.name, {})
        data.setdefault('nav', {}).update(additions.get('nav', {}))
        nav_additions = additions.get('nav', {})
        data.setdefault('nav_meta', {}).update(
            additions.get(
                'nav_meta',
                {
                    'monitoring_center': nav_additions.get('monitoring_center', 'Request Monitoring'),
                    'account_inspection': nav_additions.get('account_inspection', 'Account Inspection'),
                },
            )
        )
        data['monitoring'] = additions.get('monitoring', data.get('monitoring', {}))
        data['usage_stats'] = additions.get('usage_stats', data.get('usage_stats', {}))
        data.setdefault('quota_management', {}).update(QUOTA_LOCALE_KEYS.get(locale_path.name, {}))
        data.setdefault('gemini_cli_quota', {}).update(GEMINI_CLI_LOCALE_KEYS.get(locale_path.name, {}))
        locale_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main() -> None:
    if len(sys.argv) > 2:
        raise SystemExit('Usage: apply_customizations.py [target_dir]')
    target = Path(sys.argv[1] if len(sys.argv) == 2 else '.').resolve()
    if not (target / 'src').is_dir() or not (target / 'package.json').is_file():
        raise SystemExit(f'Target directory does not look like the upstream project: {target}')
    if not OVERLAY_DIR.is_dir():
        raise SystemExit(f'Overlay directory not found: {OVERLAY_DIR}')

    copy_overlay(target)
    patch_routes(target)
    patch_layout(target)
    patch_icons(target)
    patch_quota_types(target)
    patch_quota_store(target)
    patch_gemini_cli_quota_utils(target)
    patch_quota_configs(target)
    patch_antigravity_quota_builders(target)
    patch_quota_page(target)
    patch_quota_card(target)
    patch_quota_styles(target)
    patch_supporting_api_and_types(target)
    patch_locales(target)
    flush_writes()
    print(f'OK: CPA-Management customization applied to {target}')


if __name__ == '__main__':
    main()

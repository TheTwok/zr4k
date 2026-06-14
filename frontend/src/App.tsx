import React, { useState, useEffect, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, 
  SquaresFour, 
  Gear, 
  Sparkle, 
  Plus, 
  Trash, 
  ArrowUpRight, 
  WarningCircle, 
  CheckCircle,
  Link,
  Faders,
  LockKey,
  Prohibit,
  Crown,
  Info,
  MagnifyingGlass,
  X,
  ChartLineUp,
  CaretLeft,
  SortAscending,
  SortDescending,
  ArrowCounterClockwise,
  CaretUp,
  CaretDown
} from '@phosphor-icons/react';

const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Moscow";

const originalFetch = window.fetch;
window.fetch = function (input, init) {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as any).url;
  if (url && url.includes('/api/')) {
    init = init || {};
    const headers = new Headers(init.headers || {});
    if (!headers.has('X-User-Timezone')) {
      headers.set('X-User-Timezone', userTimeZone);
    }
    init.headers = headers;
  }
  return originalFetch(input, init);
};

const API_BASE = window.location.origin + "/api";

const TRANSLATIONS = {
  ru: {
    dashboard: "Дашборд",
    digest: "AI Дайджест",
    sources: "Источники",
    settings: "Настройки",
    info: "О приложении",
    admin: "Админ-панель",
    collected: "СОБРАНО",
    sources_count: "ИСТОЧНИКИ",
    feed_title: "Фид сообщений",
    sort_desc: "Сначала новые",
    sort_asc: "Сначала старые",
    empty_feed: "Система в ожидании. Добавьте источники и фильтры для старта.",
    go_to_source: "Перейти к источнику",
    pro_feature_title: "Дайджест",
    pro_feature_desc: "Функция умного сбора ИИ-сводки по всей истории каналов доступна только на PRO-тарифе.",
    activate_pro_btn: "Активировать PRO",
    new_digest_tab: "Создать",
    history_tab: "История",
    daily_digest: "ЕЖЕДНЕВНАЯ РАССЫЛКА",
    daily_digest_desc: "Бот будет автоматически собирать отчет за 24 часа и присылать его в выбранное время каждый день.",
    enable_newsletter: "Включить рассылку",
    time_msk: "Время (МСК):",
    save_schedule: "Сохранить расписание",
    manual_generation: "РУЧНАЯ ГЕНЕРАЦИЯ",
    sources_all_if_none: "ИСТОЧНИКИ (Все если не выбраны):",
    period: "ПЕРИОД (в часах):",
    generate_btn: "Сгенерировать",
    generating_btn: "Собираем историю...",
    history_empty: "История пуста.",
    digest_period_hours: "Период: {hours}ч",
    add_source_title: "ДОБАВИТЬ ИСТОЧНИК",
    placeholder_source: "@username или t.me/...",
    sources_title: "ИСТОЧНИКИ",
    empty_sources: "Нет активных источников.",
    placeholder_keywords: "Слово или фраза...",
    filters_title: "ФИЛЬТРЫ",
    filter_mode_semantic: "Смысловой",
    filter_mode_phrase: "Точная фраза",
    filter_mode_word: "Точное слово",
    filter_mode_exclude: "Исключить",
    no_filters: "Нет фильтров.",
    account_title: "АККАУНТ",
    subscription_status: "Статус подписки",
    status_lifetime: "Бессрочно",
    activate_code_title: "АКТИВАЦИЯ КОДА",
    placeholder_promo: "XXXX-XXXX-XXXX...",
    activate_btn: "Активировать",
    app_developer: "Разработчик",
    info_desc: "Многофункциональный инструмент для мониторинга Telegram-каналов в реальном времени и умного ИИ-анализа сообщений. Настраивайте гибкие фильтры, ловите важные новости и создавайте краткие ИИ-дайджесты за любой период.",
    app_version: "Версия",
    app_doc_btn: "Документация",
    admin_users: "ПОЛЬЗОВАТЕЛИ",
    admin_pro: "ПОДПИСЧИКИ",
    admin_promos: "ПРОМОКОДЫ",
    admin_channels: "КАНАЛЫ",
    admin_income: "ДОХОД (STARS)",
    admin_income_unit: "XTR",
    admin_search_placeholder: "Поиск пользователей...",
    admin_create_promo: "СОЗДАТЬ",
    admin_promo_days: "Дни",
    admin_promo_uses: "Использования",
    admin_promo_created: "Промокод {code} создан",
    admin_promo_details: "Дни: {days} · Исп: {uses}/{max}",
    get_pro_title: "Получить PRO",
    get_pro_desc: "Снятие ограничений. До 100 каналов, 200 фильтров и умный AI Дайджест с историей.",
    pay_stars_btn: "Оплатить (50 Stars)",
    user_card_title: "Карточка пользователя",
    user_status_banned: "ЗАБЛОКИРОВАН",
    user_expires_at: "Истекает",
    user_connected_channels: "ПОДКЛЮЧЕННЫЕ КАНАЛЫ ({count})",
    user_no_channels: "Нет каналов.",
    user_messages_last: "СООБЩЕНИЯ (Последние 50)",
    user_no_messages: "Нет сообщений.",
    user_manage_subscription: "Подписка",
    user_unban: "Разблокировать",
    user_ban: "Заблокировать",
    manage_pro_title: "Управление",
    manage_pro_days: "дней",
    manage_pro_grant: "Выдать подписку",
    manage_pro_remove: "Удалить подписку",
    ban_confirm_title: "Блокировка",
    ban_confirm_desc: "Заблокировать пользователя {id}?",
    cancel: "Отмена",
    ban_btn: "Заблокировать",
    confirm_delete_source: "Вы уверены, что хотите удалить этот источник?"
  },
  en: {
    dashboard: "Dashboard",
    digest: "AI Digest",
    sources: "Sources",
    settings: "Settings",
    info: "About",
    admin: "Admin Panel",
    collected: "COLLECTED",
    sources_count: "SOURCES",
    feed_title: "Message Feed",
    sort_desc: "Newest first",
    sort_asc: "Oldest first",
    empty_feed: "System is waiting. Add sources and filters to start.",
    go_to_source: "Go to source",
    pro_feature_title: "Digest",
    pro_feature_desc: "Smart AI digest of channel history is only available on PRO plan.",
    activate_pro_btn: "Activate PRO",
    new_digest_tab: "Create",
    history_tab: "History",
    daily_digest: "DAILY DIGEST",
    daily_digest_desc: "The bot will automatically collect a 24-hour report and send it at the selected time every day.",
    enable_newsletter: "Enable newsletter",
    time_msk: "Time (MSK):",
    save_schedule: "Save schedule",
    manual_generation: "MANUAL GENERATION",
    sources_all_if_none: "SOURCES (All if none selected):",
    period: "PERIOD (hours):",
    generate_btn: "Generate",
    generating_btn: "Generating...",
    history_empty: "History is empty.",
    digest_period_hours: "Period: {hours}h",
    add_source_title: "ADD SOURCE",
    placeholder_source: "@username or t.me/...",
    sources_title: "SOURCES",
    empty_sources: "No active sources.",
    placeholder_keywords: "Word or phrase...",
    filters_title: "FILTERS",
    filter_mode_semantic: "Semantic",
    filter_mode_phrase: "Exact phrase",
    filter_mode_word: "Exact word",
    filter_mode_exclude: "Exclude",
    no_filters: "No filters.",
    account_title: "ACCOUNT",
    subscription_status: "Subscription status",
    status_lifetime: "Lifetime",
    activate_code_title: "ACTIVATE CODE",
    placeholder_promo: "XXXX-XXXX-XXXX...",
    activate_btn: "Activate",
    app_developer: "Developer",
    info_desc: "ZR4K is a multi-functional real-time monitoring tool for Telegram channels and smart AI analysis. Set up flexible filters, catch important news, and generate concise AI digests for any period.",
    app_version: "Version",
    app_doc_btn: "Documentation",
    admin_users: "USERS",
    admin_pro: "SUBSCRIBERS",
    admin_promos: "PROMO CODES",
    admin_channels: "CHANNELS",
    admin_income: "INCOME (STARS)",
    admin_income_unit: "XTR",
    admin_search_placeholder: "Search users...",
    admin_create_promo: "CREATE",
    admin_promo_days: "Days",
    admin_promo_uses: "Activations",
    admin_promo_created: "Promo code {code} created",
    admin_promo_details: "Days: {days} · Activations: {uses}/{max}",
    get_pro_title: "Get PRO",
    get_pro_desc: "Remove limits. Up to 100 channels, 200 filters and smart AI digest with history.",
    pay_stars_btn: "Pay (50 Stars)",
    user_card_title: "User Card",
    user_status_banned: "BANNED",
    user_expires_at: "Expires",
    user_connected_channels: "CONNECTED CHANNELS ({count})",
    user_no_channels: "No channels.",
    user_messages_last: "MESSAGES (Last 50)",
    user_no_messages: "No messages.",
    user_manage_subscription: "Subscription",
    user_unban: "Unblock",
    user_ban: "Block",
    manage_pro_title: "Management",
    manage_pro_days: "days",
    manage_pro_grant: "Grant Subscription",
    manage_pro_remove: "Remove subscription",
    ban_confirm_title: "Block User",
    ban_confirm_desc: "Block user {id}?",
    cancel: "Cancel",
    ban_btn: "Block",
    confirm_delete_source: "Are you sure you want to delete this source?"
  }
};

interface User {
  telegram_id: number;
  username: string | null;
  language_code: string;
  pro_expires_at: string | null;
  is_pro: boolean;
  is_admin: boolean;
  is_banned?: boolean;
  last_digest_at: string | null;
  digest_schedule_time: string | null;
}

interface ChannelSource {
  id: number;
  username: string;
  title: string | null;
  digest_schedule_time?: string | null;
  digest_schedule_days?: string | null;
}

interface Keyword {
  id: number;
  channel_id: number;
  keyword: string;
  mode: string;
}

interface CaughtMessage {
  id: number;
  channel_id: number;
  channel_username: string;
  channel_title: string | null;
  message_id: number;
  text: string;
  url: string;
  created_at: string;
}

interface DigestHistoryItem {
  id: number;
  text: string;
  period_hours: number;
  created_at: string;
}

export default function App() {
  const tg = (window as any).Telegram?.WebApp;
  const [activeTab, setActiveTab] = useState<'dashboard' | 'digest' | 'sources' | 'settings' | 'info' | 'admin'>('dashboard');
  
  const [user, setUser] = useState<User | null>(null);
  const userLang = (user?.language_code || tg?.initDataUnsafe?.user?.language_code || 'ru').toLowerCase();
  const isRu = userLang.startsWith('ru') || userLang.startsWith('uk') || userLang.startsWith('be');
  const t = (key: keyof typeof TRANSLATIONS.ru, replacements?: Record<string, any>) => {
    const dict = isRu ? TRANSLATIONS.ru : TRANSLATIONS.en;
    let text = dict[key] || TRANSLATIONS.en[key] || String(key);
    if (replacements) {
      Object.entries(replacements).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, String(v));
      });
    }
    return text;
  };
  
  const [sources, setSources] = useState<ChannelSource[]>([]);
  const [messages, setMessages] = useState<CaughtMessage[]>([]);
  
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  
  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [newKeyword, setNewKeyword] = useState("");
  const [keywordMode, setKeywordMode] = useState<"semantic" | "exact_phrase" | "exact_word" | "exclude">("semantic");

  const [newSourceLink, setNewSourceLink] = useState("");
  const [promocode, setPromocode] = useState("");
  
  const [digestPeriod, setDigestPeriod] = useState<number>(1);
  const [selectedDigestSources, setSelectedDigestSources] = useState<number[]>([]);
  const [digestText, setDigestText] = useState("");
  const [digestLoading, setDigestLoading] = useState(false);
  const [digestView, setDigestView] = useState<'generate' | 'history' | 'schedule'>('generate');
  const [digestHistory, setDigestHistory] = useState<DigestHistoryItem[]>([]);
  const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null);
  const [scheduleDrafts, setScheduleDrafts] = useState<Record<number, { enabled: boolean; time: string; days: string[] }>>({});

  const getScheduleDraft = (src: any) => {
    if (scheduleDrafts[src.id]) {
      return scheduleDrafts[src.id];
    }
    const enabled = !!src.digest_schedule_time;
    const time = src.digest_schedule_time || "09:00";
    const days = src.digest_schedule_days 
      ? src.digest_schedule_days.split(",").map((d: string) => d.trim().toUpperCase()) 
      : ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"];
    return { enabled, time, days };
  };

  const updateDraft = (channelId: number, fields: Partial<{ enabled: boolean; time: string; days: string[] }>) => {
    setScheduleDrafts(prev => {
      const current = prev[channelId] || (() => {
        const src = sources.find(s => s.id === channelId);
        const enabled = !!src?.digest_schedule_time;
        const time = src?.digest_schedule_time || "09:00";
        const days = src?.digest_schedule_days 
          ? src.digest_schedule_days.split(",").map((d: string) => d.trim().toUpperCase()) 
          : ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"];
        return { enabled, time, days };
      })();
      return {
        ...prev,
        [channelId]: { ...current, ...fields }
      };
    });
  };
  const [isSourcesDeleteMode, setIsSourcesDeleteMode] = useState(false);

  const handleInputFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    const target = e.target;
    setTimeout(() => {
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 300);
  };
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [adminView, setAdminView] = useState<'dashboard' | 'users' | 'pro' | 'promos'>('dashboard');
  const [adminStats, setAdminStats] = useState<any>(null);
  const [adminPromocodes, setAdminPromocodes] = useState<any[]>([]);
  const [adminUsers, setAdminUsers] = useState<any[]>([]);
  const [adminUserDetails, setAdminUserDetails] = useState<any>(null);
  const [adminSearch, setAdminSearch] = useState("");
  
  const [newPromoCode, setNewPromoCode] = useState("");
  const [newPromoDuration, setNewPromoDuration] = useState(30);
  const [newPromoMaxAct, setNewPromoMaxAct] = useState(1);

  const [showBuyProModal, setShowBuyProModal] = useState(false);
  const [showDocModal, setShowDocModal] = useState(false);
  const [proTooltipVisible, setProTooltipVisible] = useState(false);
  const [banConfirmModal, setBanConfirmModal] = useState<number | null>(null);
  const [showManageProModal, setShowManageProModal] = useState<number | null>(null);
  const [proDaysInput, setProDaysInput] = useState<number>(30);

  const DEV_MOCK_INIT_DATA = "mock_658350287";
  const authHeader = tg?.initData ? tg.initData : DEV_MOCK_INIT_DATA;

  useEffect(() => {
    if (tg) { tg.ready(); tg.expand(); }
  }, [tg]);

  const loadProfile = async (silent = false) => {
    try {
      if (!silent) setIsLoading(true);
      const res = await fetch(`${API_BASE}/user/me`, { headers: { "Authorization": `tma ${authHeader}` } });
      if (!res.ok) throw new Error("Ошибка авторизации.");
      const data = await res.json();
      setUser(data);
      setErrorMsg(null);
    } catch (e: any) {
      showError(e.message);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => { loadProfile(); }, [authHeader]);

  useEffect(() => {
    if (activeTab !== 'digest' || digestView !== 'history') {
      setExpandedHistoryId(null);
    }
  }, [activeTab, digestView]);

  const showError = (msg: string) => {
    setErrorMsg(msg);
    setTimeout(() => setErrorMsg(null), 3500);
  };

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(null), 3500);
  };

  const prevTabRef = useRef(activeTab);

  useEffect(() => {
    if (!user) return;
    if (activeTab === 'dashboard') {
      fetchMessages();
      fetchSources();
    }
    else if (activeTab === 'sources') {
      fetchSources();
      if (prevTabRef.current !== 'sources') {
        setSelectedSourceId(null);
      }
    }
    else if (activeTab === 'digest') { fetchSources(); if (digestView === 'history') fetchDigestHistory(); }
    else if (activeTab === 'admin' && user?.is_admin) fetchAdminData();
    prevTabRef.current = activeTab;
  }, [activeTab, user?.telegram_id, digestView]);

  const fetchMessages = async () => {
    try {
      const res = await fetch(`${API_BASE}/messages`, { headers: { "Authorization": `tma ${authHeader}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setMessages(data);
    } catch (e: any) { showError(e.message); }
  };

  const fetchSources = async () => {
    try {
      const res = await fetch(`${API_BASE}/sources`, { headers: { "Authorization": `tma ${authHeader}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSources(data);
    } catch (e: any) { showError(e.message); }
  };

  const addSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceLink.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/sources`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ link: newSourceLink })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      setNewSourceLink("");
      fetchSources();
    } catch (e: any) { showError(e.message); }
  };

  const deleteSource = async (id: number) => {
    if (!window.confirm("Вы уверены, что хотите удалить этот источник?")) return;
    try {
      const res = await fetch(`${API_BASE}/sources/${id}`, { method: "DELETE", headers: { "Authorization": `tma ${authHeader}` } });
      if (!res.ok) throw new Error("Не удалось удалить источник.");
      fetchSources();
      if (selectedSourceId === id) setSelectedSourceId(null);
    } catch (e: any) { showError(e.message); }
  };

  const fetchKeywords = async (chanId: number) => {
    try {
      const res = await fetch(`${API_BASE}/sources/${chanId}/keywords`, { headers: { "Authorization": `tma ${authHeader}` } });
      setKeywords(await res.json());
    } catch (e: any) { showError(e.message); }
  };

  const selectSource = (id: number) => {
    if (selectedSourceId === id) setSelectedSourceId(null);
    else { setSelectedSourceId(id); fetchKeywords(id); }
  };

  const addKeyword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyword.trim() || selectedSourceId === null) return;
    try {
      const res = await fetch(`${API_BASE}/sources/${selectedSourceId}/keywords`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ keyword: newKeyword.trim(), mode: keywordMode })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      setNewKeyword("");
      fetchKeywords(selectedSourceId);
      loadProfile(true);
    } catch (e: any) { showError(e.message); }
  };

  const deleteKeyword = async (id: number) => {
    try {
      await fetch(`${API_BASE}/keywords/${id}`, { method: "DELETE", headers: { "Authorization": `tma ${authHeader}` } });
      if (selectedSourceId) { fetchKeywords(selectedSourceId); loadProfile(true); }
    } catch (e: any) { showError(e.message); }
  };

  const updateSourceSchedule = async (channelId: number, time: string | null, days: string[] | null) => {
    try {
      const daysStr = days ? days.join(",") : null;
      const res = await fetch(`${API_BASE}/sources/${channelId}/schedule`, {
        method: "POST",
        headers: { 
          "Authorization": `tma ${authHeader}`, 
          "Content-Type": "application/json" 
        },
        body: JSON.stringify({ time, days: daysStr })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setSources(prev => prev.map(s => s.id === channelId ? { 
        ...s, 
        digest_schedule_time: time,
        digest_schedule_days: daysStr
      } : s));
      showSuccess(isRu ? "Настройки рассылки сохранены" : "Newsletter settings saved");
    } catch (e: any) { 
      showError(e.message); 
    }
  };

  const activatePromo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promocode.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/user/activate-promo`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ code: promocode.trim() })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setUser(data);
      setPromocode("");
      showSuccess("Статус PRO успешно активирован.");
    } catch (e: any) { showError(e.message); }
  };

  const buyPro = () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    fetch(`${API_BASE}/user/buy-pro`, {
      method: "POST",
      headers: { "Authorization": `tma ${authHeader}` }
    })
    .then(async res => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      showSuccess(data.message);
      setShowBuyProModal(false);
      if (tg) tg.showAlert(data.message);
    })
    .catch(e => { showError(e.message); });
  };

  const fetchDigestHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/digest/history`, { headers: { "Authorization": `tma ${authHeader}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setDigestHistory(data);
    } catch (e: any) { showError(e.message); }
  };

  const deleteDigestHistoryItem = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/digest/history/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `tma ${authHeader}` }
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      setDigestHistory(prev => prev.filter(h => h.id !== id));
    } catch (e: any) { showError(e.message); }
  };

  const toggleExpand = (id: number) => {
    setExpandedHistoryId(prev => {
      const isExpanding = prev !== id;
      const nextVal = isExpanding ? id : null;
      if (isExpanding) {
        setTimeout(() => {
          const element = document.getElementById(`history-card-${id}`);
          if (element) {
            const headerOffset = 16;
            const elementPosition = element.getBoundingClientRect().top;
            const offsetPosition = elementPosition + window.pageYOffset - headerOffset;
            window.scrollTo({
              top: offsetPosition,
              behavior: 'smooth'
            });
          }
        }, 300);
      }
      return nextVal;
    });
  };

  const generateDigest = async () => {
    try {
      setDigestText("");
      setDigestLoading(true);
      const res = await fetch(`${API_BASE}/digest`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ channel_ids: selectedDigestSources, period_hours: digestPeriod, use_keywords_only: false })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setDigestText(data.digest);
      loadProfile();
    } catch (e: any) { showError(e.message); } finally { setDigestLoading(false); }
  };

  const fetchAdminData = async () => {
    try {
      const [resStats, resPromos, resUsers] = await Promise.all([
        fetch(`${API_BASE}/admin/stats`, { headers: { "Authorization": `tma ${authHeader}` } }),
        fetch(`${API_BASE}/admin/promocodes`, { headers: { "Authorization": `tma ${authHeader}` } }),
        fetch(`${API_BASE}/admin/users`, { headers: { "Authorization": `tma ${authHeader}` } })
      ]);
      if (resStats.ok) setAdminStats(await resStats.json());
      if (resPromos.ok) setAdminPromocodes(await resPromos.json());
      if (resUsers.ok) setAdminUsers(await resUsers.json());
    } catch (e: any) { showError(e.message); }
  };

  const generateRandomPromo = () => {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let code = "XXXX-";
    for (let i = 0; i < 8; i++) {
      if (i === 4) code += "-";
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setNewPromoCode(code);
  };

  const createPromoAdmin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPromoCode.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/admin/create-promo`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ code: newPromoCode.trim(), duration_days: newPromoDuration, max_activations: newPromoMaxAct })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setNewPromoCode("");
      showSuccess(`Промокод ${data.code} создан`);
      fetchAdminData();
    } catch (e: any) { showError(e.message); }
  };

  const deletePromoAdmin = async (code: string) => {
    if (!window.confirm(`Удалить промокод ${code}?`)) return;
    try {
      const res = await fetch(`${API_BASE}/admin/promocodes/${code}`, {
        method: "DELETE",
        headers: { "Authorization": `tma ${authHeader}` }
      });
      if (!res.ok) throw new Error("Не удалось удалить промокод.");
      fetchAdminData();
    } catch (e: any) { showError(e.message); }
  };

  const openUserDetails = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/admin/users/${id}`, { headers: { "Authorization": `tma ${authHeader}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setAdminUserDetails(data);
    } catch (e: any) { showError(e.message); }
  };

  const banUser = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/admin/users/${id}/ban`, { method: "POST", headers: { "Authorization": `tma ${authHeader}` } });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setBanConfirmModal(null);
      openUserDetails(id);
      fetchAdminData();
    } catch (e: any) { showError(e.message); }
  };

  const grantPro = async (id: number, days: number) => {
    try {
      const res = await fetch(`${API_BASE}/admin/users/${id}/pro`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}`, "Content-Type": "application/json" },
        body: JSON.stringify({ days })
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      setShowManageProModal(null);
      openUserDetails(id);
      fetchAdminData();
      showSuccess(days > 0 ? `Подписка выдана на ${days} дней` : "Подписка удалена");
    } catch (e: any) { showError(e.message); }
  };

  const resetCooldown = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE}/admin/users/${id}/reset-cooldown`, {
        method: "POST",
        headers: { "Authorization": `tma ${authHeader}` }
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      showSuccess(isRu ? "Лимит генерации сброшен" : "Digest cooldown reset successfully");
    } catch (e: any) { showError(e.message); }
  };

  const handleProBadgeClick = () => {
    if (user?.is_pro) {
      setProTooltipVisible(true);
      setTimeout(() => setProTooltipVisible(false), 3000);
    } else {
      setShowBuyProModal(true);
    }
  };

  const toggleDigestSource = (id: number) => {
    setSelectedDigestSources(prev => 
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const sortedMessages = useMemo(() => {
    return [...messages].sort((a, b) => {
      const timeA = new Date(a.created_at).getTime();
      const timeB = new Date(b.created_at).getTime();
      return sortOrder === 'desc' ? timeB - timeA : timeA - timeB;
    });
  }, [messages, sortOrder]);

  const filteredAdminUsers = useMemo(() => {
    if (!adminSearch.trim()) return adminUsers;
    const lower = adminSearch.toLowerCase();
    return adminUsers.filter(u => 
      u.telegram_id.toString().includes(lower) || 
      (u.username && u.username.toLowerCase().includes(lower))
    );
  }, [adminUsers, adminSearch]);

  const proUsersList = useMemo(() => {
    return filteredAdminUsers.filter(u => u.is_pro);
  }, [filteredAdminUsers]);

  const SVGChart = ({ data }: { data: number[] }) => {
    const maxVal = Math.max(...data, 1);
    const height = 80;
    const width = 300;
    const points = data.map((val, i) => `${(i / (data.length - 1)) * width},${height - (val / maxVal) * height}`);
    const polyPoints = `0,${height} ${points.join(' ')} ${width},${height}`;

    return (
      <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.8" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={polyPoints} className="chart-gradient-fill" />
        <polyline points={points.join(' ')} className="chart-line" />
      </svg>
    );
  };

  if (isLoading && !user) {
    return (
      <div className="loader-wrapper">
        <motion.div 
          animate={{ rotate: 360 }} 
          transition={{ repeat: Infinity, ease: "linear", duration: 1 }}
          style={{ width: 24, height: 24, border: '2px solid var(--border-subtle)', borderTopColor: 'var(--accent)', borderRadius: '50%' }}
        />
      </div>
    );
  }

  const getPageTitle = () => {
    if (activeTab === 'admin') return t('admin');
    const titles: Record<string, string> = { 
      dashboard: t('dashboard'), 
      digest: t('digest'), 
      sources: t('sources'), 
      settings: t('settings'), 
      info: t('info'), 
      admin: "" 
    };
    return titles[activeTab] || "";
  };

  return (
    <div className="app-layout">
      <div className="toast-container">
        <AnimatePresence>
          {errorMsg && (
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="toast toast-error">
              <WarningCircle size={18} weight="fill" className="toast-icon" />
              <span>{errorMsg}</span>
            </motion.div>
          )}
          {successMsg && (
            <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="toast toast-success">
              <CheckCircle size={18} weight="fill" className="toast-icon" />
              <span>{successMsg}</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <header className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">{getPageTitle()}</h1>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {user?.is_admin && (
            <button 
              className="btn btn-secondary" 
              style={{ 
                height: '32px', 
                width: '32px', 
                borderRadius: '8px', 
                padding: 0, 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center' 
              }} 
              onClick={() => { setActiveTab('admin'); setAdminView('dashboard'); }}
            >
              <ShieldCheck size={20} weight={activeTab === 'admin' ? "fill" : "regular"} color={activeTab === 'admin' ? 'var(--accent)' : 'var(--text-primary)'} />
            </button>
          )}
          
          <div style={{ position: 'relative' }}>
            <div 
              className={`badge ${user?.is_pro ? 'badge-pro' : 'badge-free'}`} 
              onClick={handleProBadgeClick}
              style={{ 
                cursor: 'pointer', 
                transition: 'all 0.2s', 
                userSelect: 'none', 
                height: '32px', 
                borderRadius: '8px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                minWidth: '60px' 
              }}
            >
              {user?.is_pro ? "PRO" : "FREE"}
            </div>
            
            <AnimatePresence>
              {proTooltipVisible && user?.is_pro && (
                <motion.div 
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  style={{
                    position: 'absolute',
                    top: 'calc(100% + 8px)',
                    right: 0,
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                    zIndex: 50,
                    whiteSpace: 'nowrap',
                    fontSize: '13px',
                    color: 'var(--text-secondary)'
                  }}
                >
                  {user.is_admin ? t('status_lifetime') : `${isRu ? 'До' : 'Until'}: ${user.pro_expires_at ? new Date(user.pro_expires_at).toLocaleDateString() : '?'}`}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </header>

      <main style={{ flex: 1, paddingBottom: '90px' }}>
        <AnimatePresence mode="wait">
          <motion.div 
            key={activeTab + (activeTab === 'admin' ? adminView : '')}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {/* ─── DASHBOARD ─── */}
            {activeTab === 'dashboard' && (
              <div>
                <div className="bento-grid" style={{ marginBottom: 12 }}>
                  <div className="bento-cell" style={{ padding: '16px', alignItems: 'flex-start', background: 'transparent' }}>
                    <span className="metric-label" style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-tertiary)' }}>{t('collected')}</span>
                    <span className="metric-value" style={{ fontSize: '24px', fontWeight: 400 }}>{messages.length}</span>
                  </div>
                  <div 
                    className="bento-cell" 
                    style={{ padding: '16px', alignItems: 'flex-start', background: 'transparent', cursor: 'pointer' }}
                    onClick={() => setActiveTab('sources')}
                  >
                    <span className="metric-label" style={{ fontSize: '12px', fontWeight: 500, color: 'var(--text-tertiary)' }}>{t('sources_count')}</span>
                    <span className="metric-value" style={{ fontSize: '24px', fontWeight: 400 }}>{sources.length}</span>
                  </div>
                </div>

                <div className="flex justify-between items-center mb-2" style={{ padding: '0 20px' }}>
                  <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{t('feed_title')}</span>
                  <button 
                    className="flex gap-1 items-center" 
                    style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 13 }}
                    onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                  >
                    {sortOrder === 'desc' ? <SortDescending size={16} /> : <SortAscending size={16} />}
                    {sortOrder === 'desc' ? t('sort_desc') : t('sort_asc')}
                  </button>
                </div>

                <div className="list-container">
                  {sortedMessages.length === 0 ? (
                    <div className="empty-state">{t('empty_feed')}</div>
                  ) : (
                    sortedMessages.map((msg, i) => (
                      <motion.div 
                        initial={{ opacity: 0, x: -10 }} 
                        animate={{ opacity: 1, x: 0 }} 
                        transition={{ delay: i * 0.05 }}
                        className="feed-item" 
                        key={msg.id}
                      >
                        <div className="feed-meta">
                          <span className="feed-source">{msg.channel_title || `@${msg.channel_username}`}</span>
                          <span className="feed-time">{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                        <div className="feed-text">{msg.text}</div>
                        <div>
                          <a href={msg.url} target="_blank" rel="noopener noreferrer" className="link-subtle">
                            {t('go_to_source')} <ArrowUpRight size={14} />
                          </a>
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* ─── DIGEST ─── */}
            {activeTab === 'digest' && (
              <div className="list-container" style={{ marginTop: 0 }}>
                {!user?.is_pro ? (
                  <div className="bento-cell" style={{ alignItems: 'center', textAlign: 'center', padding: '40px 16px' }}>
                    <LockKey size={32} color="var(--text-secondary)" weight="duotone" />
                    <h2 style={{ fontSize: '20px', fontWeight: 500, margin: '16px 0 8px' }}>{t('pro_feature_title')}</h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '24px' }}>{t('pro_feature_desc')}</p>
                    <button className="btn btn-primary" onClick={() => setShowBuyProModal(true)}>{t('activate_pro_btn')}</button>
                  </div>
                ) : (
                  <div className="flex flex-col gap-3">
                    <div className="segmented-control">
                      <button 
                        className={`segmented-btn ${digestView === 'generate' ? 'active' : ''}`}
                        onClick={() => setDigestView('generate')}
                      >
                        {t('new_digest_tab')}
                      </button>
                      <button 
                        className={`segmented-btn ${digestView === 'history' ? 'active' : ''}`}
                        onClick={() => { setDigestView('history'); fetchDigestHistory(); }}
                      >
                        {t('history_tab')}
                      </button>
                      <button 
                        className={`segmented-btn ${digestView === 'schedule' ? 'active' : ''}`}
                        onClick={() => setDigestView('schedule')}
                      >
                        {isRu ? "Рассылка" : "Newsletter"}
                      </button>
                    </div>

                    {digestView === 'generate' && (
                      <>
                        <div className="bento-cell">
                          <span className="label" style={{ marginBottom: '16px', fontWeight: 700, fontSize: '15px', color: 'var(--text-primary)', letterSpacing: '0.03em', display: 'block' }}>{t('manual_generation')}</span>
                          
                          {sources.length > 0 && (
                            <div style={{ marginBottom: 20 }}>
                              <div className="flex flex-col gap-0.5" style={{ marginBottom: '8px' }}>
                                <span className="label" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                  {isRu ? "ИСТОЧНИКИ" : "SOURCES"}
                                </span>
                                <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                                  {isRu ? "(все, если не выбраны):" : "(all if none selected):"}
                                </span>
                              </div>
                              <div className="flex flex-col gap-1 mt-2" style={{ maxHeight: 150, overflowY: 'auto' }}>
                                {sources.map(s => {
                                  const isSelected = selectedDigestSources.includes(s.id);
                                  return (
                                    <div 
                                      key={s.id} 
                                      className="flex items-center justify-between p-2.5 rounded-lg cursor-pointer hover:bg-white/5 transition-colors border border-transparent"
                                      onClick={() => toggleDigestSource(s.id)}
                                      style={{
                                        backgroundColor: isSelected ? 'rgba(198, 244, 50, 0.03)' : 'transparent',
                                        borderColor: isSelected ? 'rgba(198, 244, 50, 0.15)' : 'transparent'
                                      }}
                                    >
                                      <span style={{ fontSize: 14, color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                                        {s.title || `@${s.username}`}
                                      </span>
                                      {isSelected ? (
                                        <div 
                                          style={{
                                            width: '20px',
                                            height: '20px',
                                            borderRadius: '6px',
                                            border: '2px solid',
                                            borderColor: 'var(--accent)',
                                            backgroundColor: 'var(--accent)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            transition: 'all 0.25s ease',
                                            flexShrink: 0
                                          }}
                                        >
                                          <svg width="12" height="10" viewBox="0 0 12 10" fill="none" xmlns="http://www.w3.org/2000/svg">
                                            <path d="M2 5L4.5 7.5L10 2" stroke="var(--bg-canvas)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                                          </svg>
                                        </div>
                                      ) : (
                                        <div 
                                          style={{
                                            width: '20px',
                                            height: '20px',
                                            borderRadius: '6px',
                                            border: '2px solid',
                                            borderColor: 'var(--text-tertiary)',
                                            backgroundColor: 'transparent',
                                            transition: 'all 0.25s ease',
                                            flexShrink: 0
                                          }}
                                        />
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          <div className="flex flex-col gap-2 mb-6" style={{ alignItems: 'stretch' }}>
                            <div className="flex flex-col gap-0.5">
                              <span className="label" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                {isRu ? "ПЕРИОД" : "PERIOD"}
                              </span>
                              <span style={{ fontSize: '11px', color: 'var(--text-tertiary)' }}>
                                {isRu ? "(в часах):" : "(hours):"}
                              </span>
                            </div>
                            <div className="segmented-control w-full">
                              {[1, 3, 6, 12, 24].map(h => (
                                <button 
                                  key={h} 
                                  className={`segmented-btn ${digestPeriod === h ? 'active' : ''}`}
                                  onClick={() => setDigestPeriod(h)}
                                >
                                  {h}
                                </button>
                              ))}
                            </div>
                          </div>

                          <button className="btn btn-primary w-full" style={{ padding: '12px' }} onClick={generateDigest} disabled={digestLoading}>
                            <Sparkle size={18} />
                            {digestLoading ? t('generating_btn') : t('generate_btn')}
                          </button>
                        </div>

                        {(digestText || digestLoading) && (
                          <div className="bento-cell" style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                            {digestLoading ? (
                              <div className="flex flex-col gap-3 opacity-50">
                                <div style={{ height: '12px', background: 'var(--border-subtle)', width: '100%', borderRadius: '4px' }} />
                                <div style={{ height: '12px', background: 'var(--border-subtle)', width: '80%', borderRadius: '4px' }} />
                                <div style={{ height: '12px', background: 'var(--border-subtle)', width: '90%', borderRadius: '4px' }} />
                              </div>
                            ) : (
                              <div style={{ fontSize: 14 }}>{digestText}</div>
                            )}
                          </div>
                        )}
                      </>
                    )}

                    {digestView === 'history' && (
                      <div className="flex flex-col gap-3">
                        {digestHistory.length === 0 ? (
                          <div className="empty-state">{t('history_empty')}</div>
                        ) : (
                          digestHistory.map(h => (
                            <div key={h.id} id={`history-card-${h.id}`} className="bento-cell" style={{ position: 'relative' }}>
                              <div 
                                className="flex justify-between items-center mb-3 border-b border-white/10 pb-2"
                                style={{ cursor: 'pointer' }}
                                onClick={() => toggleExpand(h.id)}
                              >
                                <div className="flex flex-col">
                                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', fontWeight: 600 }}>{t('digest_period_hours', { hours: h.period_hours })}</span>
                                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 2 }}>{new Date(h.created_at).toLocaleString()}</span>
                                </div>
                                <button
                                  className="btn"
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    color: 'var(--text-tertiary)',
                                    padding: '4px',
                                    cursor: 'pointer',
                                    borderRadius: '6px',
                                    transition: 'color 0.2s, background 0.2s',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center'
                                  }}
                                  onClick={(e) => { e.stopPropagation(); deleteDigestHistoryItem(h.id); }}
                                  onMouseEnter={e => { (e.target as HTMLElement).style.color = 'var(--danger)'; (e.target as HTMLElement).style.background = 'var(--danger-faint)'; }}
                                  onMouseLeave={e => { (e.target as HTMLElement).style.color = 'var(--text-tertiary)'; (e.target as HTMLElement).style.background = 'transparent'; }}
                                  title={isRu ? 'Удалить' : 'Delete'}
                                >
                                  <Trash size={14} />
                                </button>
                              </div>
                              
                              <div style={{ position: 'relative' }}>
                                <motion.div
                                  initial={false}
                                  animate={{ height: expandedHistoryId === h.id ? 'auto' : 112 }}
                                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                                  style={{ overflow: 'hidden', position: 'relative' }}
                                >
                                  <div style={{ fontSize: 14, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                                    {h.text}
                                  </div>
                                  {expandedHistoryId !== h.id && (
                                    <div style={{
                                      position: 'absolute',
                                      bottom: 0,
                                      left: 0,
                                      right: 0,
                                      height: '40px',
                                      background: 'linear-gradient(to bottom, transparent, var(--bg-canvas))',
                                      pointerEvents: 'none'
                                    }} />
                                  )}
                                </motion.div>
                                
                                <div style={{
                                  display: 'flex',
                                  justifyContent: 'flex-end',
                                  marginTop: expandedHistoryId === h.id ? '12px' : '4px',
                                  position: expandedHistoryId === h.id ? 'relative' : 'absolute',
                                  bottom: expandedHistoryId === h.id ? 'auto' : '4px',
                                  right: expandedHistoryId === h.id ? 'auto' : '4px',
                                  zIndex: 10
                                }}>
                                  <button 
                                    onClick={(e) => { e.stopPropagation(); toggleExpand(h.id); }}
                                    style={{
                                      background: 'rgba(255, 255, 255, 0.1)',
                                      backdropFilter: 'blur(4px)',
                                      border: '1px solid rgba(255, 255, 255, 0.1)',
                                      borderRadius: '50%',
                                      width: '24px',
                                      height: '24px',
                                      display: 'flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      color: 'var(--text-primary)',
                                      cursor: 'pointer',
                                      boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
                                      transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255, 255, 255, 0.2)'; }}
                                    onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255, 255, 255, 0.1)'; }}
                                  >
                                    {expandedHistoryId === h.id ? <CaretUp size={14} /> : <CaretDown size={14} />}
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    )}

                    {digestView === 'schedule' && (
                      <div className="flex flex-col gap-3">
                        {sources.length === 0 ? (
                          <div className="empty-state">{t('empty_sources')}</div>
                        ) : (
                          sources.map(src => {
                            const draft = getScheduleDraft(src);
                            return (
                              <div key={src.id} className="bento-cell" style={{ display: 'flex', flexDirection: 'column' }}>
                                <div className="flex justify-between items-center py-1">
                                  <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)' }}>
                                    {src.title || `@${src.username}`}
                                  </span>
                                  
                                  <div 
                                    onClick={() => {
                                      if (!user?.is_pro) {
                                        setShowBuyProModal(true);
                                        return;
                                      }
                                      if (draft.enabled) {
                                        updateDraft(src.id, { enabled: false });
                                        updateSourceSchedule(src.id, null, null);
                                      } else {
                                        updateDraft(src.id, { enabled: true });
                                      }
                                    }}
                                    style={{
                                      width: '46px',
                                      height: '26px',
                                      backgroundColor: draft.enabled ? 'var(--accent)' : 'rgba(255,255,255,0.08)',
                                      borderRadius: '13px',
                                      position: 'relative',
                                      cursor: 'pointer',
                                      transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                                      border: '1px solid',
                                      borderColor: draft.enabled ? 'var(--accent)' : 'var(--border-subtle)',
                                      flexShrink: 0
                                    }}
                                  >
                                    <div 
                                      style={{
                                        width: '20px',
                                        height: '20px',
                                        backgroundColor: draft.enabled ? '#0B0D14' : '#FFFFFF',
                                        borderRadius: '50%',
                                        position: 'absolute',
                                        top: '2px',
                                        left: draft.enabled ? '22px' : '2px',
                                        transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
                                        boxShadow: '0 1px 3px rgba(0,0,0,0.4)'
                                      }}
                                    />
                                  </div>
                                </div>

                                <AnimatePresence>
                                  {draft.enabled && (
                                    <motion.div 
                                      initial={{ height: 0, opacity: 0 }} 
                                      animate={{ height: 'auto', opacity: 1 }} 
                                      exit={{ height: 0, opacity: 0 }} 
                                      style={{ overflow: 'hidden' }}
                                    >
                                      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: '8px', marginBottom: '12px', lineHeight: '1.4' }}>
                                        {t('daily_digest_desc')}
                                      </p>
                                      
                                      <div style={{ marginBottom: '12px', width: '100%' }}>
                                        <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                                          {isRu ? "Дни недели:" : "Days of the week:"}
                                        </span>
                                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '6px', width: '100%', justifyItems: 'stretch' }}>
                                          {["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"].map(day => {
                                            const isSelected = draft.days.includes(day);
                                            return (
                                              <button
                                                key={day}
                                                onClick={() => {
                                                  const nextDays = isSelected
                                                    ? draft.days.filter((d: string) => d !== day)
                                                    : [...draft.days, day];
                                                  updateDraft(src.id, { days: nextDays });
                                                }}
                                                style={{
                                                  padding: '8px 0',
                                                  width: '100%',
                                                  display: 'block',
                                                  textAlign: 'center',
                                                  borderRadius: '6px',
                                                  fontSize: '11px',
                                                  fontWeight: 600,
                                                  border: '1px solid',
                                                  borderColor: isSelected ? 'var(--accent)' : 'var(--border-subtle)',
                                                  backgroundColor: isSelected ? 'var(--accent)' : 'rgba(255,255,255,0.04)',
                                                  color: isSelected ? 'var(--bg-canvas)' : 'var(--text-secondary)',
                                                  cursor: 'pointer',
                                                  transition: 'all 0.15s ease'
                                                }}
                                              >
                                                {day}
                                              </button>
                                            );
                                          })}
                                        </div>
                                      </div>

                                      <div className="flex justify-between items-center bg-white/5 p-3 rounded-lg mb-3">
                                        <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{t('time_msk')}</span>
                                        <select 
                                          className="input" 
                                          style={{ width: '100px', height: '36px', padding: '0 10px', fontSize: 13, borderRadius: '6px' }} 
                                          value={draft.time} 
                                          onChange={e => updateDraft(src.id, { time: e.target.value })}
                                        >
                                          {Array.from({ length: 24 }).map((_, i) => {
                                            const hr = i.toString().padStart(2, '0') + ":00";
                                            return <option key={hr} value={hr}>{hr}</option>;
                                          })}
                                        </select>
                                      </div>

                                      <button
                                        onClick={() => updateSourceSchedule(src.id, draft.time, draft.days)}
                                        className="btn btn-primary w-full"
                                        style={{ padding: '8px 12px', fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                                      >
                                        <Sparkle size={14} />
                                        {isRu ? "Сохранить" : "Save settings"}
                                      </button>
                                    </motion.div>
                                  )}
                                </AnimatePresence>
                              </div>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* ─── SOURCES ─── */}
            {activeTab === 'sources' && (
              <div className="list-container" style={{ marginTop: 0 }}>
                <form onSubmit={addSource} className="input-group">
                  <span className="label">{t('add_source_title')}</span>
                  <div className="input-with-action">
                    <input className="input" placeholder={t('placeholder_source')} value={newSourceLink} onChange={e => setNewSourceLink(e.target.value)} onFocus={handleInputFocus} />
                    <button className="btn btn-primary" type="submit"><Plus size={16} /></button>
                  </div>
                </form>

                <div className="mt-4">
                  {sources.length > 0 && (
                    <div className="flex justify-end mb-2">
                      <button 
                        className="btn" 
                        style={{ 
                          padding: '4px 12px', 
                          fontSize: 12, 
                          height: '28px', 
                          background: isSourcesDeleteMode ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255,255,255,0.05)',
                          color: isSourcesDeleteMode ? 'var(--danger)' : 'var(--text-secondary)',
                          border: '1px solid',
                          borderColor: isSourcesDeleteMode ? 'rgba(239, 68, 68, 0.2)' : 'var(--border-subtle)',
                          borderRadius: '6px'
                        }}
                        onClick={() => setIsSourcesDeleteMode(!isSourcesDeleteMode)}
                      >
                        {isSourcesDeleteMode 
                          ? (isRu ? "Готово" : "Done") 
                          : (isRu ? "Редактировать" : "Edit")
                        }
                      </button>
                    </div>
                  )}
                  {sources.length === 0 ? (
                    <div className="empty-state">{t('empty_sources')}</div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {sources.map(src => (
                        <div key={src.id} className="flex flex-col gap-3">
                          <div 
                            className={`source-row ${selectedSourceId === src.id ? 'active' : ''}`} 
                            style={{ cursor: isSourcesDeleteMode ? 'default' : 'pointer' }}
                            onClick={() => { if (!isSourcesDeleteMode) selectSource(src.id); }}
                          >
                            <div className="source-info">
                              <span className="source-name">@{src.username}</span>
                              <span className="source-desc">{src.title || (isRu ? "Telegram канал" : "Telegram Channel")}</span>
                            </div>
                            <div className="flex gap-2">
                              {isSourcesDeleteMode ? (
                                <button 
                                  className="btn btn-danger" 
                                  style={{ 
                                    height: '32px', 
                                    width: '32px', 
                                    borderRadius: '8px', 
                                    padding: 0, 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justifyContent: 'center',
                                    flexShrink: 0
                                  }} 
                                  onClick={(e) => { e.stopPropagation(); deleteSource(src.id); }}
                                >
                                  <Trash size={16} />
                                </button>
                              ) : (
                                <button 
                                  className="btn btn-secondary" 
                                  style={{ 
                                    height: '32px', 
                                    width: '32px', 
                                    borderRadius: '8px', 
                                    padding: 0, 
                                    display: 'flex', 
                                    alignItems: 'center', 
                                    justifyContent: 'center',
                                    flexShrink: 0
                                  }}
                                >
                                  <Faders size={16} color={selectedSourceId === src.id ? 'var(--text-primary)' : 'var(--text-secondary)'} />
                                </button>
                              )}
                            </div>
                          </div>
                          
                          <AnimatePresence>
                            {selectedSourceId === src.id && (
                              <motion.div 
                                initial={{ height: 0, opacity: 0 }} 
                                animate={{ height: 'auto', opacity: 1 }} 
                                exit={{ height: 0, opacity: 0 }} 
                                style={{ overflow: 'hidden' }}
                              >
                                <div style={{ padding: '12px', borderLeft: '1px solid var(--border-subtle)', marginLeft: '12px' }}>
                                  <form onSubmit={addKeyword} className="input-group" style={{ marginBottom: '12px' }}>
                                    <span className="label" style={{ fontSize: '11px' }}>{t('filters_title')}</span>
                                    <div className="input-with-action">
                                      <input className="input" placeholder={t('placeholder_keywords')} value={newKeyword} onChange={e => setNewKeyword(e.target.value)} onFocus={handleInputFocus} />
                                      <select className="input" style={{ width: '120px' }} value={keywordMode} onChange={e => setKeywordMode(e.target.value as any)}>
                                        <option value="semantic">{t('filter_mode_semantic')}</option>
                                        <option value="exact_phrase">{t('filter_mode_phrase')}</option>
                                        <option value="exact_word">{t('filter_mode_word')}</option>
                                        <option value="exclude">{t('filter_mode_exclude')}</option>
                                      </select>
                                      <button className="btn btn-secondary" type="submit"><Plus size={16} /></button>
                                    </div>
                                  </form>
                                  <div className="tags-row">
                                    {keywords.map(kw => (
                                      <div key={kw.id} className={`tag ${kw.mode}`}>
                                        <span>{kw.mode === 'exclude' ? '-' : kw.mode === 'exact_word' ? '+' : ''}{kw.keyword}</span>
                                        <button className="tag-remove" onClick={() => deleteKeyword(kw.id)}>&times;</button>
                                      </div>
                                    ))}
                                    {keywords.length === 0 && <span style={{ fontSize: '13px', color: 'var(--text-tertiary)' }}>{t('no_filters')}</span>}
                                  </div>
                                </div>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ─── SETTINGS ─── */}
            {activeTab === 'settings' && (
              <div className="list-container" style={{ marginTop: 0, padding: '0 20px' }}>
                <div className="bento-cell">
                  <span className="label" style={{ marginBottom: 16 }}>{t('account_title')}</span>
                  <div className="flex flex-col gap-3">
                    <div className="flex items-center" style={{ justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Telegram ID</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-primary)' }}>{user?.telegram_id}</span>
                    </div>
                    <div style={{ height: 1, background: 'var(--border-subtle)' }} />
                    <div className="flex items-center" style={{ justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{t('subscription_status')}</span>
                      <span style={{ color: user?.is_pro ? 'var(--accent)' : 'var(--text-primary)', fontWeight: 600, fontSize: 14 }}>
                        {user?.is_pro ? (user.is_admin ? t('status_lifetime') : "PRO") : "FREE"}
                      </span>
                    </div>
                    {user?.is_pro && user?.pro_expires_at && !user.is_admin && (
                      <>
                        <div style={{ height: 1, background: 'var(--border-subtle)' }} />
                        <div className="flex items-center" style={{ justifyContent: 'space-between' }}>
                          <span style={{ color: 'var(--text-secondary)', fontSize: 14 }}>{t('user_expires_at')}</span>
                          <span style={{ fontSize: 14, color: 'var(--text-primary)' }}>
                            {new Date(user.pro_expires_at).toLocaleDateString()}
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                <div className="bento-cell" style={{ marginTop: 12 }}>
                  <form onSubmit={activatePromo} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    <span className="label" style={{ margin: 0 }}>{t('activate_code_title')}</span>
                    <div className="input-with-action">
                      <input className="input" placeholder={t('placeholder_promo')} value={promocode} onChange={e => setPromocode(e.target.value)} onFocus={handleInputFocus} />
                      <button className="btn btn-secondary" type="submit">{t('activate_btn')}</button>
                    </div>
                  </form>
                </div>
              </div>
            )}

            {/* ─── INFO TAB ─── */}
            {activeTab === 'info' && (
              <div className="list-container" style={{ marginTop: 0 }}>
                <div className="bento-cell" style={{ padding: '32px 16px', gap: '12px' }}>
                  <div style={{ textAlign: 'center' }}>
                    <h2 style={{ fontSize: '28px', fontWeight: 600, margin: '0 0 4px', color: 'var(--text-primary)' }}>ZR4K</h2>
                    <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--accent)', background: 'var(--accent-faint)', padding: '2px 8px', borderRadius: '12px' }}>1.0 beta</span>
                  </div>
                  
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6, margin: 0, textAlign: 'center' }}>
                    {t('info_desc')}
                  </p>
                  
                  <div className="flex flex-col gap-3" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-subtle)', padding: 16, borderRadius: 12 }}>
                    <div className="flex justify-between items-center">
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('app_developer')}</span>
                      <a 
                        href="https://t.me/the_twok" 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        style={{ 
                          fontFamily: 'var(--font-mono)', 
                          fontSize: 13, 
                          color: 'var(--accent)', 
                          textDecoration: 'none',
                          fontWeight: 500
                        }}
                      >
                        @the_twok
                      </a>
                    </div>
                  </div>
                  
                  <button 
                    className="btn btn-secondary w-full"
                    onClick={() => setShowDocModal(true)}
                  >
                    {t('app_doc_btn')}
                  </button>
                </div>
              </div>
            )}
            
            {/* ─── ADMIN ─── */}
            {activeTab === 'admin' && user?.is_admin && (
              <div className="list-container" style={{ marginTop: 0 }}>
                {adminView === 'dashboard' && (
                  <div className="flex flex-col gap-3">
                    <div className="bento-grid" style={{ padding: 0 }}>
                      <div className="bento-cell cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setAdminView('users')}>
                        <span className="metric-label">{t('admin_users')}</span>
                        <span className="metric-value">{adminStats?.total_users || 0}</span>
                      </div>
                      <div className="bento-cell cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setAdminView('pro')}>
                        <span className="metric-label">{t('admin_pro')}</span>
                        <span className="metric-value">{adminStats?.total_pro || 0}</span>
                      </div>
                      <div className="bento-cell cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setAdminView('promos')}>
                        <span className="metric-label">{t('admin_promos')}</span>
                        <span className="metric-value">{adminPromocodes.length || 0}</span>
                      </div>
                      <div className="bento-cell">
                        <span className="metric-label">{t('admin_channels')}</span>
                        <span className="metric-value">{adminStats?.total_channels || 0}</span>
                      </div>
                    </div>
                    
                    <div className="bento-cell mt-4">
                      <div className="flex items-center gap-2 mb-2">
                        <ChartLineUp size={20} color="var(--accent)" />
                        <span className="label" style={{ margin: 0 }}>{t('admin_income')}</span>
                      </div>
                      <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {(adminStats?.total_income || 0).toLocaleString()} <span style={{ fontSize: 14, color: 'var(--text-tertiary)' }}>{t('admin_income_unit')}</span>
                      </div>
                      <div className="chart-container">
                        <SVGChart data={adminStats?.income_chart_data || [0, 0, 0, 0, 0, 0, 0]} />
                      </div>
                    </div>

                    <div className="bento-cell mt-4" style={{ padding: '16px', gap: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                        <Sparkle size={16} color="var(--accent)" weight="fill" />
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                          {isRu ? 'ИИ — Лимиты и статистика' : 'AI — Limits & Stats'}
                        </span>
                      </div>

                      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                        {['mistral', 'gemini', 'groq'].map(p => {
                          const stats = adminStats?.ai_stats?.[p] || {
                            success_calls: 0, failed_calls: 0,
                            prompt_tokens: 0, completion_tokens: 0, total_tokens: 0,
                            today_success: 0, today_failed: 0,
                            today_prompt: 0, today_completion: 0, today_total: 0
                          };

                          let limitMax = 0;
                          let limitUsed = 0;
                          let limitUnit = '';

                          if (p === 'mistral') {
                            limitMax = 500000; limitUsed = stats.today_total || 0;
                            limitUnit = isRu ? 'токенов/день' : 'tokens/day';
                          } else if (p === 'gemini') {
                            limitMax = 1500; limitUsed = (stats.today_success || 0) + (stats.today_failed || 0);
                            limitUnit = isRu ? 'запросов/день' : 'req/day';
                          } else {
                            limitMax = 14400; limitUsed = (stats.today_success || 0) + (stats.today_failed || 0);
                            limitUnit = isRu ? 'запросов/день' : 'req/day';
                          }

                          const limitRemaining = Math.max(0, limitMax - limitUsed);
                          const pct = Math.max(0, Math.min(100, (limitRemaining / limitMax) * 100));

                          const fmt = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n);

                          const barColor = pct < 15
                            ? '#FF453A'
                            : pct < 50
                            ? '#FF9F0A'
                            : '#C6F432';

                          const dotGlow = pct > 0
                            ? `0 0 6px ${barColor}55`
                            : '0 0 6px #FF453A55';

                          return (
                            <div key={p} style={{
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 10,
                              padding: '12px 14px',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 10
                            }}>
                              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.03em' }}>
                                    {p.toUpperCase()}
                                  </span>
                                  <span style={{
                                    width: 6, height: 6, borderRadius: '50%',
                                    background: barColor,
                                    boxShadow: dotGlow,
                                    display: 'inline-block'
                                  }} />
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--success)', fontSize: 12, fontWeight: 500 }}>
                                    <CheckCircle size={12} weight="fill" />
                                    <span>{stats.success_calls}</span>
                                  </div>
                                  {stats.failed_calls > 0 && (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--danger)', fontSize: 12, fontWeight: 500 }}>
                                      <WarningCircle size={12} weight="fill" />
                                      <span>{stats.failed_calls}</span>
                                    </div>
                                  )}
                                </div>
                              </div>

                              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                <div style={{ height: 4, width: '100%', background: 'rgba(255,255,255,0.06)', borderRadius: 9999, overflow: 'hidden' }}>
                                  <div style={{
                                    height: '100%',
                                    width: `${pct}%`,
                                    background: barColor,
                                    borderRadius: 9999,
                                    transition: 'width 0.6s cubic-bezier(0.16,1,0.3,1)'
                                  }} />
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{limitUnit}</span>
                                  <span style={{ fontSize: 11, fontWeight: 600, color: pct < 15 ? 'var(--danger)' : pct < 50 ? '#FF9F0A' : 'var(--text-secondary)' }}>
                                    {fmt(limitRemaining)} / {fmt(limitMax)} ({pct.toFixed(0)}%)
                                  </span>
                                </div>
                              </div>

                              <div style={{ display: 'flex', gap: 6, paddingTop: 6, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                                {[
                                  { label: isRu ? 'Вход' : 'In', value: stats.prompt_tokens },
                                  { label: isRu ? 'Выход' : 'Out', value: stats.completion_tokens },
                                  { label: 'Total', value: stats.total_tokens }
                                ].map(chip => (
                                  <div key={chip.label} style={{
                                    flex: 1,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    gap: 2,
                                    background: 'rgba(255,255,255,0.03)',
                                    borderRadius: 7,
                                    padding: '5px 4px'
                                  }}>
                                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)', fontWeight: 500 }}>{chip.label}</span>
                                    <span style={{ fontSize: 12, color: 'var(--text-primary)', fontWeight: 600 }}>{fmt(chip.value)}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {(adminView === 'users' || adminView === 'pro') && (
                  <div className="bento-cell" style={{ padding: 16 }}>
                    <div className="flex items-center gap-4 mb-4">
                      <button className="btn btn-secondary" style={{ padding: 6 }} onClick={() => setAdminView('dashboard')}>
                        <CaretLeft size={20} />
                      </button>
                      <span className="label" style={{ margin: 0 }}>
                        {adminView === 'users' ? t('admin_users') : t('admin_pro')}
                      </span>
                    </div>
                    <div className="search-bar-container">
                      <MagnifyingGlass size={16} />
                      <input className="input" placeholder={t('admin_search_placeholder')} value={adminSearch} onChange={e => setAdminSearch(e.target.value)} onFocus={handleInputFocus} />
                    </div>
                    <div style={{ maxHeight: 400, overflowY: 'auto' }} className="flex flex-col gap-2">
                      {(adminView === 'users' ? filteredAdminUsers : proUsersList).map(u => (
                        <div key={u.telegram_id} 
                             className="source-row" 
                             style={u.telegram_id === user?.telegram_id ? {
                               border: '1px solid rgba(253, 224, 71, 0.4)',
                               background: 'linear-gradient(90deg, rgba(253, 224, 71, 0.08) 0%, rgba(253, 224, 71, 0.02) 100%)',
                               boxShadow: '0 0 10px rgba(253, 224, 71, 0.1)'
                             } : {}}
                             onClick={() => openUserDetails(u.telegram_id)}>
                          <div className="source-info" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span className="source-name" style={{ color: u.is_banned ? 'var(--danger)' : u.telegram_id === user?.telegram_id ? '#fde047' : 'var(--text-primary)', fontWeight: u.telegram_id === user?.telegram_id ? 'bold' : 'normal' }}>
                              {u.username ? `@${u.username}` : u.telegram_id}
                            </span>
                            {u.telegram_id === user?.telegram_id && (
                              <span style={{
                                fontSize: '10px',
                                background: 'rgba(253, 224, 71, 0.15)',
                                color: '#fde047',
                                padding: '2px 6px',
                                borderRadius: '12px',
                                border: '1px solid rgba(253, 224, 71, 0.3)',
                                fontWeight: 600,
                                textTransform: 'uppercase',
                                letterSpacing: '0.5px'
                              }}>
                                {isRu ? "Создатель" : "Owner"}
                              </span>
                            )}
                          </div>
                          <div className="flex gap-2">
                            {u.is_pro && <Crown size={16} color="var(--accent)" />}
                            {u.is_banned && <Prohibit size={16} color="var(--danger)" />}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {adminView === 'promos' && (
                  <div className="bento-cell" style={{ padding: 16 }}>
                    <div className="flex items-center gap-4 mb-4">
                      <button className="btn btn-secondary" style={{ padding: 6 }} onClick={() => setAdminView('dashboard')}>
                        <CaretLeft size={20} />
                      </button>
                      <span className="label" style={{ margin: 0 }}>{t('admin_promos')}</span>
                    </div>
                    <form onSubmit={createPromoAdmin} className="flex flex-col gap-2">
                      <div className="flex gap-2">
                        <input className="input" placeholder="XXXX-XXXX-XXXX" value={newPromoCode} onChange={e => setNewPromoCode(e.target.value)} style={{ flex: 1 }} onFocus={handleInputFocus} />
                        <button type="button" className="btn btn-secondary" onClick={generateRandomPromo}>GEN</button>
                      </div>
                      <div className="flex gap-2 mt-2">
                        <div className="flex flex-col flex-1 gap-1">
                          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('admin_promo_days')}</span>
                          <input type="number" className="input" value={newPromoDuration} onChange={e => setNewPromoDuration(parseInt(e.target.value))} onFocus={handleInputFocus} />
                        </div>
                        <div className="flex flex-col flex-1 gap-1">
                          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{t('admin_promo_uses')}</span>
                          <input type="number" className="input" value={newPromoMaxAct} onChange={e => setNewPromoMaxAct(parseInt(e.target.value))} onFocus={handleInputFocus} />
                        </div>
                      </div>
                      <button type="submit" className="btn btn-primary mt-2">{t('admin_create_promo')}</button>
                    </form>

                    <div className="flex flex-col gap-2 mt-4" style={{ maxHeight: 200, overflowY: 'auto' }}>
                      {adminPromocodes.map(promo => (
                        <div key={promo.code} className="flex" style={{ justifyContent: 'space-between', alignItems: 'center', padding: 8, background: 'var(--bg-canvas)', borderRadius: 8 }}>
                          <div className="flex flex-col">
                            <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{promo.code}</span>
                            <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{t('admin_promo_details', { days: promo.duration_days, uses: promo.activations_count, max: promo.max_activations })}</span>
                          </div>
                          <button className="btn btn-danger" style={{ padding: 6 }} onClick={() => deletePromoAdmin(promo.code)}><Trash size={14}/></button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </main>

      <nav className="nav-pill-container">
        <button className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
          <SquaresFour size={24} weight={activeTab === 'dashboard' ? "fill" : "regular"} />
        </button>
        <button className={`nav-item ${activeTab === 'digest' ? 'active' : ''}`} onClick={() => setActiveTab('digest')}>
          <Sparkle size={24} weight={activeTab === 'digest' ? "fill" : "regular"} />
        </button>
        <button className="nav-fab" onClick={() => setActiveTab('sources')}>
          <Link size={28} weight="bold" />
        </button>
        <button className={`nav-item ${activeTab === 'settings' ? 'active' : ''}`} onClick={() => setActiveTab('settings')}>
          <Gear size={24} weight={activeTab === 'settings' ? "fill" : "regular"} />
        </button>
        <button className={`nav-item ${activeTab === 'info' ? 'active' : ''}`} onClick={() => setActiveTab('info')}>
          <Info size={24} weight={activeTab === 'info' ? "fill" : "regular"} />
        </button>
      </nav>

      <AnimatePresence>
        {showBuyProModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="modal-overlay" onClick={() => setShowBuyProModal(false)}
            style={{ zIndex: 1000 }}
          >
            <motion.div 
              initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="modal-sheet" onClick={e => e.stopPropagation()}
            >
              <div className="modal-header">
                <h3 className="modal-title">{t('get_pro_title')}</h3>
                <button 
                  className="btn btn-secondary" 
                  style={{ 
                    height: '32px', 
                    width: '32px', 
                    borderRadius: '8px', 
                    padding: 0, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center' 
                  }} 
                  onClick={() => setShowBuyProModal(false)}
                >
                  <X size={20} />
                </button>
              </div>
              <div className="bento-cell" style={{ gap: '12px' }}>
                <p style={{ margin: 0, fontSize: 14, color: 'var(--text-secondary)' }}>{t('get_pro_desc')}</p>
                <button className="btn btn-primary" onClick={buyPro} style={{ width: '100%', height: '48px', fontSize: '16px' }}>{t('pay_stars_btn')}</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {adminUserDetails && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="modal-overlay" onClick={() => { setAdminUserDetails(null); setBanConfirmModal(null); setShowManageProModal(null); }}
          >
            <motion.div 
              initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="modal-sheet" onClick={e => e.stopPropagation()}
            >
              <div className="modal-header">
                <h3 className="modal-title">{t('user_card_title')}</h3>
                <div className="flex gap-2">
                  {user?.telegram_id !== adminUserDetails.telegram_id && (
                    <button 
                      className="btn btn-secondary" 
                      style={{ 
                        height: '32px', 
                        width: '32px', 
                        borderRadius: '8px', 
                        padding: 0, 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center' 
                      }} 
                      onClick={() => resetCooldown(adminUserDetails.telegram_id)}
                      title={isRu ? "Сбросить лимит генерации" : "Reset digest cooldown"}
                    >
                      <ArrowCounterClockwise size={18} />
                    </button>
                  )}
                  <button 
                    className="btn btn-secondary" 
                    style={{ 
                      height: '32px', 
                      width: '32px', 
                      borderRadius: '8px', 
                      padding: 0, 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center' 
                    }} 
                    onClick={() => { setAdminUserDetails(null); setBanConfirmModal(null); setShowManageProModal(null); }}
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <div className="bento-cell">
                  <div className="flex" style={{ justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>ID</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14 }}>{adminUserDetails.telegram_id}</span>
                  </div>
                  <div className="flex" style={{ justifyContent: 'space-between', marginTop: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Username</span>
                    <span style={{ fontSize: 14 }}>{adminUserDetails.username ? `@${adminUserDetails.username}` : 'N/A'}</span>
                  </div>
                  <div className="flex" style={{ justifyContent: 'space-between', marginTop: 8 }}>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{isRu ? "Статус" : "Status"}</span>
                    <span style={{ fontWeight: 600, fontSize: 14, color: adminUserDetails.is_banned ? 'var(--danger)' : (adminUserDetails.is_pro ? 'var(--accent)' : 'var(--text-primary)') }}>
                      {adminUserDetails.is_banned ? t('user_status_banned') : (adminUserDetails.is_pro ? 'PRO' : 'FREE')}
                    </span>
                  </div>
                  {adminUserDetails.is_pro && adminUserDetails.pro_expires_at && (
                    <div className="flex" style={{ justifyContent: 'space-between', marginTop: 8 }}>
                      <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{t('user_expires_at')}</span>
                      <span style={{ fontSize: 14 }}>{new Date(adminUserDetails.pro_expires_at).toLocaleString()}</span>
                    </div>
                  )}
                </div>

                <div className="bento-cell p-0 overflow-hidden">
                  <div className="border-b border-white/10 flex justify-between items-center" style={{ padding: '12px 16px' }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-tertiary)' }}>{t('user_connected_channels', { count: adminUserDetails.stats.channels })}</span>
                  </div>
                  <div style={{ maxHeight: 150, overflowY: 'auto', padding: '12px 16px' }}>
                    {adminUserDetails.channels?.length === 0 ? (
                      <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>{t('user_no_channels')}</span>
                    ) : (
                      <div className="flex flex-col gap-2">
                        {adminUserDetails.channels?.map((c: any) => {
                          let touchTimer: any = null;
                          const handleStart = () => {
                            touchTimer = setTimeout(() => {
                              touchTimer = null;
                              navigator.clipboard.writeText(`@${c.username}`);
                              showSuccess(isRu ? `Ссылка @${c.username} скопирована` : `@${c.username} copied`);
                              if (window.navigator.vibrate) window.navigator.vibrate(50);
                            }, 600);
                          };
                          const handleEnd = () => {
                            if (touchTimer) {
                              clearTimeout(touchTimer);
                              touchTimer = null;
                              window.open(`https://t.me/${c.username}`, '_blank');
                            }
                          };
                          const handleMove = () => {
                            if (touchTimer) {
                              clearTimeout(touchTimer);
                              touchTimer = null;
                            }
                          };
                          const handleContextMenu = (e: React.MouseEvent) => {
                            e.preventDefault();
                            navigator.clipboard.writeText(`@${c.username}`);
                            showSuccess(isRu ? `Ссылка @${c.username} скопирована` : `@${c.username} copied`);
                          };
                          return (
                            <div 
                              key={c.id} 
                              className="flex justify-between items-center rounded hover:bg-white/5 cursor-pointer" 
                              style={{ padding: '8px 16px', userSelect: 'none' }}
                              onTouchStart={handleStart}
                              onTouchEnd={handleEnd}
                              onTouchMove={handleMove}
                              onMouseDown={e => { if (e.button === 0) handleStart(); }}
                              onMouseUp={e => { if (e.button === 0) handleEnd(); }}
                              onMouseLeave={handleMove}
                              onContextMenu={handleContextMenu}
                            >
                              <span style={{ fontSize: 13, color: 'var(--text-primary)' }}>{c.title || `@${c.username}`}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                <div className="bento-cell p-0 overflow-hidden">
                  <div className="border-b border-white/10 flex justify-between items-center" style={{ padding: '12px 16px' }}>
                    <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-tertiary)' }}>{t('user_messages_last')}</span>
                  </div>
                  <div style={{ maxHeight: 200, overflowY: 'auto', padding: '12px 16px' }}>
                    {adminUserDetails.messages?.length === 0 ? (
                      <span style={{ fontSize: 13, color: 'var(--text-tertiary)' }}>{t('user_no_messages')}</span>
                    ) : (
                      <div className="flex flex-col gap-3">
                        {adminUserDetails.messages?.map((m: any) => {
                          let touchTimer: any = null;
                          const handleStart = () => {
                            touchTimer = setTimeout(() => {
                              touchTimer = null;
                              navigator.clipboard.writeText(m.text);
                              showSuccess(isRu ? "Текст сообщения скопирован" : "Message text copied");
                              if (window.navigator.vibrate) window.navigator.vibrate(50);
                            }, 600);
                          };
                          const handleEnd = () => {
                            if (touchTimer) {
                              clearTimeout(touchTimer);
                              touchTimer = null;
                              if (m.url) {
                                window.open(m.url, '_blank');
                              }
                            }
                          };
                          const handleMove = () => {
                            if (touchTimer) {
                              clearTimeout(touchTimer);
                              touchTimer = null;
                            }
                          };
                          const handleContextMenu = (e: React.MouseEvent) => {
                            e.preventDefault();
                            navigator.clipboard.writeText(m.text);
                            showSuccess(isRu ? "Текст сообщения скопирован" : "Message text copied");
                          };
                          return (
                            <div 
                              key={m.id} 
                              className="rounded bg-white/5 cursor-pointer hover:bg-white/10" 
                              style={{ padding: '12px 16px', userSelect: 'none' }}
                              onTouchStart={handleStart}
                              onTouchEnd={handleEnd}
                              onTouchMove={handleMove}
                              onMouseDown={e => { if (e.button === 0) handleStart(); }}
                              onMouseUp={e => { if (e.button === 0) handleEnd(); }}
                              onMouseLeave={handleMove}
                              onContextMenu={handleContextMenu}
                            >
                              <div className="flex justify-between mb-2">
                                <span style={{ fontSize: 11, color: 'var(--accent)' }}>{m.channel_title}</span>
                                <span style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>{new Date(m.created_at).toLocaleString()}</span>
                              </div>
                              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }} className="truncate-2-lines">
                                {m.text}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {user?.telegram_id !== adminUserDetails.telegram_id && (
                  <div className="flex gap-3 mt-3">
                    <button 
                      className="btn btn-secondary flex-1" 
                      onClick={() => setShowManageProModal(adminUserDetails.telegram_id)}
                      style={{ padding: '12px' }}
                    >
                      <Crown size={18} style={{ marginRight: 8 }} />
                      {t('user_manage_subscription')}
                    </button>
                    <button 
                      className="btn" 
                      style={{ 
                        padding: '12px', 
                        aspectRatio: '1/1',
                        width: '46px',
                        height: '46px',
                        background: adminUserDetails.is_banned ? 'var(--bg-canvas)' : 'var(--danger-faint)', 
                        color: adminUserDetails.is_banned ? 'var(--text-primary)' : 'var(--danger)', 
                        border: `1px solid ${adminUserDetails.is_banned ? 'var(--border-subtle)' : 'var(--danger)'}`,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }} 
                      onClick={() => {
                        if (adminUserDetails.is_banned) {
                          banUser(adminUserDetails.telegram_id);
                        } else {
                          setBanConfirmModal(adminUserDetails.telegram_id);
                        }
                      }}
                    >
                      <Prohibit size={18} />
                    </button>
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showManageProModal !== null && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="modal-overlay" onClick={() => setShowManageProModal(null)}
            style={{ zIndex: 1500, alignItems: 'center', justifyContent: 'center' }}
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              className="bento-cell" onClick={e => e.stopPropagation()}
              style={{ width: '85%', maxWidth: '320px', padding: '24px 16px', textAlign: 'center' }}
            >
              <Crown size={48} color="var(--accent)" weight="duotone" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: 18, margin: '0 0 16px' }}>{t('manage_pro_title')}</h3>
              
              <div className="flex flex-col gap-3">
                <div className="flex gap-2 justify-between">
                  <button 
                    type="button"
                    className={`btn flex-1 ${proDaysInput === 30 ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '13px', padding: '8px 4px', height: '36px', borderRadius: '8px' }} 
                    onClick={() => setProDaysInput(30)}
                  >
                    {isRu ? '1 месяц' : '1 month'}
                  </button>
                  <button 
                    type="button"
                    className={`btn flex-1 ${proDaysInput === 180 ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '13px', padding: '8px 4px', height: '36px', borderRadius: '8px' }} 
                    onClick={() => setProDaysInput(180)}
                  >
                    {isRu ? '6 месяцев' : '6 months'}
                  </button>
                  <button 
                    type="button"
                    className={`btn flex-1 ${proDaysInput === 365 ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ fontSize: '13px', padding: '8px 4px', height: '36px', borderRadius: '8px' }} 
                    onClick={() => setProDaysInput(365)}
                  >
                    {isRu ? '12 месяцев' : '12 months'}
                  </button>
                </div>
                <div className="flex gap-2 items-center">
                  <input 
                    type="number" 
                    className="input flex-1" 
                    value={proDaysInput} 
                    onChange={e => setProDaysInput(parseInt(e.target.value) || 0)} 
                    onFocus={handleInputFocus}
                  />
                  <span style={{ fontSize: 14, color: 'var(--text-secondary)' }}>{t('manage_pro_days')}</span>
                </div>
                <button className="btn btn-primary w-full" onClick={() => grantPro(showManageProModal, proDaysInput)}>
                  {t('manage_pro_grant')}
                </button>
                <div style={{ height: 1, background: 'var(--border-subtle)', margin: '8px 0' }} />
                <button className="btn btn-danger w-full" onClick={() => grantPro(showManageProModal, 0)}>
                  {t('manage_pro_remove')}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showDocModal && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="modal-overlay" onClick={() => setShowDocModal(false)}
            style={{ zIndex: 1000 }}
          >
            <motion.div 
              initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="modal-sheet" onClick={e => e.stopPropagation()}
              style={{ maxHeight: '80vh', overflowY: 'auto' }}
            >
              <div className="modal-header">
                <h3 className="modal-title">{t('app_doc_btn')}</h3>
                <button 
                  className="btn btn-secondary" 
                  style={{ 
                    height: '32px', 
                    width: '32px', 
                    borderRadius: '8px', 
                    padding: 0, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center' 
                  }} 
                  onClick={() => setShowDocModal(false)}
                >
                  <X size={20} />
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '0 0 16px' }}>
                {isRu ? (
                  <>
                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>1. Добавление источников</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        Вы можете добавлять публичные открытые Telegram-каналы, используя <strong>@username</strong> или ссылку (например, <code>t.me/username</code>).
                      </p>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-tertiary)' }}>
                        ⚠️ Приватные каналы и ссылки-приглашения не поддерживаются.
                      </p>
                    </div>

                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>2. Настройка ключевых слов</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        Фильтрация сообщений поддерживает следующие режимы работы:
                      </p>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <li><strong>Смысловой:</strong> ИИ анализирует контекст и ищет сообщения, близкие по значению вашему ключевому слову.</li>
                        <li><strong>Точная фраза:</strong> Поиск точного совпадения введенной фразы.</li>
                        <li><strong>Точное слово:</strong> Ищет конкретное слово (с учётом словоформ).</li>
                        <li><strong>Исключить:</strong> Сообщения, содержащие это слово, будут игнорироваться.</li>
                      </ul>
                    </div>

                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>3. AI Дайджест</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        Генерация структурированных ИИ-сводок по истории сообщений за любой период от <strong>1 до 24 часов</strong>.
                      </p>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        Настройте автоматическую ежедневную рассылку дайджеста в удобное время или запускайте генерацию вручную по выбранным источникам.
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>1. Adding Sources</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        You can add public open Telegram channels using <strong>@username</strong> or a channel link (e.g., <code>t.me/username</code>).
                      </p>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-tertiary)' }}>
                        ⚠️ Private channels and invite links are not supported.
                      </p>
                    </div>

                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>2. Key Words & Filters</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                        Message filtration supports the following modes:
                      </p>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <li><strong>Semantic:</strong> AI analyzes the context and finds messages that match the meaning of your keyword.</li>
                        <li><strong>Exact Phrase:</strong> Searches for the exact matching phrase.</li>
                        <li><strong>Exact Word:</strong> Searches for the exact single word.</li>
                        <li><strong>Exclude:</strong> Messages containing this keyword will be completely filtered out.</li>
                      </ul>
                    </div>

                    <div className="bento-cell" style={{ gap: '8px', alignItems: 'flex-start' }}>
                      <h4 style={{ color: 'var(--accent)', fontSize: '15px', fontWeight: 600, margin: '0 0 4px' }}>3. AI Digest</h4>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        Generates structured AI summaries based on message history for any period from <strong>1 to 24 hours</strong>.
                      </p>
                      <p style={{ margin: 0, fontSize: '13px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
                        Set up an automatic daily digest newsletter at your preferred time or trigger manual generation for selected sources.
                      </p>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {banConfirmModal !== null && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="modal-overlay" onClick={() => setBanConfirmModal(null)}
            style={{ zIndex: 2000, alignItems: 'center', justifyContent: 'center' }}
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
              className="bento-cell" onClick={e => e.stopPropagation()}
              style={{ width: '85%', maxWidth: '320px', padding: 24, textAlign: 'center' }}
            >
              <WarningCircle size={48} color="var(--danger)" weight="duotone" style={{ margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: 18, margin: '0 0 8px' }}>{t('ban_confirm_title')}</h3>
              <p style={{ fontSize: 14, color: 'var(--text-secondary)', marginBottom: 24 }}>
                {t('ban_confirm_desc', { id: banConfirmModal })}
              </p>
              <div className="flex gap-2">
                <button className="btn btn-secondary flex-1" onClick={() => setBanConfirmModal(null)}>{t('cancel')}</button>
                <button className="btn btn-danger flex-1" onClick={() => banUser(banConfirmModal)}>{t('ban_btn')}</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
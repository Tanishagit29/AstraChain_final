// Backend URL helper. Dynamically supports localhost, local network IP (e.g. 192.168.x.x for mobile phones), and VITE_API_URL.
export function getApiBaseUrl() {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname;
    const proto = window.location.protocol || 'http:';
    return `${proto}//${host}:8000/api`;
  }
  return 'http://127.0.0.1:8000/api';
}

const REQUEST_TIMEOUT_MS = 30000; // normal page data
const PIPELINE_TIMEOUT_MS = 10 * 60 * 1000; // big CSVs can take a while to clean + forecast

function getNetworkHint() {
  return `Cannot reach the AstraChain backend at ${getApiBaseUrl()}. Start it with: cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

function describeNetworkError(err) {
  if (err && err.name === 'AbortError') {
    return 'The backend took too long to respond. Check the backend terminal for errors.';
  }
  return getNetworkHint();
}

async function readError(res, fallback) {
  const body = await res.json().catch(() => ({}));
  // The backend uses { error } for pipeline failures, { message } for handled errors and { detail } for FastAPI errors.
  return body.error || body.message || body.detail || `${fallback}: ${res.status}`;
}

async function apiRequest(endpoint, options = {}) {
  try {
    const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers };
    const res = await fetchWithTimeout(`${getApiBaseUrl()}${endpoint}`, { ...options, headers });
    if (!res.ok) {
      throw new Error(`API Error: ${res.status}`);
    }
    const json = await res.json();
    return json.data !== undefined ? json.data : json;
  } catch (err) {
    console.warn(`[AstraChain API] ${endpoint}:`, err.message);
    return null;
  }
}

export const api = {
  // =============================================
  // PIPELINE ENDPOINTS (Primary)
  // =============================================

  /** Run the full automatic pipeline: upload → clean → forecast → inventory → wastage */
  runFullPipeline: async (files) => {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    try {
      const res = await fetchWithTimeout(
        `${getApiBaseUrl()}/data-collection/pipeline`,
        { method: 'POST', body: formData },
        PIPELINE_TIMEOUT_MS
      );
      if (!res.ok) {
        throw new Error(await readError(res, 'Pipeline failed'));
      }
      return await res.json();
    } catch (err) {
      console.error('[Pipeline Error]', err);
      const isNetwork = err instanceof TypeError || err.name === 'AbortError';
      return { error: isNetwork ? describeNetworkError(err) : err.message };
    }
  },

  /** Get the current pipeline status */
  getPipelineStatus: async () => {
    return await apiRequest('/pipeline/status');
  },

  /** Get combined dashboard data from pipeline results */
  getPipelineDashboard: async () => {
    return await apiRequest('/pipeline/dashboard');
  },

  /** Get the Groq LLM agents' reasoning about the latest pipeline run (filled in the background) */
  getPipelineAgents: async () => {
    return await apiRequest('/pipeline/agents');
  },

  /** Get latest XGBoost forecast from pipeline */
  getPipelineForecast: async () => {
    return await apiRequest('/pipeline/forecast');
  },

  /** Get latest inventory analysis from pipeline */
  getPipelineInventory: async () => {
    return await apiRequest('/pipeline/inventory');
  },

  /** Get latest wastage/expiry decisions from pipeline */
  getPipelineWastage: async () => {
    return await apiRequest('/pipeline/wastage');
  },

  /** Add a near-to-expire item with automatic discount calculation */
  addNearExpiryItem: async (itemData) => {
    return await apiRequest('/pipeline/wastage/add', {
      method: 'POST',
      body: JSON.stringify(itemData),
    });
  },

  /** Get complete data collection & pipeline intelligence state */
  getPipelineDataCollection: async () => {
    return await apiRequest('/pipeline/data-collection');
  },

  // =============================================
  // AI, AGENTS & TELEMETRY
  // =============================================

  getAIAgents: async () => {
    return await apiRequest('/ai/agents');
  },

  chatAICopilot: async (message) => {
    return await apiRequest('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  getAIRecommendations: async () => {
    return await apiRequest('/ai/recommendations');
  },

  getSuppliers: async () => {
    return await apiRequest('/suppliers');
  },

  getRoutes: async () => {
    return await apiRequest('/routes');
  },

  getKnownLocations: async () => {
    return await apiRequest('/routes/locations');
  },

  optimizeMultiStopRoute: async ({ truckId, origin, stops, returnToOrigin = false }) => {
    return await apiRequest('/routes/optimize-multi-stop', {
      method: 'POST',
      body: JSON.stringify({
        truck_id: truckId,
        origin,
        stops,
        return_to_origin: returnToOrigin,
      }),
    });
  },

  getFestivalCalendar: async (year = null) => {
    const q = year ? `?year=${year}` : '';
    return await apiRequest(`/forecast/festivals/calendar${q}`);
  },

  getUpcomingFestivals: async (category = 'General', withinDays = 60) => {
    return await apiRequest(`/forecast/festivals/upcoming?category=${encodeURIComponent(category)}&within_days=${withinDays}`);
  },

  getFestivalForecast: async (productId, horizonDays = 60) => {
    return await apiRequest(`/forecast/${productId}/festival-forecast?horizon_days=${horizonDays}`);
  },

  getFestivalItemDemand: async (festivalName = null, horizonDays = 60, limit = 20) => {
    const festQuery = festivalName ? `festival_name=${encodeURIComponent(festivalName)}&` : '';
    return await apiRequest(`/forecast/festivals/item-demand?${festQuery}horizon_days=${horizonDays}&limit=${limit}`);
  },

  getAutomationRules: async () => {
    return await apiRequest('/automation/rules');
  },

  getReports: async () => {
    return await apiRequest('/reports');
  },

  executeKeyAction: async ({ action_type, target_id, details }) => {
    return await apiRequest('/multi-agent/action/execute', {
      method: 'POST',
      body: JSON.stringify({ action_type, target_id, details }),
    });
  },

  // =============================================
  // MANAGER NOTIFICATION & 1-CLICK RESTOCK
  // =============================================

  getNotifications: async (unreadOnly = false) => {
    const q = unreadOnly ? '?unread_only=true' : '';
    const res = await apiRequest(`/notifications${q}`);
    return res || { success: false, unread_count: 0, stockout_count: 0, wastage_count: 0, festival_count: 0, restocked_count: 0, data: [] };
  },

  restockProduct: async ({ product_id, quantity = 500, notification_id = null }) => {
    return await apiRequest('/notifications/restock', {
      method: 'POST',
      body: JSON.stringify({ product_id, quantity, notification_id }),
    });
  },

  mitigateWastage: async ({ product_id, wastage_id = null, discount = '30% Dynamic Markdown', notification_id = null }) => {
    return await apiRequest('/notifications/wastage/mitigate', {
      method: 'POST',
      body: JSON.stringify({ product_id, wastage_id, discount, notification_id }),
    });
  },

  notifyRouteArrival: async ({ truck_id = 'MH-04-JK-4821', origin = 'Mumbai Central Port', destination = 'Pune Logistics Hub', fuel_saved = 14.2, co2_saved = 38.0 } = {}) => {
    return await apiRequest('/notifications/route/arrival', {
      method: 'POST',
      body: JSON.stringify({ truck_id, origin, destination, fuel_saved, co2_saved }),
    });
  },

  prestockFestival: async ({ product_id, festival_name = 'Diwali', quantity = 500, notification_id = null }) => {
    return await apiRequest('/notifications/festival/prestock', {
      method: 'POST',
      body: JSON.stringify({ product_id, festival_name, quantity, notification_id }),
    });
  },

  markNotificationRead: async (notificationId) => {
    return await apiRequest(`/notifications/${notificationId}/read`, {
      method: 'POST',
    });
  },

  markAllNotificationsRead: async () => {
    return await apiRequest('/notifications/mark-all-read', {
      method: 'POST',
    });
  },

  dismissNotification: async (notificationId) => {
    return await apiRequest(`/notifications/${notificationId}`, {
      method: 'DELETE',
    });
  },

  simulateNotification: async (type = 'stockout', details = {}) => {
    return await apiRequest('/notifications/simulate', {
      method: 'POST',
      body: JSON.stringify({ type, ...details }),
    });
  },


  getNotificationWsUrl: () => {
    if (import.meta.env.VITE_WS_URL) {
      return import.meta.env.VITE_WS_URL;
    }

    if (typeof window !== 'undefined' && window.location) {
      const host = window.location.hostname;
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

      return `${proto}//${host}:8000/api/notifications/ws`;
    }

    return 'ws://127.0.0.1:8000/api/notifications/ws';
  },

  // PHONE & MOBILE NOTIFICATION INTEGRATION
  getPhoneConfig: async () => {
    return await apiRequest('/notifications/phone/config');
  },

  updatePhoneConfig: async (config) => {
    return await apiRequest('/notifications/phone/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  sendTestPhonePush: async (alertType = 'stockout') => {
    return await apiRequest('/notifications/phone/test', {
      method: 'POST',
      body: JSON.stringify({ type: alertType }),
    });
  },

  // =============================================
  // LEGACY ENDPOINTS (Kept for compatibility)
  // =============================================

  getDashboard: async () => {
    const data = await apiRequest('/dashboard');
    if (data) return data;
    return null;
  },

  getForecast: async (productId = null, horizonDays = 30) => {
    if (productId) {
      const data = await apiRequest(`/forecast/${productId}?horizon_days=${horizonDays}`);
      if (data && data.daily_forecasts) return data.daily_forecasts;
    }
    const data = await apiRequest('/forecast');
    return data;
  },

  getInventory: async () => {
    const data = await apiRequest('/inventory?limit=100');
    if (data && data.items) return data.items;
    return [];
  },

  getWastage: async () => {
    const data = await apiRequest('/wastage');
    return data || [];
  },

  // Data Collection step-by-step (used by DataIntelligenceAgent page)
  uploadDataCollectionFiles: async (files) => {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    try {
      const res = await fetchWithTimeout(`${getApiBaseUrl()}/data-collection/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(err);
      return null;
    }
  },

  cleanDataCollectionData: async (params) => {
    const formData = new FormData();
    formData.append('session_id', params.session_id);
    formData.append('imputation_strategy', params.imputation_strategy || 'auto');
    formData.append('remove_duplicates', params.remove_duplicates !== false);
    formData.append('remove_empty_rows', params.remove_empty_rows !== false);
    formData.append('remove_empty_cols', params.remove_empty_cols !== false);
    formData.append('outlier_indices_to_remove', JSON.stringify(params.outlier_indices_to_remove || []));
    formData.append('standardize_fields', params.standardize_fields !== false);

    try {
      const res = await fetchWithTimeout(`${getApiBaseUrl()}/data-collection/clean`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) throw new Error(`Cleaning failed: ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(err);
      return null;
    }
  },
};


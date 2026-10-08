const API_BASE_URL = 'http://127.0.0.1:8000/api';

async function apiRequest(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
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
      const res = await fetch(`${API_BASE_URL}/data-collection/pipeline`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.error || errBody.detail || `Pipeline failed: ${res.status}`);
      }
      return await res.json();
    } catch (err) {
      console.error('[Pipeline Error]', err);
      return { error: err.message };
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
      const res = await fetch(`${API_BASE_URL}/data-collection/upload`, {
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
      const res = await fetch(`${API_BASE_URL}/data-collection/clean`, {
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


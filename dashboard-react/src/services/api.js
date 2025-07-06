const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

// Dynamic Assistant URL discovery
const getAssistantUrl = () => {
  if (process.env.REACT_APP_ASSISTANT_URL) return process.env.REACT_APP_ASSISTANT_URL;

  const ports = [5002, 5000, 3001];
  for (const port of ports) {
    if (window.location.port === port.toString()) continue;
    console.log(`🔄 Probing assistant on port ${port}`);
    return `http://localhost:${port}/api`;
  }

  return 'http://localhost:5002/api';
};

const ASSISTANT_URL = getAssistantUrl();
console.log(`🌐 Using Assistant URL: ${ASSISTANT_URL}`);

const TIMEOUTS = {
  STANDARD: 60000,
  EXTENDED: 20000,
  ASSISTANT: 45000,
  HEALTH_CHECK: 5000,
};

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const timeout = options.timeout || TIMEOUTS.STANDARD;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
      ...options,
    };

    try {
      const response = await fetch(url, config);
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return { data };
    } catch (error) {
      clearTimeout(timeoutId);
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - please try again');
      }
      console.error(`API request failed: ${endpoint}`, error);
      throw error;
    }
  }

  async healthCheck() {
    return this.request('/health', { timeout: TIMEOUTS.HEALTH_CHECK });
  }

  async getDashboardOverview() {
    return this.request('/dashboard/overview', { timeout: TIMEOUTS.EXTENDED });
  }

  async getBrands() {
    return this.request('/brands');
  }

  async getBrandScores(brand, limit = 100) {
    return this.request(`/brands/${encodeURIComponent(brand)}/scores?limit=${limit}`);
  }

  async getBrandPerformance(brand, days = 30) {
    return this.request(`/performance/${encodeURIComponent(brand)}?days=${days}`);
  }

  async getAlerts(limit = 25) {
    return this.request(`/alerts?limit=${limit}`);
  }

  async resolveAlert(alertId) {
    return this.request(`/alerts/${alertId}/resolve`, {
      method: 'POST',
    });
  }

  async getSentimentTrends(brand = null, days = 7) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/sentiment-trends?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getBiasDistribution(brand = null, days = 7) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/bias-distribution?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Enhanced endpoint for Alert Severity Pie Chart
  async getAlertSeverityData(brand = null, days = 7) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/alert-severity?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Enhanced endpoint for Bias Heatmap Chart
  async getBiasHeatmapData(brand = null, days = 7) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/bias-heatmap?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Enhanced endpoint for Brand Trust Trends Chart
  async getBrandTrustTrends(brand = null, days = 7) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/brand-trust-trends?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Enhanced utility endpoints for chart data
  async getAlertsWithSeverity(brand = null, limit = 100) {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/alerts/severity?${params}`);
  }

  async getBiasMetrics(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/bias-metrics?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getTrustScoreHistory(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/trust-score-history?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Batch data fetching for dashboard efficiency
  async getDashboardChartData(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/dashboard/chart-data?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // New comprehensive data endpoints for advanced analytics
  async getComprehensiveBiasData(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/comprehensive-bias-data?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getAlertSeverityDistribution(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/alert-severity-distribution?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getBrandTrustMetrics(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/brand-trust-metrics?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getBiasHeatmapMatrix(brand = null, days = 30) {
    const params = new URLSearchParams({ days: days.toString() });
    if (brand) params.append('brand', brand);
    return this.request(`/bias-heatmap-matrix?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Time-series data endpoints
  async getTimeSeriesData(metric, brand = null, days = 30) {
    const params = new URLSearchParams({ 
      metric: metric,
      days: days.toString() 
    });
    if (brand) params.append('brand', brand);
    return this.request(`/time-series?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getMultiMetricTimeSeriesData(metrics = [], brand = null, days = 30) {
    const params = new URLSearchParams({ 
      metrics: metrics.join(','),
      days: days.toString() 
    });
    if (brand) params.append('brand', brand);
    return this.request(`/multi-metric-time-series?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Advanced filtering and aggregation endpoints
  async getFilteredAlerts(filters = {}, limit = 100) {
    const params = new URLSearchParams({ limit: limit.toString() });
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        params.append(key, value);
      }
    });
    return this.request(`/alerts/filtered?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async getAggregatedMetrics(groupBy = 'brand', aggregation = 'count', days = 30) {
    const params = new URLSearchParams({ 
      groupBy: groupBy,
      aggregation: aggregation,
      days: days.toString() 
    });
    return this.request(`/aggregated-metrics?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  // Export and reporting endpoints
  async exportChartData(chartType, brand = null, days = 30, format = 'json') {
    const params = new URLSearchParams({ 
      chartType: chartType,
      days: days.toString(),
      format: format
    });
    if (brand) params.append('brand', brand);
    return this.request(`/export/chart-data?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }

  async generateReport(reportType, brand = null, days = 30) {
    const params = new URLSearchParams({ 
      reportType: reportType,
      days: days.toString()
    });
    if (brand) params.append('brand', brand);
    return this.request(`/generate-report?${params}`, { timeout: TIMEOUTS.EXTENDED });
  }
}

// 🧠 ZOBON assistant API (enhanced with chart-specific methods)
export const askSQLAssistant = async (question, context = {}, retryCount = 0) => {
  const MAX_RETRIES = 2;
  const RETRY_DELAY = 2000;

  if (!question || typeof question !== 'string' || !question.trim()) {
    throw new Error('Question must be a non-empty string');
  }

  const normalizedQuestion = question.trim();
  const payload = { 
    question: normalizedQuestion,
    ...context
  };

  console.log(`🤖 Assistant Request (attempt ${retryCount + 1}):`, {
    question: normalizedQuestion,
    context: context,
    url: `${ASSISTANT_URL}/ask`
  });

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUTS.ASSISTANT);

  try {
    const response = await fetch(`${ASSISTANT_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json"
      },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.message || errorMessage;
      } catch {}

      throw new Error(`Assistant API error: ${errorMessage}`);
    }

    const data = await response.json();

    if (!data || typeof data !== 'object') {
      throw new Error('Invalid response from assistant service');
    }

    if (data.error) throw new Error(data.error);
    if (!data.answer || typeof data.answer !== "string") {
      throw new Error('Assistant returned no valid answer');
    }

    console.log('✅ Assistant response received successfully');
    return { data };

  } catch (error) {
    clearTimeout(timeoutId);

    if (error.name === 'AbortError') {
      throw new Error('Assistant request timed out');
    }

    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      if (retryCount < MAX_RETRIES) {
        console.log(`🔄 Network error, retrying in ${RETRY_DELAY}ms...`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return askSQLAssistant(question, context, retryCount + 1);
      }

      throw new Error(`Connection failed to assistant at ${ASSISTANT_URL}. Is the backend running?`);
    }

    throw error;
  }
};

// Chart-specific assistant methods
export const askChartAssistant = async (chartType, question, chartData = null) => {
  const context = {
    chartType: chartType,
    hasData: chartData !== null,
    dataSize: chartData ? chartData.length : 0
  };

  return askSQLAssistant(question, context);
};

export const askBiasAnalysisAssistant = async (question, biasData = null) => {
  return askChartAssistant('bias-analysis', question, biasData);
};

export const askTrustTrendAssistant = async (question, trustData = null) => {
  return askChartAssistant('trust-trend', question, trustData);
};

export const askSeverityAnalysisAssistant = async (question, severityData = null) => {
  return askChartAssistant('severity-analysis', question, severityData);
};

export const checkAssistantHealth = async () => {
  console.log(`🔍 Checking AI Assistant health at ${ASSISTANT_URL}...`);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUTS.HEALTH_CHECK);

  try {
    const response = await fetch(`${ASSISTANT_URL}/health`, {
      method: "GET",
      headers: { "Accept": "application/json" },
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (response.ok) {
      const healthData = await response.json();
      console.log('✅ Health check successful');
      return {
        status: 'healthy',
        timestamp: Date.now(),
        details: healthData,
        url: ASSISTANT_URL
      };
    } else {
      return {
        status: 'unhealthy',
        error: `HTTP ${response.status}`,
        timestamp: Date.now(),
        url: ASSISTANT_URL
      };
    }
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('❌ Health check failed:', error);

    return {
      status: 'unreachable',
      error: error.message,
      timestamp: Date.now(),
      url: ASSISTANT_URL
    };
  }
};

export const testAssistantConnection = async () => {
  console.log('🧪 Testing AI Assistant connection...');

  try {
    const healthResult = await checkAssistantHealth();

    if (healthResult.status === 'unreachable') {
      return {
        success: false,
        error: 'Service is unreachable',
        details: healthResult
      };
    }

    const { data: queryResult } = await askSQLAssistant("Show me a simple test query");

    return {
      success: true,
      health: healthResult,
      testQuery: queryResult
    };

  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
};

const apiService = new ApiService();
export default apiService;
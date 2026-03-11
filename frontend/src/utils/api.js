// frontend/src/utils/api.js
// ============================================================
// API UTILITIES - Simplified for reliability
// ============================================================

// Export for backward compatibility
export const API_URL = import.meta.env.VITE_API_URL || '/api';
export const API_KEY = import.meta.env.VITE_API_KEY || '';

// Use relative URL - works with both dev (proxy) and production (same origin)
const API_BASE = '/api';

// Backward compatible exports
export const resolveApiUrl = () => API_URL;
export const headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

// Backward compatible fetch with retry
export const fetchWithRetry = async (url, options = {}, retries = 3, backoff = 1000) => {
  try {
    const response = await fetch(url, options);
    if (!response.ok && retries > 0 && response.status >= 500) {
      await new Promise(resolve => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    return response;
  } catch (error) {
    if (retries > 0) {
      await new Promise(resolve => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
};

// Simple fetch with timeout
async function apiFetch(url, options = {}, timeout = 30000) {
  const fullUrl = `${API_BASE}${url}`;
  console.log(`[API] ${options.method || 'GET'} ${fullUrl}`);
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(fullUrl, {
      ...options,
      headers: { ...headers, ...options.headers },
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
}

// ============================================================
// AGENTS API
// ============================================================

export const fetchAgents = async () => {
  try {
    const response = await apiFetch('/agents/');
    if (!response.ok) return [];
    const data = await response.json();
    return data.agents || data.results || data.data || data || [];
  } catch (error) {
    console.error('Error fetching agents:', error);
    return [];
  }
};

export const createAgent = async (agentData) => {
  try {
    console.log('[API] Creating agent:', agentData);
    
    const response = await apiFetch('/agents/', {
      method: 'POST',
      body: JSON.stringify(agentData)
    });
    
    console.log('[API] Response status:', response.status);
    
    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch (e) {
        const text = await response.text();
        errorMessage = text || errorMessage;
      }
      console.error('[API] Error:', errorMessage);
      return { error: errorMessage };
    }
    
    const data = await response.json();
    console.log('[API] Success:', data);
    return data;
    
  } catch (error) {
    console.error('[API] Exception:', error);
    return { error: error.message || 'Network error - backend may be down' };
  }
};

export const deleteAgent = async (agentId) => {
  try {
    const response = await apiFetch(`/agents/${agentId}`, { method: 'DELETE' });
    return response.ok;
  } catch (error) {
    console.error('Error deleting agent:', error);
    return false;
  }
};

export const stopAgent = async (agentId) => {
  try {
    const response = await apiFetch(`/agents/${agentId}/stop`, { method: 'POST' });
    return response.ok;
  } catch (error) {
    console.error('Error stopping agent:', error);
    return false;
  }
};

export const fetchAgentLeads = async (agentId) => {
  try {
    const response = await apiFetch(`/agents/${agentId}/leads`);
    if (!response.ok) return [];
    const data = await response.json();
    return data.leads || data.results || data.data || [];
  } catch (error) {
    console.error('Error fetching agent leads:', error);
    return [];
  }
};

export const exportAgentLeads = async (agentId) => {
  try {
    const response = await apiFetch(`/agents/${agentId}/export`, { method: 'GET' });
    if (!response.ok) throw new Error('Export failed');
    return await response.blob();
  } catch (error) {
    console.error('Error exporting agent leads:', error);
    throw error;
  }
};

// ============================================================
// LEADS API
// ============================================================

export const fetchLeads = async (limit = 10, type = null, filters = {}) => {
  try {
    let url = `/leads?limit=${limit}`;
    if (type) url += `&type=${type}`;
    
    // Add source filters
    if (filters.sources && filters.sources.length > 0) {
      filters.sources.forEach(source => {
        url += `&sources=${encodeURIComponent(source)}`;
      });
    }
    
    // Add freshness filters
    if (filters.freshness && filters.freshness.length > 0) {
      filters.freshness.forEach(fresh => {
        url += `&freshness=${encodeURIComponent(fresh)}`;
      });
    }
    
    const response = await apiFetch(url);
    if (!response.ok) return [];
    
    const data = await response.json();
    return data.leads || data.results || data.data || [];
  } catch (error) {
    console.error('Error fetching leads:', error);
    return [];
  }
};

// Backward compatible fetchLeadsMeta
export const fetchLeadsMeta = async (limit = 10) => {
  const data = await fetchLeads(limit);
  return { leads: data, warning: '' };
};

export const searchLeads = async (query, location = 'Kenya') => {
  try {
    console.log(`[API] POST /search query="${query}" location="${location}"`);
    
    const response = await apiFetch('/search', {
      method: 'POST',
      body: JSON.stringify({ query, location }),
      cache: 'no-store'
    });
    
    if (!response.ok) {
      console.error('[API] Search failed:', response.status);
      return [];
    }
    
    const data = await response.json();
    const results = data.results || data.leads || [];
    console.log(`[API] Received ${results.length} leads (mode: ${data.mode || 'unknown'})`);
    return results;
  } catch (error) {
    console.error('[API] Search error:', error);
    return [];
  }
};

// ============================================================
// NOTIFICATIONS API
// ============================================================

export const fetchNotifications = async () => {
  try {
    const response = await apiFetch('/notifications/');
    if (!response.ok) return [];
    const data = await response.json();
    return data.notifications || data.results || data.data || [];
  } catch (error) {
    console.error('Error fetching notifications:', error);
    return [];
  }
};

export const fetchNotificationCount = async () => {
  try {
    const response = await apiFetch('/notifications/count?unread_only=true');
    if (!response.ok) return 0;
    const data = await response.json();
    return data.count || 0;
  } catch (error) {
    console.error('Error fetching notification count:', error);
    return 0;
  }
};

// ============================================================
// HEALTH/PING
// ============================================================

export const pingBackend = async () => {
  try {
    const response = await apiFetch('/search/health');
    return response.ok;
  } catch (error) {
    return false;
  }
};

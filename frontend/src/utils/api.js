// frontend/src/utils/api.js
// ============================================================
// API UTILITIES — Fixed error handling, dual key support
// ============================================================

export const API_URL = import.meta.env.VITE_API_URL || "/api";
export const API_KEY = import.meta.env.VITE_API_KEY || "";
export const GOOGLE_CSE_ID = "f32db13486dc14c26";

const baseHeaders = {
  "Content-Type": "application/json",
  "Accept": "application/json"
};

export const headers = API_KEY
  ? { ...baseHeaders, "x-api-key": API_KEY }
  : baseHeaders;

// Retry helper with exponential backoff
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
      console.warn(`Fetch failed, retrying in ${backoff}ms...`, error.message);
      await new Promise(resolve => setTimeout(resolve, backoff));
      return fetchWithRetry(url, options, retries - 1, backoff * 2);
    }
    throw error;
  }
};

// FIXED: Better error handling, support both 'leads' and 'results' keys
export const fetchLeads = async (limit = 10, type = null) => {
  try {
    let url = `${API_URL}/leads?limit=${limit}`;
    if (type) url += `&type=${type}`;

    const response = await fetchWithRetry(url, { method: "GET", headers });

    if (!response.ok) {
      console.error(`API Error: ${response.status} ${response.statusText}`);
      return [];
    }

    const data = await response.json();

    if (data.warning) {
      console.warn("⚠️ Backend warning:", data.warning);
    }

    // Support multiple response formats
    return data.leads || data.results || data.data || [];
  } catch (error) {
    console.error("❌ Error fetching leads:", error);
    return [];
  }
};

export const fetchLeadsMeta = async (limit = 10) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/leads?limit=${limit}`, {
      method: "GET",
      headers,
    });

    if (!response.ok) {
      console.error(`API Error: ${response.status}`);
      return { leads: [], warning: `API returned ${response.status}` };
    }

    const data = await response.json();
    return {
      leads: data.leads || data.results || data.data || [],
      warning: data.warning || ""
    };
  } catch (error) {
    console.error("❌ Error fetching leads meta:", error);
    return { leads: [], warning: "Network error — check if backend is running" };
  }
};

// Search function for Dashboard
export const searchLeads = async (query, location = "Kenya") => {
  try {
    const response = await fetchWithRetry(`${API_URL}/search`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query, location }),
      cache: 'no-store'
    });

    if (!response.ok) {
      console.error(`Search API Error: ${response.status}`);
      // Try GET fallback
      const getResponse = await fetchWithRetry(
        `${API_URL}/search?q=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`,
        { method: "GET", headers }
      );
      if (getResponse.ok) {
        const getData = await getResponse.json();
        return getData.results || getData.leads || getData.data || [];
      }
      return [];
    }

    const data = await response.json();
    return data.results || data.leads || data.data || [];
  } catch (error) {
    console.error("❌ Search error:", error);
    return [];
  }
};

// ============================================================
// AGENTS API
// ============================================================

export const fetchAgents = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/`, { method: "GET", headers });
    if (!response.ok) return [];
    const data = await response.json();
    return data.agents || data.results || data.data || data || [];
  } catch (error) {
    console.error("❌ Error fetching agents:", error);
    return [];
  }
};

export const createAgent = async (agentData) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/`, {
      method: "POST",
      headers,
      body: JSON.stringify(agentData)
    });
    if (!response.ok) {
        const errorData = await response.json();
        return { error: errorData.detail || "Failed to create agent" };
    }
    return await response.json();
  } catch (error) {
    console.error("❌ Error creating agent:", error);
    return { error: error.message };
  }
};

export const deleteAgent = async (agentId) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${agentId}`, { method: "DELETE", headers });
    return response.ok;
  } catch (error) {
    console.error("❌ Error deleting agent:", error);
    return false;
  }
};

export const stopAgent = async (agentId) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${agentId}/stop`, { method: "POST", headers });
    return response.ok;
  } catch (error) {
    console.error("❌ Error stopping agent:", error);
    return false;
  }
};

export const fetchAgentLeads = async (agentId) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${agentId}/leads`, { method: "GET", headers });
    if (!response.ok) return [];
    const data = await response.json();
    return data.leads || data.results || data.data || [];
  } catch (error) {
    console.error("❌ Error fetching agent leads:", error);
    return [];
  }
};

export const exportAgentLeads = async (agentId) => {
  try {
    const response = await fetchWithRetry(`${API_URL}/agents/${agentId}/export`, { method: "GET", headers });
    if (!response.ok) throw new Error("Export failed");
    return await response.blob();
  } catch (error) {
    console.error("❌ Error exporting agent leads:", error);
    throw error;
  }
};

// ============================================================
// NOTIFICATIONS API
// ============================================================

export const fetchNotifications = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/notifications/`, { method: "GET", headers });
    if (!response.ok) return [];
    const data = await response.json();
    return data.notifications || data.results || data.data || [];
  } catch (error) {
    console.error("❌ Error fetching notifications:", error);
    return [];
  }
};

export const fetchNotificationCount = async () => {
  try {
    const response = await fetchWithRetry(`${API_URL}/notifications/count?unread_only=true`, { method: "GET", headers });
    if (!response.ok) return 0;
    const data = await response.json();
    return data.count || 0;
  } catch (error) {
    console.error("❌ Error fetching notification count:", error);
    return 0;
  }
};

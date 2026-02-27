import React, { useState, useEffect } from 'react';
import { fetchAgents, createAgent, deleteAgent, exportAgentLeads, stopAgent } from '../utils/api';

// Direct API call for sync run (bypasses Celery)
const runAgentSync = async (agentId) => {
  console.log('[runAgentSync] Called with agentId:', agentId);
  
  if (!agentId) {
    console.error('[runAgentSync] ERROR: agentId is null/undefined');
    return { status: 'error', message: 'Agent ID is missing' };
  }
  
  // Ensure agentId is a string
  const id = String(agentId).trim();
  console.log('[runAgentSync] Using ID:', id);
  
  try {
    const url = `/api/agents/${id}/run-sync`;
    console.log('[runAgentSync] Fetching:', url);
    
    const response = await fetch(url, { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    console.log('[runAgentSync] Response status:', response.status);
    
    if (!response.ok) {
      const text = await response.text();
      console.error('[runAgentSync] HTTP Error:', response.status, text);
      throw new Error(`HTTP ${response.status}: ${text}`);
    }
    
    const data = await response.json();
    console.log('[runAgentSync] Response data:', data);
    return data;
  } catch (error) {
    console.error('[runAgentSync] Error:', error);
    return { status: 'error', message: error.message };
  }
};

const AgentManager = () => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    query: '',
    location: 'Kenya',
    interval_hours: 2,
    duration_days: 7
  });

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    setLoading(true);
    const data = await fetchAgents();
    setAgents(data);
    setLoading(false);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    console.log("[AgentManager] Submitting form:", formData);
    setLoading(true);
    
    try {
      const result = await createAgent(formData);
      console.log("[AgentManager] Create result:", result);
      
      // Success: result has id and no error
      if (result && result.id && !result.error) {
        console.log("[AgentManager] Agent created:", result.id);
        setAgents([...agents, result]);
        setShowCreate(false);
        setFormData({
          name: '',
          query: '',
          location: 'Kenya',
          interval_hours: 2,
          duration_days: 7
        });
      } 
      // Explicit error from API
      else if (result && result.error) {
        console.error("[AgentManager] API error:", result.error);
        alert("Failed to create agent: " + result.error);
      } 
      // Unexpected response format
      else {
        console.error("[AgentManager] Invalid response:", result);
        alert("Failed to create agent: Server returned unexpected response");
      }
    } catch (err) {
      console.error("[AgentManager] Exception:", err);
      alert("Error creating agent: " + (err.message || "Network error - check console"));
    }
    
    setLoading(false);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this agent?')) {
      await deleteAgent(id);
      setAgents(agents.filter(a => a.id !== id));
    }
  };

  const handleStop = async (id) => {
    if (window.confirm('Are you sure you want to stop this agent?')) {
        await stopAgent(id);
        // Refresh local state
        setAgents(agents.map(a => a.id === id ? { ...a, active: false } : a));
    }
  };

  const handleRunSync = async (id, name) => {
    // DEBUG: Log exactly what we're working with
    console.log("[DEBUG] handleRunSync called with id:", id, "type:", typeof id);
    console.log("[DEBUG] window.location:", window.location.href);
    
    if (!window.confirm(`Run agent "${name}" now? This will execute immediately without Celery.`)) {
      return;
    }
    setLoading(true);
    try {
      const result = await runAgentSync(id);
      console.log("[AgentManager] Run sync result:", result);
      
      if (result.status === 'success') {
        alert(`Agent "${name}" executed successfully!\n\nResult: ${result.result}`);
        // Refresh agents to show updated last_run
        await loadAgents();
      } else {
        alert(`Failed to run agent: ${result.message}`);
      }
    } catch (err) {
      console.error("[AgentManager] Run sync error:", err);
      alert("Error running agent: " + err.message);
    }
    setLoading(false);
  };

  const handleExport = async (id) => {
    const data = await exportAgentLeads(id);
    if (data && data.blob) {
      const url = window.URL.createObjectURL(data.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename || `agent_${id}_export.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString('en-KE', { 
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' 
    });
  };

  return (
    <div className="p-4 bg-gray-900 text-white rounded-lg shadow-xl">
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 mb-6 text-center md:text-left">
        <h2 className="text-2xl font-bold text-blue-400">🕵️ 24/7 Demand Radar Agents</h2>
        <button 
          onClick={() => setShowCreate(!showCreate)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
        >
          {showCreate ? 'Cancel' : '+ Create Agent'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-800 p-6 rounded-lg mb-8 border border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Agent Name</label>
              <input 
                type="text" 
                placeholder="e.g. Water Tanks Hunter"
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Search Query</label>
              <input 
                type="text" 
                placeholder="e.g. water tanks"
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.query}
                onChange={(e) => setFormData({...formData, query: e.target.value})}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Location</label>
              <input 
                type="text" 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.location}
                onChange={(e) => setFormData({...formData, location: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Run Interval (Hours)</label>
              <select 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.interval_hours}
                onChange={(e) => setFormData({...formData, interval_hours: parseInt(e.target.value)})}
              >
                <option value={1}>Every 1 Hour</option>
                <option value={2}>Every 2 Hours</option>
                <option value={6}>Every 6 Hours</option>
                <option value={12}>Every 12 Hours</option>
                <option value={24}>Every 24 Hours</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Duration (Days)</label>
              <input 
                type="number" 
                className="w-full bg-gray-700 border border-gray-600 rounded p-2 focus:outline-none focus:border-blue-500"
                value={formData.duration_days}
                onChange={(e) => setFormData({...formData, duration_days: parseInt(e.target.value)})}
              />
            </div>
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-bold py-2 rounded transition-colors disabled:opacity-50"
          >
            {loading ? 'Deploying Agent...' : '🚀 Deploy Agent'}
          </button>
        </form>
      )}

      {loading && !showCreate ? (
        <div className="text-center py-10">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-400">Loading your agents...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {agents.length === 0 ? (
            <div className="text-center py-10 bg-gray-800 rounded-lg border border-dashed border-gray-700">
              <p className="text-gray-500">No active agents. Create one to start 24/7 monitoring.</p>
            </div>
          ) : (
            agents.map(agent => (
              <div key={agent.id} className="bg-gray-800 p-5 rounded-lg border border-gray-700 shadow-lg">
                {/* Header */}
                <div className="flex flex-col md:flex-row justify-between items-start gap-4 mb-4">
                    <div>
                        <h3 className="text-xl font-bold text-white flex items-center gap-2">
                            {agent.name}
                            <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${agent.active ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                                {agent.active ? 'ACTIVE' : 'STOPPED'}
                            </span>
                        </h3>
                        <p className="text-sm text-gray-400 mt-1">
                            Query: <span className="text-blue-300 font-medium">"{agent.query}"</span> • {agent.location}
                        </p>
                    </div>
                </div>

                {/* Metrics Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 bg-gray-900/50 p-3 rounded-md">
                    <div className="text-center">
                        <p className="text-xs text-gray-500 uppercase">Total Leads</p>
                        <p className="text-2xl font-bold text-white">{agent.leads_count || 0}</p>
                    </div>
                    <div className="text-center">
                        <p className="text-xs text-gray-500 uppercase">High Intent</p>
                        <p className="text-2xl font-bold text-green-400">{agent.high_intent_count || 0}</p>
                    </div>
                    <div className="text-center">
                        <p className="text-xs text-gray-500 uppercase">Next Run</p>
                        <p className="text-sm font-medium text-blue-300 mt-1">{agent.active ? formatDate(agent.next_run_at) : '-'}</p>
                    </div>
                    <div className="text-center">
                        <p className="text-xs text-gray-500 uppercase">Last Run</p>
                        <p className="text-sm font-medium text-gray-300 mt-1">{formatDate(agent.last_run)}</p>
                    </div>
                </div>
                
                {/* Actions */}
                <div className="flex flex-col md:flex-row justify-between items-center border-t border-gray-700 pt-4 gap-4">
                  <div className="text-xs text-gray-500">
                    Runs every {agent.interval_hours}h for {agent.duration_days} days
                  </div>
                  <div className="flex gap-2">
                    <button 
                        onClick={() => handleExport(agent.id)}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors"
                        title="Download Leads"
                    >
                        📥 Download
                    </button>
                    
                    {agent.active && (
                        <button 
                            onClick={() => handleStop(agent.id)}
                            className="bg-orange-900/50 hover:bg-orange-900 text-orange-300 px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors"
                            title="Stop Agent"
                        >
                            🛑 Stop
                        </button>
                    )}

                    {agent.active && (
                        <button 
                            onClick={() => handleRunSync(String(agent.id), agent.name)}
                            disabled={loading}
                            className="bg-blue-900/50 hover:bg-blue-900 text-blue-300 px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors disabled:opacity-50"
                            title="Run Now (No Celery needed)"
                        >
                            ▶️ Run Now
                        </button>
                    )}

                    <button 
                        onClick={() => handleDelete(agent.id)}
                        className="bg-red-900/50 hover:bg-red-900 text-red-300 px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors"
                        title="Delete Agent"
                    >
                        🗑️ Delete
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AgentManager;

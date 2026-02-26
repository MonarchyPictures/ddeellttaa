import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Filter, Zap, MessageSquare, Clock } from 'lucide-react';
import LeadCard from './LeadCard';
import getApiUrl, { getApiKey } from '../config';

const LeadsDrawer = ({ isOpen, onClose, filterType }) => {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && filterType) {
      fetchFilteredLeads();
    }
  }, [isOpen, filterType]);

  const fetchFilteredLeads = async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      
      // Parse the filter string (e.g., /leads?high_intent=true)
      const queryString = filterType.includes('?') ? filterType.split('?')[1] : '';
      const params = new URLSearchParams(queryString);
      params.append('limit', '20');

      const res = await fetch(`${apiUrl}/leads?${params.toString()}`, {
        headers: { 'X-API-Key': apiKey }
      });

      if (!res.ok) throw new Error('Failed to fetch filtered leads');
      
      const data = await res.json();
      const finalLeads = data.leads || (Array.isArray(data) ? data : []);
      
      // Sort by score (Robust Fallback)
      const sorted = [...finalLeads].sort((a, b) => {
        const scoreA = a.buyer_match_score || a.intent_score || 0;
        const scoreB = b.buyer_match_score || b.intent_score || 0;
        return scoreB - scoreA;
      });
      setLeads(sorted);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getTitle = () => {
    if (filterType?.includes('high_intent')) return 'High Intent Signals';
    if (filterType?.includes('has_whatsapp')) return 'WhatsApp Active Leads';
    if (filterType?.includes('24h')) return 'Recent Market Activity';
    return 'Lead Signals';
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60]"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-[#0a0a0b] border-l border-white/10 z-[70] shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-black/20">
              <div>
                <h2 className="text-xl font-black text-white flex items-center gap-2">
                  <Zap className="text-blue-500" size={20} />
                  {getTitle()}
                </h2>
                <p className="text-xs text-white/40 mt-1 uppercase tracking-widest font-bold">
                  Kenya • Live Pipeline
                </p>
              </div>
              <button 
                onClick={onClose}
                className="p-2 hover:bg-white/5 rounded-full text-white/40 hover:text-white transition-colors"
              >
                <X size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-64 space-y-4">
                  <div className="w-12 h-12 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                  <p className="text-white/40 font-bold text-xs uppercase tracking-widest animate-pulse">Syncing market data...</p>
                </div>
              ) : error ? (
                <div className="p-6 bg-red-500/5 border border-red-500/20 rounded-2xl text-center">
                  <p className="text-red-400 text-sm font-bold">{error}</p>
                </div>
              ) : leads.length > 0 ? (
                leads.map((lead, idx) => (
                  <motion.div
                    key={lead.lead_id || idx}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <LeadCard lead={lead} />
                  </motion.div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-center">
                  <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mb-4">
                    <Filter className="text-white/20" size={32} />
                  </div>
                  <h3 className="text-white font-bold">No signals found</h3>
                  <p className="text-white/40 text-sm mt-1">Try expanding your search or wait for new market updates.</p>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-white/10 bg-black/40">
              <button 
                onClick={onClose}
                className="w-full py-4 bg-white/5 hover:bg-white/10 text-white font-bold rounded-2xl transition-all uppercase tracking-widest text-xs"
              >
                Close Panel
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default LeadsDrawer;

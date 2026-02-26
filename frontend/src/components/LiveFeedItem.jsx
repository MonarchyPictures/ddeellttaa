import React from 'react';
import { motion } from 'framer-motion';
import { MapPin, ArrowRight, Zap, Search, MessageSquare } from 'lucide-react';
import getApiUrl, { getApiKey } from '../config';

/**
 * @typedef {import('./LeadCard').Lead} Lead
 */

/**
 * @param {{ lead: Lead, isNew: boolean }} props
 */
const LiveFeedItem = ({ lead, isNew }) => {
  const whatsappUrl = lead.whatsapp_url || lead.whatsapp_link;
  const hasWhatsApp = !!whatsappUrl;

  const handleEngage = async (e, targetUrl = null) => {
    e.stopPropagation();
    try {
      const apiUrl = getApiUrl();
      const apiKey = getApiKey();
      await fetch(`${apiUrl}/outreach/contact/${lead.id}`, {
        method: 'POST',
        headers: {
          'X-API-Key': apiKey
        }
      });
    } catch (err) {
      console.error("Failed to track engagement", err);
    }
    
    if (targetUrl) {
       window.open(targetUrl, '_blank');
    } else {
       window.open(lead.post_link, '_blank');
    }
  };

  return (
    <motion.div
      initial={isNew ? { opacity: 0, x: -20 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={`relative px-6 py-5 hover:bg-white/5 transition-all group cursor-pointer border-l-2 ${
        isNew ? 'bg-blue-500/5 border-blue-500' : 'bg-transparent border-transparent'
      }`}
      onClick={() => window.open(lead.post_link, '_blank')}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-3">
          <div className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-widest flex items-center gap-1.5 border ${
            lead.intent_score > 0.8 
              ? 'bg-red-500/10 text-red-500 border-red-500/20' 
              : 'bg-blue-500/10 text-blue-500 border-blue-500/20'
          }`}>
            {lead.intent_score > 0.8 ? <Zap size={10} className="fill-red-500" /> : <Search size={10} />}
            {lead.intent_score > 0.8 ? 'High Intent' : 'Discovery'}
          </div>
          <span className="text-[9px] text-white/20 font-black uppercase tracking-[0.2em]">{lead.source_platform}</span>
        </div>
        <span className="text-[9px] text-white/20 font-bold uppercase tracking-widest">{lead.time_ago}</span>
      </div>
      
      <p className="text-sm text-white/70 font-medium mb-4 leading-relaxed line-clamp-2 italic">
        "{lead.buyer_request_snippet}"
      </p>
      
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-1.5 text-white/30">
          <MapPin size={12} className="text-blue-500/60" />
          <span className="text-[10px] font-black uppercase tracking-widest">{lead.location_raw}</span>
        </div>
        {hasWhatsApp ? (
          <button 
            onClick={(e) => handleEngage(e, whatsappUrl)}
            className="flex items-center gap-1.5 text-[10px] font-black text-green-500 uppercase tracking-[0.2em] hover:text-green-400 transition-colors group/btn"
          >
            WhatsApp 
            <MessageSquare size={14} className="group-hover/btn:scale-110 transition-transform" />
          </button>
        ) : (
          <button 
            onClick={(e) => handleEngage(e, lead.post_link)}
            className="flex items-center gap-1.5 text-[10px] font-black text-blue-500 uppercase tracking-[0.2em] hover:text-blue-400 transition-colors group/btn"
          >
            Engage 
            <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
          </button>
        )}
      </div>
    </motion.div>
  );
};

export default LiveFeedItem;

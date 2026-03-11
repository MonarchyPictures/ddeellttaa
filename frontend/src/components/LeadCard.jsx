import React, { useState } from 'react';
import {
  Phone,
  ExternalLink,
  MapPin,
  Clock,
  Flame,
  ShieldCheck,
  Mail,
  MessageCircle,
  Globe,
  Activity,
  Check,
  Link2,
  Calendar,
  Users
} from 'lucide-react';
import { motion } from 'framer-motion';
import getApiUrl, { getApiKey } from '../config';

const LeadCard = ({ lead, onSave, onDelete, onClick, onStatusChange, onTap }) => {
  const [copied, setCopied] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [localOutreach, setLocalOutreach] = useState(lead.outreach_suggestion);

  const timeAgo = (date) => {
    if (!date) return "N/A";
    const seconds = Math.floor((new Date() - new Date(date)) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + "y ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + "mo ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + "d ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + "h ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + "m ago";
    return Math.floor(seconds) + "s ago";
  };

  // AI Intent Scoring
  const aiScore = lead.ai_intent_score || 0;
  const aiTemperature = lead.ai_temperature || (aiScore >= 75 ? 'HOT' : aiScore >= 50 ? 'WARM' : aiScore >= 25 ? 'COLD' : 'REJECT');
  const aiReasoning = lead.ai_score_reasoning || '';
  
  const getTemperatureBadge = () => {
    switch(aiTemperature) {
      case 'HOT':
        return { 
          icon: "🔥", 
          label: "HOT LEAD", 
          bg: "bg-red-500", 
          text: "text-white",
          border: "border-red-600"
        };
      case 'WARM':
        return { 
          icon: "☀️", 
          label: "WARM LEAD", 
          bg: "bg-amber-500", 
          text: "text-white",
          border: "border-amber-600"
        };
      case 'COLD':
        return { 
          icon: "❄️", 
          label: "COLD LEAD", 
          bg: "bg-blue-500", 
          text: "text-white",
          border: "border-blue-600"
        };
      default:
        return { 
          icon: "⚪", 
          label: "LOW PRIORITY", 
          bg: "bg-gray-500", 
          text: "text-white",
          border: "border-gray-600"
        };
    }
  };

  const tempBadge = getTemperatureBadge();

  // Field mapping
  const timestamp = lead.timestamp || lead.request_timestamp || lead.created_at;
  const title = lead.title || lead.product || "General Request";
  const location = lead.location || "Kenya";
  const phone = lead.phone || lead.contact_phone;
  const source = lead.source || "Web";
  const sourceUrl = lead.source_url || lead.url;
  const groupName = lead.group_name || lead.subreddit || lead.channel_name || lead.forum_name;
  
  const displayPhone = (phone) => {
    if (!phone) return null;
    if (phone.startsWith('254') && phone.length === 12) {
      return `0${phone.slice(3, 5)} ${phone.slice(5, 8)} ${phone.slice(8)}`;
    }
    return phone;
  };

  const handleContact = async (e) => {
    e.stopPropagation();
    
    if (lead.whatsapp_url || lead.whatsapp_link) {
      setIsGenerating(true);
      try {
        const apiUrl = getApiUrl();
        const apiKey = getApiKey();
        
        const response = await fetch(`${apiUrl}/outreach/${lead.lead_id}/whatsapp`, {
          headers: { 'X-API-Key': apiKey }
        });

        if (response.ok) {
          const data = await response.json();
          window.open(data.url, '_blank');
          if (onTap) onTap(lead.lead_id || lead.id);
        } else {
          const link = lead.whatsapp_url || lead.whatsapp_link;
          if (link) {
            window.open(link, '_blank');
            if (onTap) onTap(lead.lead_id || lead.id);
          }
        }
      } catch (err) {
        console.error("Outreach error:", err);
        const link = lead.whatsapp_url || lead.whatsapp_link;
        if (link) {
          window.open(link, '_blank');
          if (onTap) onTap(lead.lead_id || lead.id);
        }
      } finally {
        setIsGenerating(false);
      }
    } else if (sourceUrl) {
      window.open(sourceUrl, '_blank');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4 }}
      className="bg-[#0A0A0B] border border-white/10 rounded-2xl overflow-hidden relative group hover:border-white/20 transition-all duration-300 shadow-2xl"
    >
      {/* Temperature Header Bar */}
      <div className={`${tempBadge.bg} px-6 py-3 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <span className="text-2xl">{tempBadge.icon}</span>
          <span className={`${tempBadge.text} font-black text-sm uppercase tracking-wider`}>
            {tempBadge.label}
          </span>
          {aiScore > 0 && (
            <span className={`${tempBadge.text} text-xs font-bold ml-2 opacity-80`}>
              {aiScore}/100
            </span>
          )}
        </div>
        {lead.is_verified && (
          <div className="flex items-center gap-1 text-white/90">
            <ShieldCheck size={16} />
            <span className="text-xs font-bold uppercase">Verified</span>
          </div>
        )}
      </div>

      <div className="p-6">
        {/* Product Title */}
        <div className="mb-4">
          <h2 className="text-white font-bold text-xl mb-2">
            {title}
          </h2>
          <div className="flex items-center gap-2 text-white/60 text-sm">
            <Calendar size={14} />
            <span>{timeAgo(timestamp)}</span>
          </div>
        </div>

        {/* Intent Quote */}
        <div className="bg-white/5 rounded-xl p-4 mb-5 border-l-4 border-blue-500">
          <p className="text-white/90 text-lg italic leading-relaxed">
            "{lead.text || lead.buyer_request_snippet || title}"
          </p>
          {aiReasoning && (
            <p className="text-white/40 text-xs mt-2">
              AI Analysis: {aiReasoning}
            </p>
          )}
        </div>

        {/* Trust Info Grid */}
        <div className="grid grid-cols-2 gap-4 mb-5">
          {/* Location */}
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
              <MapPin size={18} className="text-blue-500" />
            </div>
            <div>
              <div className="text-white/40 text-xs font-bold uppercase tracking-wider">Location</div>
              <div className="text-white font-semibold">{location}</div>
            </div>
          </div>
          
          {/* Source */}
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center flex-shrink-0">
              <Globe size={18} className="text-purple-500" />
            </div>
            <div>
              <div className="text-white/40 text-xs font-bold uppercase tracking-wider">Source</div>
              <div className="text-white font-semibold">{source}</div>
            </div>
          </div>
          
          {/* Posted Time */}
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
              <Clock size={18} className="text-amber-500" />
            </div>
            <div>
              <div className="text-white/40 text-xs font-bold uppercase tracking-wider">Posted</div>
              <div className="text-white font-semibold">{timeAgo(timestamp)}</div>
            </div>
          </div>
          
          {/* Group/Channel */}
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center flex-shrink-0">
              <Users size={18} className="text-green-500" />
            </div>
            <div>
              <div className="text-white/40 text-xs font-bold uppercase tracking-wider">
                {source === 'Telegram' ? 'Channel' : source === 'Reddit' ? 'Subreddit' : 'Group'}
              </div>
              <div className="text-white font-semibold truncate max-w-[150px]">
                {groupName || 'Unknown'}
              </div>
            </div>
          </div>
        </div>

        {/* Phone Number - PROMINENT */}
        {phone && (
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center">
                  <Phone size={24} className="text-white" />
                </div>
                <div>
                  <div className="text-green-400 text-xs font-bold uppercase tracking-wider">Phone Number</div>
                  <div className="text-white font-black text-2xl tracking-wide">
                    {displayPhone(phone)}
                  </div>
                </div>
              </div>
              <a 
                href={`tel:${phone}`}
                onClick={(e) => e.stopPropagation()}
                className="bg-green-500 hover:bg-green-400 text-white px-4 py-2 rounded-lg font-bold text-sm uppercase tracking-wider transition-colors"
              >
                Call
              </a>
            </div>
          </div>
        )}

        {/* View Original Post - CRITICAL */}
        {sourceUrl && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              window.open(sourceUrl, '_blank');
            }}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-3 uppercase tracking-wider transition-all active:scale-95 shadow-lg shadow-blue-600/20 mb-2"
          >
            <ExternalLink size={20} />
            View Original Post
            <span className="text-blue-200 text-xs normal-case font-bold">
              ({source})
            </span>
          </button>
        )}
        
        <p className="text-center text-white/30 text-xs mb-5">
          Opens the real message on {source} for verification
        </p>

        {/* Action Buttons */}
        <div className="flex gap-3">
          {(lead.whatsapp_url || lead.whatsapp_link) ? (
            <button
              onClick={handleContact}
              disabled={isGenerating}
              className="flex-1 bg-green-600 hover:bg-green-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-wider transition-all active:scale-95 shadow-lg shadow-green-600/20"
            >
              {isGenerating ? <Activity size={20} className="animate-spin" /> : <MessageCircle size={20} />}
              {isGenerating ? 'Connecting...' : 'WhatsApp'}
            </button>
          ) : (
            <button
              onClick={handleContact}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-black text-sm py-4 rounded-xl flex items-center justify-center gap-2 uppercase tracking-wider transition-all active:scale-95"
            >
              <ExternalLink size={20} />
              View Source
            </button>
          )}
          
          <button
            onClick={async (e) => {
              e.stopPropagation();
              setIsGenerating(true);
              try {
                const apiUrl = getApiUrl();
                const apiKey = getApiKey();
                const res = await fetch(`${apiUrl}/outreach/${lead.lead_id}`, {
                  method: 'POST',
                  headers: { 'X-API-Key': apiKey }
                });
                if (res.ok) {
                  const data = await res.json();
                  await navigator.clipboard.writeText(data.message);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }
              } catch (err) {
                console.error("Copy failed:", err);
              } finally {
                setIsGenerating(false);
              }
            }}
            className={`px-6 py-4 rounded-xl border font-black text-sm uppercase tracking-wider transition-all flex items-center gap-2 ${
              copied 
                ? 'bg-green-500/20 border-green-500 text-green-500' 
                : 'bg-white/5 border-white/10 text-white/60 hover:bg-white/10'
            }`}
          >
            {copied ? <Check size={18} /> : <Mail size={18} />}
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default LeadCard;

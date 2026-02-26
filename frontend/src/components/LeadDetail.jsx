import React, { useState } from 'react';
import { X, Phone, MessageSquare, Bookmark, ExternalLink, MapPin, Clock, Flame, ShieldCheck, Send, CheckCircle2, Trash2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const LeadDetail = ({ lead, onClose, onSave, onDelete, onUpdate }) => {
  const [note, setNote] = useState(lead.notes || '');
  const [status, setStatus] = useState(lead.status || 'not_contacted');
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState(lead.personalized_message || '');

  const handleUpdate = async () => {
    setIsUpdating(true);
    try {
      await onUpdate(lead.id, { status, notes: note });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleSendMessage = async () => {
    if (!message.trim()) return;
    setIsUpdating(true);
    try {
      await onUpdate(lead.id, { personalized_message: message });
      setMessage('');
      alert('Message sent successfully (saved to lead profile)!');
    } catch (err) {
      alert('Failed to save message.');
    } finally {
      setIsUpdating(false);
    }
  };

  const getIntentColor = (score) => {
    if (score >= 0.8) return 'text-red-500 bg-red-500/10 border-red-500/20';
    if (score >= 0.5) return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
    return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
  };

  const getIntentLabel = (score) => {
    if (score >= 0.8) return 'High';
    if (score >= 0.5) return 'Medium';
    return 'Low';
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        className="bg-[#111] border border-white/10 w-full max-w-2xl rounded-2xl overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">Lead Details</h2>
            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border ${getIntentColor(lead.intent_score)}`}>
              {getIntentLabel(lead.intent_score)} Intent
            </span>
          </div>
          <div className="flex items-center gap-2">
            {onDelete && (
              <button 
                onClick={() => {
                  onDelete(lead.id);
                  onClose();
                }}
                className="p-2 hover:bg-red-500/10 rounded-lg transition-colors text-white/40 hover:text-red-500"
                title="Discard Lead"
              >
                <Trash2 size={20} />
              </button>
            )}
            <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-lg transition-colors text-white/40 hover:text-white">
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="flex flex-col md:flex-row h-[70vh] overflow-hidden">
          {/* Left Side: Info */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 border-r border-white/5">
            <div>
              <h3 className="text-white/40 text-xs font-bold uppercase tracking-widest mb-2">Buyer Request</h3>
              <p className="text-lg text-white font-medium leading-relaxed">
                "{lead.buyer_request_snippet}"
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                <div className="flex items-center gap-2 text-white/40 text-xs font-bold uppercase mb-1">
                  <Clock size={12} />
                  Found
                </div>
                <div className="text-white text-sm">
                  {new Date(lead.created_at).toLocaleString()}
                </div>
              </div>
              <div className="bg-white/5 p-4 rounded-xl border border-white/5">
                <div className="flex items-center gap-2 text-white/40 text-xs font-bold uppercase mb-1">
                  <MapPin size={12} />
                  Location
                </div>
                <div className="text-white text-sm">
                  {lead.location_raw || 'Kenya'}
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-white/40 text-xs font-bold uppercase tracking-widest mb-3">Platform & Original Post</h3>
              <div className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500">
                    <ShieldCheck size={20} />
                  </div>
                  <div>
                    <div className="text-white font-medium">{lead.source_platform}</div>
                    <div className="text-white/40 text-xs">Verified Signal</div>
                  </div>
                </div>
                <a 
                  href={lead.post_link} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors text-white/60"
                >
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="flex flex-col md:flex-row gap-3">
              <button 
                onClick={() => onSave(lead.id)}
                className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all border ${lead.is_saved ? 'bg-blue-500/20 border-blue-500/50 text-blue-400' : 'bg-white/5 border-white/10 text-white/40 hover:text-white'}`}
              >
                <Bookmark size={18} fill={lead.is_saved ? 'currentColor' : 'none'} />
                {lead.is_saved ? 'Saved' : 'Save Lead'}
              </button>
              {lead.contact_phone && (
                <a 
                  href={`tel:${lead.contact_phone}`}
                  className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-bold text-sm transition-all shadow-lg shadow-green-900/20"
                >
                  <Phone size={18} />
                  Call Now
                </a>
              )}
            </div>
          </div>

          {/* Right Side - CRM & Actions */}
          <div className="w-full md:w-80 overflow-y-auto p-6 bg-white/[0.02] flex flex-col gap-6">
            <div className="flex items-center justify-between">
              <h3 className="text-white/40 text-xs font-bold uppercase tracking-widest mb-3">Status Management</h3>
              <select 
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="w-full bg-[#1a1a1a] border border-white/10 text-white px-4 py-3 rounded-xl text-sm focus:outline-none focus:border-blue-500/50 mb-3"
              >
                <option value="not_contacted">Not Contacted</option>
                <option value="contacted">Contacted</option>
                <option value="replied">Replied</option>
                <option value="converted">Converted</option>
                <option value="lost">Lost</option>
              </select>
            </div>

            <div>
              <h3 className="text-white/40 text-xs font-bold uppercase tracking-widest mb-3">Internal Notes</h3>
              <textarea 
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Add private notes about this lead..."
                className="w-full bg-[#1a1a1a] border border-white/10 text-white px-4 py-3 rounded-xl text-sm focus:outline-none focus:border-blue-500/50 h-32 resize-none mb-3"
              />
              <button 
                onClick={handleUpdate}
                disabled={isUpdating}
                className="w-full bg-white/5 hover:bg-white/10 text-white py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border border-white/10"
              >
                {isUpdating ? 'Updating...' : 'Save Updates'}
              </button>
            </div>

            <div className="mt-auto pt-6 border-t border-white/5">
              <h3 className="text-white/40 text-xs font-bold uppercase tracking-widest mb-3">Quick Message</h3>
              <div className="relative">
                <textarea 
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type a message..."
                  className="w-full bg-[#1a1a1a] border border-white/10 text-white px-4 py-3 pr-12 rounded-xl text-sm focus:outline-none focus:border-blue-500/50 h-24 resize-none"
                />
                <button 
                  onClick={handleSendMessage}
                  disabled={!message.trim()}
                  className="absolute bottom-3 right-3 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all disabled:opacity-50 disabled:bg-white/10"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default LeadDetail;

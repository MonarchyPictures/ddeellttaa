import React from 'react';

const LeadTable = ({ leads, selected = [], setSelected, onStatusChange, onTap }) => {
  const toggleSelect = (id, e) => {
    if (e) e.stopPropagation();
    if (selected.includes(id)) {
      setSelected(selected.filter(item => item !== id));
    } else {
      setSelected([...selected, id]);
    }
  };

  const handleRowClick = (lead) => {
    // 1. Prioritize WhatsApp flow if link exists
    const contactLink = lead.whatsapp_url || lead.whatsapp_link;
    
    if (contactLink) {
      window.open(contactLink, '_blank');
    } else if (lead.source_url) {
      // 2. Fallback to source URL
      window.open(lead.source_url, '_blank');
    }

    // 3. Log tap callback
    if (onTap) {
      onTap(lead.lead_id || lead.id);
    }
  };

  const toggleSelectAll = () => {
    if (selected.length === leads.length) {
      setSelected([]);
    } else {
      setSelected(leads.map(lead => lead.lead_id || lead.id));
    }
  };

  const isAllSelected = leads.length > 0 && selected.length === leads.length;

  return (
    <div className="w-full overflow-hidden bg-white/5 border border-white/10 rounded-3xl">
      <div className="overflow-x-auto overflow-y-auto max-h-[600px]">
        <table className="w-full text-left border-collapse min-w-[800px]">
          <thead className="sticky top-0 z-10 bg-neutral-900 text-[10px] font-black uppercase tracking-widest text-white/40 border-b border-white/10 shadow-sm">
            <tr>
              <th className="px-6 py-4 w-12">
                <input 
                  type="checkbox" 
                  checked={isAllSelected}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 rounded border-white/10 bg-white/5 checked:bg-blue-600 focus:ring-blue-500/20 cursor-pointer"
                />
              </th>
              <th className="px-6 py-4">Potential Buyer</th>
              <th className="px-6 py-4">Location</th>
              <th className="px-6 py-4">Intent</th>
              <th className="px-6 py-4 text-right">Rank Score</th>
            </tr>
          </thead>
          <tbody className="text-sm">
            {leads && leads.map((lead) => {
              const id = lead.lead_id || lead.id;
              const isSelected = selected.includes(id);
              const isRecent = lead.timestamp && (new Date() - new Date(lead.timestamp)) < 24 * 60 * 60 * 1000;
              const isHighIntent = (lead.ranked_score || lead.intent_score) >= 0.7;
              const hasWhatsApp = !!lead.whatsapp_link;
              
              return (
                <tr 
                  key={id} 
                  className={`border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer ${isSelected ? 'bg-blue-600/5' : ''}`}
                  onClick={() => handleRowClick(lead)}
                >
                  <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                    <input 
                      type="checkbox" 
                      checked={isSelected}
                      onChange={(e) => toggleSelect(id, e)}
                      className="w-4 h-4 rounded border-white/10 bg-white/5 checked:bg-blue-600 focus:ring-blue-500/20 cursor-pointer"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white">{lead.buyer_name || lead.source_name || "Verified Buyer"}</span>
                        <div className="flex flex-wrap items-center gap-2">
                          {isHighIntent && <span title="High intent" className="text-[10px]">🔥</span>}
                          {hasWhatsApp && <span title="WhatsApp active" className="text-[10px]">💬</span>}
                          {isRecent && <span title="Recent activity" className="text-[10px]">⏱</span>}
                        </div>
                      </div>
                      <span className="text-[10px] text-blue-500 font-black uppercase tracking-tighter">{lead.product || "General Vehicle"}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-white/60 italic text-xs">{lead.location_raw || lead.property_city || "Unknown"}</td>
                  <td className="px-6 py-4">
                    <div className="max-w-xs truncate text-white/80 font-medium italic">
                      "{lead.intent_query || lead.intent || "No intent data"}"
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className="bg-blue-600/20 text-blue-400 px-3 py-1 rounded-full text-[10px] font-black border border-blue-500/20">
                      {((lead.ranked_score || lead.buyer_match_score || lead.intent_score || 0) * 100).toFixed(0)}%
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default LeadTable;
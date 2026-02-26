import React, { useState, useEffect, useRef } from 'react';
import LiveFeedItem from './LiveFeedItem';
import { motion, AnimatePresence } from 'framer-motion';
/**
 * @typedef {import('./LeadCard').Lead} Lead
 */

/**
 * @param {{ leads: Lead[] }} props
 */
const LiveFeed = ({ leads: initialLeads }) => {
  const [leads, setLeads] = useState(initialLeads);
  const [isAutoScroll, setIsAutoScroll] = useState(true);
  const scrollRef = useRef(null);
  const lastScrollTop = useRef(0);

  // Update leads when prop changes
  useEffect(() => {
    setLeads(initialLeads);
  }, [initialLeads]);

  // Handle auto-scroll
  useEffect(() => {
    if (isAutoScroll && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  }, [leads, isAutoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    
    const { scrollTop } = scrollRef.current;
    
    // If user scrolls down, disable auto-scroll
    if (scrollTop > 10 && isAutoScroll) {
      setIsAutoScroll(false);
    } 
    // If user scrolls back to top, re-enable auto-scroll
    else if (scrollTop <= 2 && !isAutoScroll) {
      setIsAutoScroll(true);
    }
    
    lastScrollTop.current = scrollTop;
  };

  return (
    <div className="flex-1 h-full overflow-hidden flex flex-col bg-[#050505] border border-white/5 rounded-2xl">
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <h3 className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em] italic">Live Intelligence Stream</h3>
          {isAutoScroll && (
            <div className="flex items-center gap-2 px-2.5 py-1 bg-blue-500/10 rounded-full border border-blue-500/20">
              <span className="relative flex h-1.5 w-1.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-500"></span>
              </span>
              <span className="text-[9px] font-bold text-blue-500 uppercase tracking-widest">Patrolling</span>
            </div>
          )}
        </div>
        
        {!isAutoScroll && (
          <button 
            onClick={() => setIsAutoScroll(true)}
            className="text-[10px] font-bold text-white/40 hover:text-white uppercase tracking-widest transition-all flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/20"
          >
            <div className="w-1 h-1 bg-blue-500 rounded-full animate-pulse" />
            Resume Auto-Sync
          </button>
        )}
      </div>
      
      <div 
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto divide-y divide-white/5 no-scrollbar"
      >
        <AnimatePresence initial={false}>
          {leads.map((lead, index) => (
            <motion.div
              key={lead.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.3 }}
            >
              <LiveFeedItem 
                lead={lead} 
                isNew={index === 0 && leads.length > initialLeads.length} 
              />
            </motion.div>
          ))}
        </AnimatePresence>
        
        {leads.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center py-32 opacity-20">
            <div className="w-10 h-10 border-2 border-dashed border-blue-500 rounded-full animate-spin mb-4" />
            <p className="text-[10px] font-bold uppercase tracking-[0.2em]">Intercepting Signals...</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveFeed;

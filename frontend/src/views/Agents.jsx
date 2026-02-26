import React from 'react';
import AgentManager from '../components/AgentManager';
import { Radar } from 'lucide-react';

const Agents = () => {
  return (
    <div className="flex-1 bg-black overflow-y-auto pt-20 pb-24">
      <div className="max-w-4xl mx-auto px-4 md:px-8">
        <div className="flex flex-col md:flex-row items-center md:items-start gap-3 mb-8 text-center md:text-left">
          <div className="p-3 bg-blue-600/20 rounded-2xl">
            <Radar className="h-8 w-8 text-blue-500" />
          </div>
          <div>
            <h1 className="text-xl md:text-3xl font-black text-white tracking-tight uppercase italic">
              Demand <span className="text-blue-600">Radar</span>
            </h1>
            <p className="text-white/40 text-[10px] font-black uppercase tracking-[0.3em]">
              Autonomous 24/7 Intelligence Agents
            </p>
          </div>
        </div>
        
        <div className="bg-surface-secondary/30 backdrop-blur-xl border border-white/5 rounded-3xl p-1">
          <AgentManager />
        </div>

        <div className="mt-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-white/5 p-6 rounded-3xl border border-white/5">
            <h3 className="text-blue-400 font-bold mb-2 flex items-center gap-2">
              <span className="text-lg">🕒</span> Always On
            </h3>
            <p className="text-white/60 text-sm">
              Agents run every 2 hours to catch new demand before your competitors do.
            </p>
          </div>
          <div className="bg-white/5 p-6 rounded-3xl border border-white/5">
            <h3 className="text-green-400 font-bold mb-2 flex items-center gap-2">
              <span className="text-lg">🚨</span> Instant Alerts
            </h3>
            <p className="text-white/60 text-sm">
              Get notified the second a high-intent buyer is detected in your target location.
            </p>
          </div>
          <div className="bg-white/5 p-6 rounded-3xl border border-white/5">
            <h3 className="text-purple-400 font-bold mb-2 flex items-center gap-2">
              <span className="text-lg">📊</span> Data Export
            </h3>
            <p className="text-white/60 text-sm">
              Download your leads as structured .txt files for your CRM or outreach team.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Agents;

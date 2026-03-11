import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ListFilter, Users, Settings, Radio } from 'lucide-react';

const BottomNav = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const tabs = [
    { path: '/', label: 'Home', icon: LayoutDashboard },
    { path: '/live', label: 'Live', icon: Radio, highlight: true },
    { path: '/leads', label: 'Leads', icon: ListFilter },
    { path: '/agents', label: 'Agents', icon: Users },
    { path: '/settings', label: 'Config', icon: Settings },
  ];

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-black/80 border-t border-white/10 px-2 py-3 z-[100] backdrop-blur-xl">
      <div className="flex justify-around items-center max-w-md mx-auto">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = currentPath === tab.path;
          
          const activeColor = tab.highlight ? 'text-green-400' : 'text-blue-500';
          const activeBg = tab.highlight ? 'bg-green-500/10' : 'bg-blue-500/10';
          
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className={`flex flex-col items-center justify-center min-w-[64px] h-12 gap-1.5 transition-all active:scale-90 touch-none select-none ${
                isActive ? activeColor : 'text-white/40'
              }`}
            >
              <div className={`relative p-2 rounded-xl transition-all duration-300 ${isActive ? `${activeBg} scale-110` : ''}`}>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
                {tab.highlight && !isActive && (
                  <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                )}
              </div>
              <span className={`text-[8px] font-bold uppercase tracking-[0.15em] transition-opacity duration-300 ${isActive ? 'opacity-100' : 'opacity-60'}`}>
                {tab.label}
              </span>
            </Link>
          );
        })}
      </div>
      {/* Safe area for mobile home indicators */}
      <div className="h-4 md:hidden" />
    </nav>
  );
};

export default BottomNav;
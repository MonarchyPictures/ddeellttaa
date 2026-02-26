import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, ListFilter, Users, Settings } from 'lucide-react';

const BottomNav = () => {
  const location = useLocation();
  const currentPath = location.pathname;

  const tabs = [
    { path: '/', label: 'Home', icon: LayoutDashboard },
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
          
          return (
            <Link
              key={tab.path}
              to={tab.path}
              className={`flex flex-col items-center justify-center min-w-[64px] h-12 gap-1.5 transition-all active:scale-90 touch-none select-none ${
                isActive ? 'text-blue-500' : 'text-white/40'
              }`}
            >
              <div className={`p-2 rounded-xl transition-all duration-300 ${isActive ? 'bg-blue-500/10 scale-110' : ''}`}>
                <Icon size={22} strokeWidth={isActive ? 2.5 : 2} />
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
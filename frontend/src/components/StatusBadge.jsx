import React from 'react';

const StatusBadge = ({ status }) => {
  const statusStyles = {
    new: 'bg-blue-50 text-blue-600 border-blue-100',
    contacted: 'bg-amber-50 text-amber-600 border-amber-100',
    converted: 'bg-green-50 text-green-600 border-green-100',
    rejected: 'bg-red-50 text-red-600 border-red-100',
  };

  const statusKey = status?.toLowerCase() || 'new';
  const currentStyle = statusStyles[statusKey] || statusStyles.new;

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-widest border ${currentStyle} shadow-sm inline-flex items-center gap-1.5`}>
      <span className={`w-1 h-1 rounded-full ${
        statusKey === 'new' ? 'bg-blue-600 animate-pulse' : 
        statusKey === 'contacted' ? 'bg-amber-500' :
        statusKey === 'converted' ? 'bg-green-500' : 'bg-red-500'
      }`} />
      {status || 'New'}
    </span>
  );
};

export default StatusBadge;

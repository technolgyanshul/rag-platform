import React from 'react';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: 'active' | 'inactive' | 'processing' | 'error' | 'indexed';
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const variants = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    processing: 'bg-blue-100 text-blue-800',
    error: 'bg-red-100 text-red-800',
    indexed: 'bg-green-100 text-green-800',
  };

  const label = {
    active: 'Active',
    inactive: 'Inactive',
    processing: 'Processing',
    error: 'Error',
    indexed: 'Indexed',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variants[status],
        className
      )}
    >
      {label[status]}
    </span>
  );
}

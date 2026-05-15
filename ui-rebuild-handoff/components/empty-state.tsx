import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <Card className={className}>
      <CardContent className="p-12 text-center">
        <div className="flex flex-col items-center gap-4">
          {Icon && (
            <div className="p-3 rounded-lg bg-muted">
              <Icon size={32} className="text-muted-foreground" />
            </div>
          )}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-foreground">{title}</h3>
            {description && <p className="text-sm text-muted-foreground">{description}</p>}
          </div>
          {action && (
            <Button onClick={action.onClick} variant="default" className="mt-2">
              {action.label}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

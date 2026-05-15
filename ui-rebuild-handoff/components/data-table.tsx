'use client';

import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronRight, Trash2, MoreVertical } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export interface DataTableColumn<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  width?: string;
}

interface DataTableProps<T extends { id: string }> {
  title?: string;
  description?: string;
  columns: DataTableColumn<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  onDelete?: (row: T) => void;
  emptyState?: {
    title: string;
    description: string;
    action?: {
      label: string;
      onClick: () => void;
    };
  };
  loading?: boolean;
}

export function DataTable<T extends { id: string }>({
  title,
  description,
  columns,
  data,
  onRowClick,
  onDelete,
  emptyState,
  loading = false,
}: DataTableProps<T>) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="text-center text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0 && emptyState) {
    return (
      <Card>
        <CardContent className="p-12">
          <div className="text-center space-y-4">
            <h3 className="text-lg font-semibold text-foreground">{emptyState.title}</h3>
            <p className="text-sm text-muted-foreground">{emptyState.description}</p>
            {emptyState.action && (
              <Button onClick={emptyState.action.onClick} variant="default">
                {emptyState.action.label}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      {(title || description) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {description && <p className="text-sm text-muted-foreground mt-2">{description}</p>}
        </CardHeader>
      )}
      <CardContent className="p-0 overflow-x-auto">
        <Table>
          <TableHeader className="bg-muted/50">
            <TableRow>
              {columns.map((column, idx) => (
                <TableHead key={idx} className="font-semibold whitespace-nowrap">
                  {column.header}
                </TableHead>
              ))}
              {(onDelete || onRowClick) && <TableHead className="text-right whitespace-nowrap">Actions</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => (
              <TableRow
                key={row.id}
                className={onRowClick ? 'cursor-pointer hover:bg-muted/50' : ''}
              >
                {columns.map((column, idx) => (
                  <TableCell
                    key={idx}
                    onClick={() => onRowClick?.(row)}
                    className="text-sm whitespace-nowrap"
                  >
                    {column.cell ? column.cell(row) : String(column.accessorKey ? row[column.accessorKey] : '')}
                  </TableCell>
                ))}
                {(onDelete || onRowClick) && (
                  <TableCell className="text-right whitespace-nowrap">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreVertical size={16} />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {onRowClick && (
                          <DropdownMenuItem onClick={() => onRowClick(row)}>
                            <ChevronRight className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                        )}
                        {onDelete && (
                          <DropdownMenuItem
                            onClick={() => onDelete(row)}
                            className="text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

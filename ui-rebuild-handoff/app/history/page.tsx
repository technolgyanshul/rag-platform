'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { DataTable, type DataTableColumn } from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/empty-state';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { History, Download } from 'lucide-react';
import Link from 'next/link';

interface QuerySession {
  id: string;
  query: string;
  agent: string;
  team: string;
  responseTime: string;
  timestamp: string;
}

export default function HistoryPage() {
  const [sessions, setSessions] = useState<QuerySession[]>([
    {
      id: '1',
      query: 'How do I integrate the API?',
      agent: 'Support Agent',
      team: 'Product Team',
      responseTime: '1.2s',
      timestamp: '2024-01-15T14:30:00',
    },
    {
      id: '2',
      query: 'What are the authentication methods?',
      agent: 'Documentation Agent',
      team: 'Engineering',
      responseTime: '0.8s',
      timestamp: '2024-01-15T13:45:00',
    },
    {
      id: '3',
      query: 'How to deploy on production?',
      agent: 'Support Agent',
      team: 'Product Team',
      responseTime: '1.5s',
      timestamp: '2024-01-15T12:20:00',
    },
  ]);

  const [deleteSession, setDeleteSession] = useState<QuerySession | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const columns: DataTableColumn<QuerySession>[] = [
    {
      header: 'Query',
      accessorKey: 'query',
      cell: (row) => <span className="truncate">{row.query}</span>,
    },
    {
      header: 'Agent',
      accessorKey: 'agent',
    },
    {
      header: 'Team',
      accessorKey: 'team',
    },
    {
      header: 'Response Time',
      accessorKey: 'responseTime',
    },
    {
      header: 'Timestamp',
      accessorKey: 'timestamp',
      cell: (row) => new Date(row.timestamp).toLocaleString(),
    },
  ];

  const handleDeleteConfirm = async () => {
    if (!deleteSession) return;
    setIsDeleting(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      setSessions(sessions.filter((s) => s.id !== deleteSession.id));
      setDeleteSession(null);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleExport = () => {
    const csv = [
      ['Query', 'Agent', 'Team', 'Response Time', 'Timestamp'],
      ...sessions.map((s) => [s.query, s.agent, s.team, s.responseTime, s.timestamp]),
    ]
      .map((row) => row.map((cell) => `"${cell}"`).join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'session-history.csv';
    a.click();
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="Session History"
        description="View and export RAG query history"
        actions={
          <Button onClick={handleExport} variant="outline">
            <Download size={18} className="mr-2" />
            Export
          </Button>
        }
      />

      {sessions.length === 0 ? (
        <EmptyState
          icon={History}
          title="No session history"
          description="Your RAG queries and sessions will appear here."
        />
      ) : (
        <DataTable
          title="Query Sessions"
          description={`${sessions.length} sessions recorded`}
          columns={columns}
          data={sessions}
          onDelete={(session) => setDeleteSession(session)}
          emptyState={{
            title: 'No sessions',
            description: 'Your RAG queries will be recorded here',
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteSession}
        title="Delete session?"
        description={`Are you sure you want to delete this session? This action cannot be undone.`}
        actionLabel="Delete Session"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteSession(null)}
      />
    </DashboardLayout>
  );
}

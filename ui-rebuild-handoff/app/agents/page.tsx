'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { DataTable, type DataTableColumn } from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/empty-state';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { Bot, Badge } from 'lucide-react';
import Link from 'next/link';

interface Agent {
  id: string;
  name: string;
  model: string;
  status: 'active' | 'inactive' | 'error';
  team: string;
  createdAt: string;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([
    {
      id: '1',
      name: 'Support Agent',
      model: 'gpt-4',
      status: 'active',
      team: 'Product Team',
      createdAt: '2024-01-15',
    },
    {
      id: '2',
      name: 'Documentation Agent',
      model: 'gpt-3.5-turbo',
      status: 'active',
      team: 'Engineering',
      createdAt: '2024-01-10',
    },
  ]);

  const [deleteAgent, setDeleteAgent] = useState<Agent | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusColor = (status: Agent['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const columns: DataTableColumn<Agent>[] = [
    {
      header: 'Agent Name',
      accessorKey: 'name',
    },
    {
      header: 'Model',
      accessorKey: 'model',
      cell: (row) => <code className="text-xs bg-muted px-2 py-1 rounded">{row.model}</code>,
    },
    {
      header: 'Status',
      accessorKey: 'status',
      cell: (row) => (
        <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(row.status)}`}>
          {row.status.charAt(0).toUpperCase() + row.status.slice(1)}
        </span>
      ),
    },
    {
      header: 'Team',
      accessorKey: 'team',
    },
    {
      header: 'Created',
      accessorKey: 'createdAt',
      cell: (row) => new Date(row.createdAt).toLocaleDateString(),
    },
  ];

  const handleDeleteConfirm = async () => {
    if (!deleteAgent) return;
    setIsDeleting(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      setAgents(agents.filter((a) => a.id !== deleteAgent.id));
      setDeleteAgent(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="AI Agents"
        description="Configure and manage your AI agents"
        actions={
          <Link href="/agents/new">
            <Button>Create Agent</Button>
          </Link>
        }
      />

      {agents.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No agents configured"
          description="Create your first AI agent to start processing RAG queries."
          action={{
            label: 'Create Agent',
            onClick: () => (window.location.href = '/agents/new'),
          }}
        />
      ) : (
        <DataTable
          title="Active Agents"
          columns={columns}
          data={agents}
          onDelete={(agent) => setDeleteAgent(agent)}
          emptyState={{
            title: 'No agents',
            description: 'Create a new agent to get started',
            action: {
              label: 'Create Agent',
              onClick: () => (window.location.href = '/agents/new'),
            },
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteAgent}
        title="Delete agent?"
        description={`Are you sure you want to delete "${deleteAgent?.name}"? This action cannot be undone.`}
        actionLabel="Delete Agent"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteAgent(null)}
      />
    </DashboardLayout>
  );
}

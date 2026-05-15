'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { DataTable, type DataTableColumn } from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/empty-state';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { Users } from 'lucide-react';
import Link from 'next/link';

interface Team {
  id: string;
  name: string;
  members: number;
  createdAt: string;
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([
    {
      id: '1',
      name: 'Product Team',
      members: 5,
      createdAt: '2024-01-15',
    },
    {
      id: '2',
      name: 'Engineering',
      members: 8,
      createdAt: '2024-01-10',
    },
  ]);

  const [deleteTeam, setDeleteTeam] = useState<Team | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const columns: DataTableColumn<Team>[] = [
    {
      header: 'Team Name',
      accessorKey: 'name',
    },
    {
      header: 'Members',
      accessorKey: 'members',
      cell: (row) => `${row.members} members`,
    },
    {
      header: 'Created',
      accessorKey: 'createdAt',
      cell: (row) => new Date(row.createdAt).toLocaleDateString(),
    },
  ];

  const handleDeleteConfirm = async () => {
    if (!deleteTeam) return;
    setIsDeleting(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      setTeams(teams.filter((t) => t.id !== deleteTeam.id));
      setDeleteTeam(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="Teams"
        description="Manage teams and their members for RAG operations"
        actions={
          <Link href="/teams/new">
            <Button>Create Team</Button>
          </Link>
        }
      />

      {teams.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No teams yet"
          description="Create your first team to start managing AI agents and knowledge bases together."
          action={{
            label: 'Create Team',
            onClick: () => (window.location.href = '/teams/new'),
          }}
        />
      ) : (
        <DataTable
          title="Your Teams"
          columns={columns}
          data={teams}
          onDelete={(team) => setDeleteTeam(team)}
          emptyState={{
            title: 'No teams',
            description: 'Create a new team to get started',
            action: {
              label: 'Create Team',
              onClick: () => (window.location.href = '/teams/new'),
            },
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteTeam}
        title="Delete team?"
        description={`Are you sure you want to delete "${deleteTeam?.name}"? This action cannot be undone. All team data and associated agents will be permanently removed.`}
        actionLabel="Delete Team"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTeam(null)}
      />
    </DashboardLayout>
  );
}

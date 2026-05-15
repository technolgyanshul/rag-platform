'use client';

import React, { useState } from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { DataTable, type DataTableColumn } from '@/components/data-table';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/empty-state';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { BookOpen, FileText } from 'lucide-react';
import Link from 'next/link';

interface KnowledgeFile {
  id: string;
  name: string;
  type: string;
  size: string;
  status: 'indexed' | 'processing' | 'error';
  uploadedAt: string;
}

export default function KnowledgePage() {
  const [files, setFiles] = useState<KnowledgeFile[]>([
    {
      id: '1',
      name: 'Product Documentation.pdf',
      type: 'PDF',
      size: '2.4 MB',
      status: 'indexed',
      uploadedAt: '2024-01-15',
    },
    {
      id: '2',
      name: 'API Reference.docx',
      type: 'DOCX',
      size: '1.2 MB',
      status: 'indexed',
      uploadedAt: '2024-01-14',
    },
    {
      id: '3',
      name: 'FAQ.txt',
      type: 'TXT',
      size: '256 KB',
      status: 'processing',
      uploadedAt: '2024-01-13',
    },
  ]);

  const [deleteFile, setDeleteFile] = useState<KnowledgeFile | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const getStatusColor = (status: KnowledgeFile['status']) => {
    switch (status) {
      case 'indexed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const columns: DataTableColumn<KnowledgeFile>[] = [
    {
      header: 'Filename',
      accessorKey: 'name',
      cell: (row) => (
        <div className="flex items-center gap-2">
          <FileText size={16} className="text-muted-foreground" />
          <span>{row.name}</span>
        </div>
      ),
    },
    {
      header: 'Type',
      accessorKey: 'type',
      cell: (row) => <span className="text-xs font-medium">{row.type}</span>,
    },
    {
      header: 'Size',
      accessorKey: 'size',
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
      header: 'Uploaded',
      accessorKey: 'uploadedAt',
      cell: (row) => new Date(row.uploadedAt).toLocaleDateString(),
    },
  ];

  const handleDeleteConfirm = async () => {
    if (!deleteFile) return;
    setIsDeleting(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      setFiles(files.filter((f) => f.id !== deleteFile.id));
      setDeleteFile(null);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="Knowledge Base"
        description="Manage documents and files for RAG indexing"
        actions={
          <Link href="/knowledge/upload">
            <Button>Upload File</Button>
          </Link>
        }
      />

      {files.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No knowledge files yet"
          description="Upload documents to build your knowledge base for AI agents."
          action={{
            label: 'Upload File',
            onClick: () => (window.location.href = '/knowledge/upload'),
          }}
        />
      ) : (
        <DataTable
          title="Knowledge Files"
          description={`${files.length} files indexed and ready for RAG queries`}
          columns={columns}
          data={files}
          onDelete={(file) => setDeleteFile(file)}
          emptyState={{
            title: 'No files',
            description: 'Upload your first knowledge file',
            action: {
              label: 'Upload File',
              onClick: () => (window.location.href = '/knowledge/upload'),
            },
          }}
        />
      )}

      <ConfirmDialog
        open={!!deleteFile}
        title="Delete file?"
        description={`Are you sure you want to delete "${deleteFile?.name}"? This file will be removed from the knowledge base and cannot be recovered.`}
        actionLabel="Delete File"
        cancelLabel="Cancel"
        isDestructive
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteFile(null)}
      />
    </DashboardLayout>
  );
}

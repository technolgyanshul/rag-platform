'use client';

import React from 'react';
import { DashboardLayout } from '@/components/dashboard-layout';
import { PageHeader } from '@/components/page-header';
import { StatCard } from '@/components/stat-card';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BarChart3, Users, BookOpen, MessageSquare } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  return (
    <DashboardLayout user={{ email: 'user@example.com', name: 'John Doe' }}>
      <PageHeader
        title="Dashboard"
        description="Welcome to RAG Ops. Monitor your AI agents and knowledge base."
      />

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
        <StatCard
          title="Total Teams"
          value="3"
          description="Active teams"
          icon={Users}
          trend={{ value: 12, isPositive: true }}
        />
        <StatCard
          title="AI Agents"
          value="12"
          description="Configured agents"
          icon={BarChart3}
          trend={{ value: 8, isPositive: true }}
        />
        <StatCard
          title="Knowledge Files"
          value="248"
          description="Indexed documents"
          icon={BookOpen}
          trend={{ value: 5, isPositive: true }}
        />
        <StatCard
          title="Queries Today"
          value="1,429"
          description="RAG queries processed"
          icon={MessageSquare}
          trend={{ value: 23, isPositive: true }}
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/teams/new" className="block">
              <Button variant="outline" className="w-full justify-start">
                Create New Team
              </Button>
            </Link>
            <Link href="/agents/new" className="block">
              <Button variant="outline" className="w-full justify-start">
                Configure Agent
              </Button>
            </Link>
            <Link href="/knowledge/upload" className="block">
              <Button variant="outline" className="w-full justify-start">
                Upload Knowledge
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4 text-sm">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-foreground">Knowledge file indexed</p>
                  <p className="text-xs text-muted-foreground">5 minutes ago</p>
                </div>
              </div>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-foreground">Agent created</p>
                  <p className="text-xs text-muted-foreground">1 hour ago</p>
                </div>
              </div>
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-medium text-foreground">Team member added</p>
                  <p className="text-xs text-muted-foreground">2 hours ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">System Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">API Health</span>
              <span className="inline-flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-600"></span>
                Operational
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Database</span>
              <span className="inline-flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-600"></span>
                Operational
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Indexing</span>
              <span className="inline-flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                Processing
              </span>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}

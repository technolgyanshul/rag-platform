'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Home,
  Users,
  BookOpen,
  MessageSquare,
  History,
  Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DashboardLayoutProps {
  children: React.ReactNode;
  user?: { email: string; name?: string };
}

export function DashboardLayout({ children, user }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = React.useState(true);
  const pathname = usePathname();

  const navigationItems = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: Home,
    },
    {
      label: 'Teams',
      href: '/teams',
      icon: Users,
    },
    {
      label: 'Agents',
      href: '/agents',
      icon: Bot,
    },
    {
      label: 'Knowledge',
      href: '/knowledge',
      icon: BookOpen,
    },
    {
      label: 'Chat',
      href: '/chat',
      icon: MessageSquare,
    },
    {
      label: 'History',
      href: '/history',
      icon: History,
    },
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'bg-sidebar text-sidebar-foreground border-r border-sidebar-border transition-all duration-300 fixed md:relative z-40',
          sidebarOpen ? 'w-64' : 'w-0 md:w-64'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-sidebar-border">
            <Link href="/dashboard" className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded bg-sidebar-primary text-sidebar-primary-foreground">
                <BarChart3 size={20} />
              </div>
              <span className="font-semibold text-lg">RAG Ops</span>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-4 px-3">
            <ul className="space-y-2">
              {navigationItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={cn(
                        'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors',
                        active
                          ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                          : 'text-sidebar-foreground hover:bg-sidebar-accent'
                      )}
                    >
                      <Icon size={20} />
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Footer */}
          <div className="border-t border-sidebar-border p-4 space-y-2">
            <Link
              href="/profile"
              className={cn(
                'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors text-sm',
                pathname === '/profile'
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent'
              )}
            >
              <Settings size={20} />
              <span>Profile</span>
            </Link>
            <button className="w-full flex items-center gap-3 px-4 py-2 rounded-lg transition-colors text-sidebar-foreground hover:bg-sidebar-accent text-sm">
              <LogOut size={20} />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 md:hidden z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col w-full">
        {/* Header */}
        <header className="bg-card border-b border-border px-4 md:px-6 py-4 flex items-center justify-between sticky top-0 z-20">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="text-foreground hover:bg-muted rounded-lg p-2 transition-colors md:hidden"
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          <div className="hidden md:block text-foreground text-sm">
            {user && (
              <span>
                Welcome, <span className="font-semibold">{user.name || user.email}</span>
              </span>
            )}
          </div>
          <div className="md:hidden text-foreground text-sm font-semibold">
            RAG Ops
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          <div className="p-4 md:p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}

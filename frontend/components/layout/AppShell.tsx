"use client";

import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { Header } from "./Header";
import { NavItem, Sidebar } from "./Sidebar";

type AppShellProps = {
  title: string;
  subtitle: string;
  actions?: ReactNode;
  children: ReactNode;
};

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/knowledge", label: "Knowledge Base", icon: "database" },
  { href: "/chat", label: "Chat Workspace", icon: "forum" },
  { href: "/history", label: "Query Logs", icon: "history" },
  { href: "/team", label: "Team Management", icon: "group" },
  { href: "/profile", label: "Profile", icon: "account_circle" },
];

export function AppShell({ title, subtitle, actions, children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <div className="app-shell">
      <div className="side-nav--desktop">
        <Sidebar navItems={navItems} activePath={pathname} />
      </div>

      {mobileOpen ? <button type="button" className="mobile-overlay" onClick={() => setMobileOpen(false)} aria-label="Close navigation" /> : null}

      <div className={`mobile-drawer${mobileOpen ? " is-open" : ""}`}>
        <Sidebar navItems={navItems} activePath={pathname} onNavigate={() => setMobileOpen(false)} mobile />
      </div>

      <div className="shell-main">
        <Header onMenuClick={() => setMobileOpen(true)} />

        <main className="shell-content">
          <section className="page-header">
            <div>
              <h2>{title}</h2>
              <p>{subtitle}</p>
            </div>
            {actions ? <div className="page-header__actions">{actions}</div> : null}
          </section>
          {children}
        </main>
      </div>
    </div>
  );
}

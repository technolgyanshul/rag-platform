"use client";

import { usePathname } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";

import { Header } from "./Header";
import { NavItem, Sidebar } from "./Sidebar";
import { fieldOnlyClipboardText } from "../../lib/clipboard";

type AppShellProps = {
  title: string;
  subtitle: string;
  actions?: ReactNode;
  children: ReactNode;
};

const navItems: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { href: "/teams", label: "Teams", icon: "groups" },
  { href: "/knowledge", label: "Knowledge Base", icon: "database" },
  { href: "/chat", label: "Chat Workspace", icon: "forum" },
  { href: "/history", label: "Query Logs", icon: "history" },
  { href: "/profile", label: "Profile", icon: "account_circle" },
];

/** Shared authenticated shell with sidebar, header, and page content container. */
export function AppShell({ title, subtitle, actions, children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleCopy = (event: ClipboardEvent) => {
      const clipboardText = fieldOnlyClipboardText(document.activeElement);
      if (clipboardText === null || !event.clipboardData) {
        return;
      }
      event.clipboardData.setData("text/plain", clipboardText);
      event.preventDefault();
    };
    document.addEventListener("copy", handleCopy, true);
    return () => {
      document.removeEventListener("copy", handleCopy, true);
    };
  }, []);

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
              <p className="page-kicker">RAG Ops Console</p>
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

import Link from "next/link";

export type NavItem = {
  href: string;
  label: string;
  icon: string;
};

type SidebarProps = {
  navItems: NavItem[];
  activePath: string;
  onNavigate?: () => void;
  mobile?: boolean;
};

export function Sidebar({ navItems, activePath, onNavigate, mobile = false }: SidebarProps) {
  return (
    <aside className={`side-nav${mobile ? " side-nav--mobile" : ""}`}>
      <div className="side-nav__brand">
        <div className="brand-mark">
          <span className="material-symbols-outlined">memory</span>
        </div>
        <div>
          <h1>RAG Ops</h1>
          <p>Retrieval System</p>
        </div>
      </div>

      <nav className="side-nav__links">
        {navItems.map((item) => {
          const active = activePath === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link${active ? " is-active" : ""}`}
              onClick={onNavigate}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

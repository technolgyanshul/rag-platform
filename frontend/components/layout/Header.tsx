type HeaderProps = {
  onMenuClick?: () => void;
};

/** Top app header with mobile menu trigger and branding. */
export function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="top-bar">
      <div className="top-bar__left">
        <button type="button" className="top-bar__menu" onClick={onMenuClick} aria-label="Open navigation menu">
          <span className="material-symbols-outlined">menu</span>
        </button>
        <div className="top-bar__search">
          <span className="material-symbols-outlined">search</span>
          <input type="text" placeholder="Search workspace" readOnly />
        </div>
      </div>
      <div className="top-bar__actions" aria-hidden>
        <span className="top-bar__status-dot" />
        <span>Operational</span>
      </div>
    </header>
  );
}

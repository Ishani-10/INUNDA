export default function Header({ view, setView, revision, ml }: {
  view: string; setView: (v: string) => void; revision: number; ml: boolean;
}) {
  const tabs = [
    { id: "nowcast", label: "Nowcast" },
    { id: "routes", label: "Flood-Safe Routes" },
    { id: "ml", label: "ML Model" },
  ];
  return (
    <header className="topbar">
      <div className="brand">
        <span className="brandmark">INUNDA</span>
        <span className="brandsub">Urban Flood Nowcast · 26085</span>
      </div>
      <nav className="tabs">
        {tabs.map((t) => (
          <button key={t.id} className={view === t.id ? "tab active" : "tab"}
            onClick={() => setView(t.id)}>{t.label}</button>
        ))}
      </nav>
      <div className="meta">
        <span className="pill">rev {revision}</span>
        <span className={"pill " + (ml ? "ok" : "")}>ML {ml ? "trained" : "loading"}</span>
      </div>
    </header>
  );
}

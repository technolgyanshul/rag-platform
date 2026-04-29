import Link from "next/link";

const links = [
  "login",
  "register",
  "profile",
  "dashboard",
  "team",
  "knowledge",
  "chat",
  "history"
];

export default function HomePage() {
  return (
    <main className="container">
      <h1>Multi-Agent RAG Platform</h1>
      <p>Phase 1 scaffold is ready.</p>
      <div className="card">
        <h2>App Routes</h2>
        <ul>
          {links.map((link) => (
            <li key={link}>
              <Link href={`/${link}`}>/{link}</Link>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}

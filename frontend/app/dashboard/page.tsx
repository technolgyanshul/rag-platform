"use client";

import { ProtectedPage } from "../../components/auth/ProtectedPage";

export default function DashboardPage() {
  return (
    <ProtectedPage>
      <main className="container">Dashboard page scaffold</main>
    </ProtectedPage>
  );
}

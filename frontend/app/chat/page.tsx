"use client";

import { ProtectedPage } from "../../components/auth/ProtectedPage";

export default function ChatPage() {
  return (
    <ProtectedPage>
      <main className="container">Chat page scaffold</main>
    </ProtectedPage>
  );
}

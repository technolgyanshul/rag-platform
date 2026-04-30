"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { supabase } from "../../lib/supabase";

export default function ProfilePage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const loadUser = async () => {
      const {
        data: { user },
        error
      } = await supabase.auth.getUser();

      if (error || !user) {
        setMessage("Could not load profile.");
        setLoading(false);
        return;
      }

      setEmail(user.email ?? "");
      setLoading(false);
    };

    void loadUser();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  return (
    <ProtectedPage>
      <AppShell
        title="User Profile"
        subtitle="Manage identity metadata and active account access"
        actions={
          <button type="button" onClick={handleLogout}>
            Log out
          </button>
        }
      >
        <div className="split-2">
          <div className="card">
            <h3 style={{ marginBottom: 8 }}>Operator Identity</h3>
            {loading ? <p className="status-message">Loading profile...</p> : <p>Email: {email || "Unavailable"}</p>}
            <p className="status-message" style={{ marginTop: 10 }}>
              Role: Senior Operator
            </p>
            <p className="status-message">Environment: Light Theme Console</p>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 8 }}>Security Protocol</h3>
            <ul className="history-list">
              <li className="history-item">
                <strong>Two-Factor Authentication</strong>
                <p className="status-message">Recommended for admin-level accounts.</p>
              </li>
              <li className="history-item">
                <strong>API Tokens</strong>
                <p className="status-message">Rotate service tokens every 30 days.</p>
              </li>
            </ul>
          </div>
        </div>
        {message ? <p className="status-message">{message}</p> : null}
      </AppShell>
    </ProtectedPage>
  );
}

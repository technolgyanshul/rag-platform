"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
import { AppShell } from "../../components/layout/AppShell";
import { createClient } from "@/utils/supabase/client";

export default function ProfilePage() {
  const router = useRouter();
  const [email, setEmail] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const loadUser = async () => {
      const supabase = createClient();
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
    await createClient().auth.signOut();
    router.push("/login");
  };

  return (
    <ProtectedPage>
      <AppShell
        title="User Profile"
        subtitle="Manage active account access"
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
            <p className="status-message" style={{ marginTop: 10 }}>Identity data is sourced from your current Supabase session.</p>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 8 }}>Session</h3>
            <p className="status-message">Use the logout action to revoke the local browser session.</p>
          </div>
        </div>
        {message ? <p className="status-message">{message}</p> : null}
      </AppShell>
    </ProtectedPage>
  );
}

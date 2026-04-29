"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ProtectedPage } from "../../components/auth/ProtectedPage";
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
      <main className="container">
        <div className="card auth-card">
          <h1>Profile</h1>
          {loading ? <p>Loading profile...</p> : <p>Email: {email || "Unavailable"}</p>}
          {message && <p className="status-message">{message}</p>}
          <button type="button" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </main>
    </ProtectedPage>
  );
}

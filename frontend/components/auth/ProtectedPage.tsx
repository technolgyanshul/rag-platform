"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { createClient } from "@/utils/supabase/client";

type ProtectedPageProps = {
  children: React.ReactNode;
};

export function ProtectedPage({ children }: ProtectedPageProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
      const supabase = createClient();
      const { data, error } = await supabase.auth.getSession();
      if (error || !data.session) {
        router.replace("/login");
        return;
      }
      setLoading(false);
    };

    void checkSession();
  }, [router]);

  if (loading) {
    return (
      <main className="auth-page">
        <div className="card auth-card">
          <p className="status-message">Checking your session...</p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { supabase } from "../../lib/supabase";

type ProtectedPageProps = {
  children: React.ReactNode;
};

export function ProtectedPage({ children }: ProtectedPageProps) {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkSession = async () => {
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
      <main className="container">
        <p>Checking your session...</p>
      </main>
    );
  }

  return <>{children}</>;
}

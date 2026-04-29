"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { supabase } from "../../lib/supabase";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleRegister = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const { error } = await supabase.auth.signUp({ email, password });
      if (error) {
        setMessage(error.message);
        setLoading(false);
        return;
      }

      setMessage("Registration successful. You can now sign in.");
      router.push("/login");
    } catch {
      setMessage("Registration failed due to a network or server error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="container">
      <div className="card auth-card">
        <h1>Register</h1>
        <form className="auth-form" onSubmit={handleRegister}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={6}
          />

          <button type="submit" disabled={loading}>
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>

        {message && <p className="status-message">{message}</p>}

        <p>
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </main>
  );
}

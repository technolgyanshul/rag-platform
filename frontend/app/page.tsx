import { redirect } from "next/navigation";

/** Root route redirect to login entrypoint. */
export default function HomePage() {
  redirect("/login");
}

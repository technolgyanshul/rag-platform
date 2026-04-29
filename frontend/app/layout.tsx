import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RAG Platform",
  description: "Multi-agent multi-model RAG research platform"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

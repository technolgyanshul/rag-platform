import "./globals.css";
import type { Metadata } from "next";
import localFont from "next/font/local";

const inter = localFont({
  variable: "--font-inter",
  src: [
    { path: "../public/fonts/inter-100.ttf", weight: "100", style: "normal" },
    { path: "../public/fonts/inter-200.ttf", weight: "200", style: "normal" },
    { path: "../public/fonts/inter-300.ttf", weight: "300", style: "normal" },
    { path: "../public/fonts/inter-400.ttf", weight: "400", style: "normal" },
    { path: "../public/fonts/inter-500.ttf", weight: "500", style: "normal" },
    { path: "../public/fonts/inter-600.ttf", weight: "600", style: "normal" },
    { path: "../public/fonts/inter-700.ttf", weight: "700", style: "normal" },
    { path: "../public/fonts/inter-800.ttf", weight: "800", style: "normal" },
    { path: "../public/fonts/inter-900.ttf", weight: "900", style: "normal" },
  ],
});

const spaceGrotesk = localFont({
  variable: "--font-space",
  src: [
    { path: "../public/fonts/space-grotesk-300.ttf", weight: "300", style: "normal" },
    { path: "../public/fonts/space-grotesk-400.ttf", weight: "400", style: "normal" },
    { path: "../public/fonts/space-grotesk-500.ttf", weight: "500", style: "normal" },
    { path: "../public/fonts/space-grotesk-600.ttf", weight: "600", style: "normal" },
    { path: "../public/fonts/space-grotesk-700.ttf", weight: "700", style: "normal" },
  ],
});

export const metadata: Metadata = {
  title: "RAG Ops",
  description: "Operator console for RAG workflows"
};

/** Global app layout applying local fonts and baseline HTML structure. */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${spaceGrotesk.variable}`}>{children}</body>
    </html>
  );
}

import { describe, expect, it } from "vitest";

// TypeScript cannot infer types for local .mjs config imports in this test context.
// @ts-expect-error - covered by runtime test expectations below.
import nextConfig from "./next.config.mjs";

describe("nextConfig", () => {
  it("rewrites /api requests to the internal backend without the /api prefix", async () => {
    const rewrites = await nextConfig.rewrites();

    expect(rewrites).toEqual([
      {
        source: "/api/:path*",
        destination: "https://backend:8000/:path*",
      },
    ]);
  });

  it("allows the Cloudflare tunnel host to access Next.js dev resources", () => {
    expect(nextConfig.allowedDevOrigins).toContain("rag.anshul-garg.com");
  });
});

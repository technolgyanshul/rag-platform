import { describe, expect, it } from "vitest";

import nextConfig from "./next.config.mjs";

describe("nextConfig", () => {
  it("rewrites /api requests to the internal backend without the /api prefix", async () => {
    const rewrites = await nextConfig.rewrites();

    expect(rewrites).toEqual([
      {
        source: "/api/:path*",
        destination: "http://backend:8000/:path*",
      },
    ]);
  });
});

/** @type {import('next').NextConfig} */
const apiInternalBaseUrl = process.env.API_INTERNAL_BASE_URL || "https://backend:8000";

const nextConfig = {
  allowedDevOrigins: ["rag.anshul-garg.com"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiInternalBaseUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;

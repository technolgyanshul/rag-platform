/** @type {import('next').NextConfig} */
const apiInternalBaseUrl = process.env.API_INTERNAL_BASE_URL || "http://backend:8000";

const nextConfig = {
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

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: { unoptimized: true },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/backend/:path*", destination: `${api}/api/v1/:path*` },
    ];
  },
};
module.exports = nextConfig;

/** @type {import('next').NextConfig} */
const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8001";

const nextConfig = {
  // Self-contained server bundle for the Docker image.
  output: "standalone",
  // The browser only talks to this origin; Next forwards /api/* to the planner API.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }];
  },
  poweredByHeader: false,
};

export default nextConfig;

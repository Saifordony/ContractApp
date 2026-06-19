/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The FastAPI backend base URL. Same-origin /api in production behind a proxy,
  // or set NEXT_PUBLIC_BACKEND_URL to point directly at the backend in dev.
};
export default nextConfig;

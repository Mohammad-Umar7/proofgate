/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the demo (replays, galaxy, bench) works on any static host with no backend.
  // When NEXT_PUBLIC_API_URL points at a running engine, the console switches to live mode.
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  reactStrictMode: true,
  agentRules: false,
  transpilePackages: ["three"],
};

export default nextConfig;

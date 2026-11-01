import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Set only by the Docker build, so `next dev` and Vercel are unaffected.
  // Produces .next/standalone with its own minimal server.js.
  output: process.env.DOCKER_BUILD ? "standalone" : undefined,
  // Limits build workers: the default of one per CPU core can exhaust memory on a laptop.
  experimental: { cpus: 2 },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

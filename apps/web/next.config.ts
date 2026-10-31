import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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

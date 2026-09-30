import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // small, self-contained production image (see frontend/Dockerfile)
};

export default nextConfig;

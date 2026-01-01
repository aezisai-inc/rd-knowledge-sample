/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  env: {
    NEXT_PUBLIC_API_ENDPOINT:
      process.env.NEXT_PUBLIC_API_ENDPOINT ||
      "https://tc3gjfcpf1.execute-api.ap-northeast-1.amazonaws.com/dev",
  },
};

module.exports = nextConfig;


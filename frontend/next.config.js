/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_DEPLOYMENT_ENV: process.env.DEPLOYMENT_ENV || "itc",
  },
};

module.exports = nextConfig;

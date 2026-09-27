/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['*.pinggy-free.link', '*.free.pinggy.net', '*.pinggy.io', 'localhost', '127.0.0.1'],
  async rewrites() {
    return [
      {
        source: '/detect-corners',
        destination: 'http://127.0.0.1:8000/detect-corners',
      },
      {
        source: '/scan-pro',
        destination: 'http://127.0.0.1:8000/scan-pro',
      },
      {
        source: '/api/ocr',
        destination: 'http://127.0.0.1:8000/api/ocr',
      },
      {
        source: '/api/validate-document',
        destination: 'http://127.0.0.1:8000/api/validate-document',
      },
      {
        source: '/api/detect-tampering',
        destination: 'http://127.0.0.1:8000/api/detect-tampering',
      },
      {
        source: '/api/verify-face',
        destination: 'http://127.0.0.1:8000/api/verify-face',
      },
      {
        source: '/api/save-verified-user',
        destination: 'http://127.0.0.1:8000/api/save-verified-user',
      },
      {
        source: '/backend/:path*',
        destination: 'http://127.0.0.1:8000/:path*',
      },
    ];
  },
};

export default nextConfig;

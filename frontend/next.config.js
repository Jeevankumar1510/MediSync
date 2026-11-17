/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://127.0.0.1:8000/api/v1/:path*',
      },
      {
        source: '/monitoring/:path*',
        destination: 'http://127.0.0.1:8000/monitoring/:path*',
      },
      {
        source: '/auth/:path*',
        destination: 'http://127.0.0.1:8000/auth/:path*',
      },
      {
        source: '/patients/:path*',
        destination: 'http://127.0.0.1:8000/patients/:path*',
      },
      {
        source: '/integrations/:path*',
        destination: 'http://127.0.0.1:8000/integrations/:path*',
      },
      {
        source: '/normalization/:path*',
        destination: 'http://127.0.0.1:8000/normalization/:path*',
      },
      {
        source: '/sync/:path*',
        destination: 'http://127.0.0.1:8000/sync/:path*',
      },
      {
        source: '/webhooks/:path*',
        destination: 'http://127.0.0.1:8000/webhooks/:path*',
      },
      {
        source: '/ai/:path*',
        destination: 'http://127.0.0.1:8000/ai/:path*',
      },
      {
        source: '/rag/:path*',
        destination: 'http://127.0.0.1:8000/rag/:path*',
      },
    ];
  },
};

module.exports = nextConfig;

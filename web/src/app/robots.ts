import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/api/',
          '/dashboard',
          '/account',
          '/billing',
          '/journal',
          '/intelligence/setups',
          '/intelligence/scanner',
          '/auth/',
        ],
      },
      {
        // Allow Google News bot full access to news content
        userAgent: 'Googlebot-News',
        allow: '/post/',
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}

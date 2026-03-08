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
        // Allow Google News bot full access to news and analysis content
        userAgent: 'Googlebot-News',
        allow: ['/post/', '/news', '/analysis'],
      },
    ],
    sitemap: [`${BASE_URL}/sitemap.xml`, `${BASE_URL}/news-sitemap.xml`],
    host: BASE_URL,
  };
}

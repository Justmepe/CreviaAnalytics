import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';
const API_URL  = process.env.NEXT_PUBLIC_API_URL  || 'http://localhost:8000';

async function fetchAllPostSlugs(): Promise<{ slug: string; published_at: string; content_type: string }[]> {
  try {
    const res = await fetch(`${API_URL}/api/content/feed?page_size=500&page=1`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.items || data.posts || []).map((p: { slug: string; published_at: string; content_type: string }) => ({
      slug: p.slug,
      published_at: p.published_at,
      content_type: p.content_type,
    }));
  } catch {
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const posts = await fetchAllPostSlugs();

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE_URL,                      lastModified: new Date(), changeFrequency: 'hourly',  priority: 1.0 },
    { url: `${BASE_URL}/analysis`,        lastModified: new Date(), changeFrequency: 'hourly',  priority: 0.9 },
    { url: `${BASE_URL}/pricing`,         lastModified: new Date(), changeFrequency: 'monthly', priority: 0.7 },
    { url: `${BASE_URL}/about`,           lastModified: new Date(), changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE_URL}/privacy`,         lastModified: new Date(), changeFrequency: 'yearly',  priority: 0.3 },
    { url: `${BASE_URL}/waitlist`,        lastModified: new Date(), changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE_URL}/whale-tracker`,   lastModified: new Date(), changeFrequency: 'hourly',  priority: 0.8 },
    { url: `${BASE_URL}/intelligence`,    lastModified: new Date(), changeFrequency: 'hourly',  priority: 0.8 },
  ];

  const postPages: MetadataRoute.Sitemap = posts.map((p) => ({
    url: `${BASE_URL}/post/${p.slug}`,
    lastModified: new Date(p.published_at),
    changeFrequency: 'weekly' as const,
    priority: p.content_type === 'article' ? 0.9 : 0.7,
  }));

  return [...staticPages, ...postPages];
}

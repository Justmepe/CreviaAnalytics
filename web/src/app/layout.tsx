import type { Metadata } from "next";
import { Bebas_Neue, DM_Mono, DM_Sans, Instrument_Serif, Syne } from "next/font/google";
import { Suspense } from "react";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import LiveMarketBar from "@/components/layout/LiveMarketBar";
import Footer from "@/components/layout/Footer";
import { AuthProvider } from "@/context/AuthContext";
import { MarketPricesProvider } from "@/context/MarketPricesContext";
import { getLatestPrices } from "@/lib/api";

const bebasNeue = Bebas_Neue({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-bebas",
  display: "swap",
});

const dmMono = DM_Mono({
  weight: ["300", "400", "500"],
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const dmSans = DM_Sans({
  weight: ["300", "400", "500", "600"],
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const instrumentSerif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const syne = Syne({
  weight: ["400", "500", "600", "700", "800"],
  subsets: ["latin"],
  variable: "--font-syne",
  display: "swap",
});

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://creviacockpit.com';

export const metadata: Metadata = {
  metadataBase: new URL(BASE_URL),
  title: {
    default: "CreviaCockpit | Crypto Market Intelligence",
    template: "%s | CreviaCockpit",
  },
  description:
    "Real-time crypto market analysis covering 16+ assets across majors, DeFi, privacy coins, and memecoins. Market memos, analysis threads, and risk alerts.",
  keywords: [
    "crypto analysis", "bitcoin analysis", "ethereum analysis", "crypto market intelligence",
    "DeFi analytics", "crypto research", "bitcoin price", "altcoin analysis",
    "crypto trading", "on-chain data", "whale tracking", "crypto news",
  ],
  authors: [{ name: 'CreviaCockpit', url: BASE_URL }],
  creator: 'CreviaCockpit',
  publisher: 'CreviaCockpit',
  alternates: { canonical: BASE_URL },
  openGraph: {
    type: 'website',
    siteName: 'CreviaCockpit',
    url: BASE_URL,
    title: 'CreviaCockpit | Crypto Market Intelligence',
    description: 'Real-time crypto market analysis covering 16+ assets. Market memos, analysis threads, whale tracking, and risk alerts.',
    images: [{ url: '/og-default.png', width: 1200, height: 630, alt: 'CreviaCockpit Crypto Intelligence' }],
  },
  twitter: {
    card: 'summary_large_image',
    site: '@CreviaCockpit',
    creator: '@CreviaCockpit',
    title: 'CreviaCockpit | Crypto Market Intelligence',
    description: 'Real-time crypto market analysis. Market memos, analysis threads, whale tracking, and risk alerts.',
    images: ['/og-default.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, 'max-snippet': -1, 'max-image-preview': 'large', 'max-video-preview': -1 },
  },
  icons: {
    icon: "/favicon.png",
    shortcut: "/favicon.png",
    apple: "/favicon.png",
  },
  verification: {
    google: process.env.GOOGLE_SITE_VERIFICATION || '',
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // Fetch once server-side for SSR initial state — cached 60s by fetchAPI
  const initialPrices = await getLatestPrices().catch(() => []);

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        {/* Google AdSense — ca-pub-2327890732767084 */}
        {process.env.NEXT_PUBLIC_ADSENSE_PUB_ID && (
          <script
            async
            src={`https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=${process.env.NEXT_PUBLIC_ADSENSE_PUB_ID}`}
            crossOrigin="anonymous"
          />
        )}
      </head>
      <body
        suppressHydrationWarning
        className={`${bebasNeue.variable} ${dmMono.variable} ${dmSans.variable} ${instrumentSerif.variable} ${syne.variable} font-sans antialiased`}
        style={{ background: '#08090c', color: '#dfe3f0' }}
      >
        <MarketPricesProvider initialPrices={initialPrices}>
          <AuthProvider>
            <Navbar />
            <LiveMarketBar />
            <main className="min-h-screen">
              <Suspense>{children}</Suspense>
            </main>
            <Footer />
          </AuthProvider>
        </MarketPricesProvider>
      </body>
    </html>
  );
}

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

export const metadata: Metadata = {
  title: {
    default: "CreviaCockpit | Crypto Market Intelligence",
    template: "%s | CreviaCockpit",
  },
  description:
    "Real-time crypto market analysis covering 16+ assets across majors, DeFi, privacy coins, and memecoins. Market memos, analysis threads, and risk alerts.",
  keywords: [
    "crypto analysis",
    "bitcoin",
    "ethereum",
    "market intelligence",
    "DeFi",
    "crypto research",
  ],
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

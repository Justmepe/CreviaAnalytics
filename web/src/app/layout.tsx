import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import LiveMarketBar from "@/components/layout/LiveMarketBar";
import Footer from "@/components/layout/Footer";
import { AuthProvider } from "@/context/AuthContext";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: {
    default: "Crevia Analytics | Crypto Market Intelligence",
    template: "%s | Crevia Analytics",
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} font-sans bg-zinc-950 text-zinc-100 antialiased`}
      >
        <AuthProvider>
          <Navbar />
          <LiveMarketBar />
          <main className="min-h-screen">{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}

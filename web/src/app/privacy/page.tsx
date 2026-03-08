import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy',
  description: 'CreviaCockpit privacy policy — how we collect, use, and protect your data.',
  robots: { index: true, follow: false },
};

export default function PrivacyPage() {
  const lastUpdated = 'March 2026';

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
      <p className="text-sm text-zinc-500 mb-10">Last updated: {lastUpdated}</p>

      <div className="prose prose-invert prose-zinc max-w-none space-y-8 text-sm leading-relaxed text-zinc-300">

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">1. Introduction</h2>
          <p>
            CreviaCockpit (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) operates creviacockpit.com. This Privacy Policy
            explains how we collect, use, and protect information about visitors and registered
            users of our platform.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">2. Information We Collect</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li><strong className="text-white">Account data:</strong> Email address and name when you register.</li>
            <li><strong className="text-white">Usage data:</strong> Pages visited, features used, and API calls made.</li>
            <li><strong className="text-white">Exchange API keys:</strong> Encrypted at rest using AES-256. Secret keys are never returned to the browser after submission.</li>
            <li><strong className="text-white">Trade journal data:</strong> Trade entries, notes, and performance data you voluntarily enter.</li>
            <li><strong className="text-white">Cookies:</strong> Session authentication cookies and, if you have consented, third-party advertising cookies (Google AdSense).</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">3. How We Use Your Information</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Providing and personalising the CreviaCockpit platform.</li>
            <li>Sending account notifications and, if subscribed, market intelligence digests.</li>
            <li>Improving content quality and platform performance.</li>
            <li>Complying with legal obligations.</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">4. Advertising</h2>
          <p>
            We use Google AdSense to display advertisements on some pages. Google may use cookies
            to serve ads based on prior visits to our site and other sites on the internet. You can
            opt out of personalised advertising at{' '}
            <a href="https://www.google.com/settings/ads" className="text-emerald-400 hover:text-emerald-300" target="_blank" rel="noopener noreferrer">
              google.com/settings/ads
            </a>.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">5. Data Sharing</h2>
          <p>
            We do not sell, trade, or rent your personal data to third parties. We may share
            anonymised, aggregated data for analytics purposes. Service providers (Cloudflare,
            database hosts) process data on our behalf under strict data processing agreements.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">6. Data Retention</h2>
          <p>
            Account data is retained while your account is active. You may request deletion at any
            time by contacting us. Exchange API keys can be deleted from the Account page at any
            time, which immediately removes them from our servers.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">7. Your Rights</h2>
          <p>
            Depending on your jurisdiction, you may have rights to access, correct, delete, or
            export your personal data. To exercise these rights, contact us at the email below.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">8. Security</h2>
          <p>
            We implement industry-standard security measures including HTTPS encryption, encrypted
            database storage, and JWT-based authentication. No method of transmission over the
            internet is 100% secure; we cannot guarantee absolute security.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-white mb-3">9. Contact</h2>
          <p>
            For privacy-related enquiries, email us at{' '}
            <a href="mailto:privacy@creviacockpit.com" className="text-emerald-400 hover:text-emerald-300">
              privacy@creviacockpit.com
            </a>.
          </p>
        </section>

      </div>
    </div>
  );
}

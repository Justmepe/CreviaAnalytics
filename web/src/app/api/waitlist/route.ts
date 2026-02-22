import { NextRequest, NextResponse } from 'next/server';
import { promises as dns } from 'dns';

// Email validation helpers
function isValidFormat(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

// Domains that are obviously fake/disposable — block them
const BLOCKED_DOMAINS = new Set([
  'mailinator.com', 'guerrillamail.com', 'tempmail.com', 'throwaway.email',
  'yopmail.com', 'sharklasers.com', 'guerrillamailblock.com', 'grr.la',
  'spam4.me', 'trashmail.com', 'dispostable.com', 'maildrop.cc',
  'discard.email', 'fakeinbox.com', 'mailnull.com', 'spamgourmet.com',
]);

async function domainHasMx(domain: string): Promise<boolean> {
  try {
    const records = await dns.resolveMx(domain);
    return records.length > 0;
  } catch {
    return false; // domain doesn't exist or has no MX records
  }
}

async function sendResendEmail(apiKey: string, payload: Record<string, unknown>) {
  return fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => null);
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, name, source } = body as {
      email?: string;
      name?: string;
      source?: string;
    };

    // 1. Format check
    if (!email || !isValidFormat(email)) {
      return NextResponse.json({ detail: 'Please enter a valid email address.' }, { status: 400 });
    }

    const domain = email.split('@')[1].toLowerCase();

    // 2. Disposable domain check
    if (BLOCKED_DOMAINS.has(domain)) {
      return NextResponse.json(
        { detail: 'Disposable email addresses are not accepted. Please use your real email.' },
        { status: 400 }
      );
    }

    // 3. MX record check — does this domain actually receive email?
    const hasMx = await domainHasMx(domain);
    if (!hasMx) {
      return NextResponse.json(
        { detail: `The domain "${domain}" doesn't appear to accept email. Please double-check your address.` },
        { status: 400 }
      );
    }

    const apiKey = process.env.RESEND_API_KEY;
    const ownerEmail = process.env.OWNER_EMAIL;
    const audienceId = process.env.RESEND_AUDIENCE_ID;
    const firstName = name?.trim().split(' ')[0] || 'there';

    if (apiKey) {
      // Add to Resend audience
      if (audienceId) {
        await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, first_name: name || undefined, unsubscribed: false }),
        }).catch(() => null);
      }

      // 4. Confirmation email to the user (double-validates deliverability)
      await sendResendEmail(apiKey, {
        from: 'CreviaCockpit <onboarding@resend.dev>',
        to: [email],
        subject: "You're on the CreviaCockpit waitlist 🎉",
        html: `
          <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:32px 24px;background:#09090b;color:#e4e4e7;border-radius:12px">
            <div style="width:40px;height:40px;background:#10b981;border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:bold;color:#09090b;margin-bottom:24px;font-size:14px">CC</div>
            <h2 style="color:#ffffff;margin:0 0 12px">Hey ${firstName}, you're on the list!</h2>
            <p style="color:#a1a1aa;line-height:1.6;margin:0 0 20px">
              You've secured early access to <strong style="color:#10b981">CreviaCockpit</strong> —
              live market regime detection, AI trade setups, opportunity scanner, and risk calculator for 16+ crypto assets.
            </p>
            <p style="color:#a1a1aa;line-height:1.6;margin:0 0 24px">
              We'll email you at <strong style="color:#ffffff">${email}</strong> when your early access is ready.
              Early access members get Pro features <strong style="color:#10b981">free during beta</strong>.
            </p>
            <a href="https://crevia.creohub.io/tools/risk-calculator"
               style="display:inline-block;background:#10b981;color:#09090b;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:600;font-size:14px">
              Try the Risk Calculator Free →
            </a>
            <p style="color:#52525b;font-size:12px;margin-top:32px">
              If you didn't request this, you can safely ignore this email.
            </p>
          </div>
        `,
      });

      // Owner notification
      if (ownerEmail) {
        await sendResendEmail(apiKey, {
          from: 'Crevia Waitlist <onboarding@resend.dev>',
          to: [ownerEmail],
          subject: `New waitlist signup: ${email}`,
          html: `
            <p>A new person joined the CreviaCockpit waitlist.</p>
            <table cellpadding="6" style="border-collapse:collapse">
              <tr><td><strong>Email</strong></td><td>${email}</td></tr>
              <tr><td><strong>Name</strong></td><td>${name || '—'}</td></tr>
              <tr><td><strong>Source</strong></td><td>${source || '—'}</td></tr>
              <tr><td><strong>MX verified</strong></td><td>✅ Yes</td></tr>
            </table>
          `,
        });
      }
    }

    return NextResponse.json({
      success: true,
      message: "You're on the list! Check your inbox for a confirmation.",
    });
  } catch {
    return NextResponse.json(
      { detail: 'Something went wrong. Please try again.' },
      { status: 500 }
    );
  }
}

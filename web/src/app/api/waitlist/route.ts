import { NextRequest, NextResponse } from 'next/server';

// No database needed for the waitlist MVP.
// Uses Resend (free) to:
//   1. Add contacts to a Resend audience (your email list)
//   2. Notify you by email on each signup
//
// Required env vars (set in Vercel dashboard):
//   RESEND_API_KEY       — from resend.com (free account)
//   OWNER_EMAIL          — your email, gets a ping on each signup
//   RESEND_AUDIENCE_ID   — optional: Resend audience ID to store contacts

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { email, name, source } = body as {
      email?: string;
      name?: string;
      source?: string;
    };

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return NextResponse.json({ detail: 'A valid email address is required.' }, { status: 400 });
    }

    const apiKey = process.env.RESEND_API_KEY;
    const ownerEmail = process.env.OWNER_EMAIL;
    const audienceId = process.env.RESEND_AUDIENCE_ID;

    if (apiKey) {
      // Add to Resend audience/contact list
      if (audienceId) {
        await fetch(`https://api.resend.com/audiences/${audienceId}/contacts`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email,
            first_name: name || undefined,
            unsubscribed: false,
          }),
        }).catch(() => null); // non-fatal if this fails
      }

      // Notify owner
      if (ownerEmail) {
        await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            from: 'Crevia Waitlist <onboarding@resend.dev>',
            to: [ownerEmail],
            subject: `New waitlist signup: ${email}`,
            html: `
              <p>A new person joined the Crevia Analytics waitlist.</p>
              <table cellpadding="6">
                <tr><td><strong>Email</strong></td><td>${email}</td></tr>
                <tr><td><strong>Name</strong></td><td>${name || '—'}</td></tr>
                <tr><td><strong>Source</strong></td><td>${source || '—'}</td></tr>
              </table>
            `,
          }),
        }).catch(() => null);
      }
    }

    return NextResponse.json({
      success: true,
      message: "You're on the list! We'll reach out when early access opens.",
    });
  } catch {
    return NextResponse.json(
      { detail: 'Something went wrong. Please try again.' },
      { status: 500 }
    );
  }
}

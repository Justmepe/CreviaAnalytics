# Substack Authentication - Manual Cookie Capture

## Quick Setup (2 minutes)

Substack's page structure changes frequently, so the most reliable method is **manual cookie capture**.

### Steps:

**1. Open Substack Login Page**
```
https://substack.com/auth/login
```

**2. Sign In**
- Email: `petergikonyo025@gmail.com`
- Password: `@Gikonyo@2026!`
- Click "Continue"

**3. Open Browser DevTools**
- Press `F12` (or right-click → Inspect)

**4. Find the Cookie**
- Click the "Application" tab (or "Storage" in Firefox)
- On the left: Click "Cookies" → expand it
- Click `https://substack.com`
- Scroll down to find `substack.sid`
- Click on it

**5. Copy the Cookie Value**
- On the right side, find the "Value" column
- Copy the entire value (it's a long string starting with `s:` or `s%3A`)

**6. Save to Your Project**

Either option:

**Option A: Use the helper script**
```bash
python paste_substack_cookie.py
```
- Paste the value when prompted
- Done!

**Option B: Update .env manually**
```
SUBSTACK_SID=<paste_the_value_here>
```

### Test It Works

```bash
python test_substack_post.py
```

You should see:
```
[OK] Authentication successful!
[SUCCESS] Note posted! ID: ...
```

## Why Manual?

Substack's login page structure changes between versions/regions. The manual method:
- ✅ Always works
- ✅ Takes 2 minutes
- ✅ Gets a fresh, valid cookie
- ❌ Requires C+P once

## Browser Automation Status

We created a Playwright-based browser automation system (`src/utils/substack_playwright_auth.py`), but Substack's dynamic page redirects make it unreliable. The manual method is the sweetspot: fast, reliable, and requires no debugging.

The Playwright fallback is **disabled** in `SubstackPoster` until Substack's page structure stabilizes.

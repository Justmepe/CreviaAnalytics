# SUBSTACK POSTING SETUP - COMPLETE WORKFLOW

## Overview
You need to provide a valid session cookie from Substack to enable posting. This 5-minute process breaks down into **Capture → Verify → Test**.

---

## STEP 1: Capture Cookie from Your Browser (2 minutes)

### 1.1 Open Substack Login
Go to: https://substack.com/auth/login

### 1.2 Sign In with Your Account
- **Email:** `petergikonyo025@gmail.com`
- **Password:** `@Gikonyo@2026!`
- Click the "Continue" button (or "Sign with password" if shown)

### 1.3 After Login, Capture the Cookie (do this QUICKLY!)
Substack cookies expire fast, so work quickly.

1. **Open Developer Tools:** Press `F12`
2. **Go to Application Tab:** Click "Application" tab (right side of DevTools)
3. **Find Cookies:** On left side → Cookies → https://substack.com
4. **Locate substack.sid:** Scroll down to find `substack.sid` (it's always there)
5. **Copy Its Value:** Right-side panel shows: `Name | Value`
   - Copy the VALUE (long string starting with `s:` or `s%3A`)
   - ⚠️  **Copy the ENTIRE value** (might be 100+ characters)

### 1.4 Keep Browser Tab Open
Don't close the browser or log out yet - the cookie is tied to this session.

---

## STEP 2: Verify Cookie Works (1 minute)

Once you have the cookie value:

```bash
python verify_substack_cookie.py
```

When prompted, paste the cookie value you copied.

**What happens:**
- ✓ **If it says VALID:** Great! Proceed to Step 3
- ✗ **If it says INVALID:** Cookie expired or wrong value
  - Go back to browser (still logged in from Step 1.3)
  - Re-copy the `substack.sid` value (sometimes it changes after page load)
  - Try again with: `python verify_substack_cookie.py`

---

## STEP 3: Save Cookie to Project (1 minute)

Once verified as valid, save it:

```bash
python paste_substack_cookie.py
```

When prompted:
1. Paste the cookie value (from Step 1.3)
2. Press Enter
3. The script will verify it again, then save to:
   - `.env` (as `SUBSTACK_SID=...`)
   - `data/substack_cookies.json`

---

## STEP 4: Test Full Integration (1 minute)

Test that posting works:

```bash
python test_substack_post.py
```

**Expected output:**
```
✓ STEP 1: Authentication successful!
✓ STEP 2: Test note posted successfully!
   Note ID: abc123...

View it here: https://petergikonyo.substack.com
```

**If it works:** All done! Your Substack posting is live.

**If it fails:** 
- Cookie likely expired
- Go back to Step 1 and get a fresh one (browser tab should still be open)
- Re-run Steps 2-4

---

## Troubleshooting

### "Cookie verification FAILED"
- **Cause:** Cookie expired or wrong value
- **Fix:** Go back to browser (logged in), re-copy `substack.sid`, try again
- **Why:** Substack session cookies are short-lived (30-60 minutes)

### "Authentication FAILED" in test script
- **Cause:** Cookie not saved or expired
- **Fix:** Run `python paste_substack_cookie.py` with a fresh cookie
- **Or:** Delete `data/substack_cookies.json` and try again

### "Test note posted but I don't see it"
- Check: https://petergikonyo.substack.com
- It might be queued or needs refresh
- May have hit daily posting limit (max 5 notes/day)

### "Password login blocked by CAPTCHA"
- This is normal - Substack blocks automated login
- This is why we use manual cookie capture instead
- The manual cookie method completely avoids this

---

## Helper Scripts Reference

| Script | Purpose | When to Use |
|--------|---------|------------|
| `verify_substack_cookie.py` | Test if a cookie value is valid | Before saving it |
| `paste_substack_cookie.py` | Save cookie to `.env` and JSON | After verifying it works |
| `test_substack_post.py` | End-to-end authentication + posting test | Final verification |
| `SUBSTACK_AUTH_GUIDE.md` | Detailed manual steps | Reference guide |

---

## Understanding the Auth Flow

```
1. Manual cookie capture
   ↓
2. Cookie stored in .env + data/substack_cookies.json
   ↓
3. SubstackPoster loads .env on startup
   ↓
4. _ensure_authenticated() applies cookie
   ↓
5. _test_session() verifies it works
   ↓
6. post_note() sends note to Substack API
```

Your main.py script automatically calls `post_thread_as_note()` and `post_memo_as_note()` during analysis runs, so once this setup is complete, Substack posting will work automatically.

---

## Why This Approach?

**Manual cookie capture vs other methods:**

| Method | Pros | Cons |
|--------|------|------|
| **Manual Cookie** | ✓ Most reliable | Takes 2 min |
| | ✓ Avoids CAPTCHA | Cookies expire |
| | ✓ Works immediately | | 
| **Password Login API** | ✗ Simple code | Blocked by CAPTCHA |
| | | Requires account change |
| **Browser Automation** | ✓ Automatic | Substack structure changes |
| | | Selector mismatches |
| | | Extra overhead |

We chose **manual capture** because:
1. Substack has strong anti-bot protections (CAPTCHA on API login)
2. Page structure changes frequently (breaks selectors)
3. Manual capture is fastest to implement and most reliable
4. Once saved, cookie persists across script runs

---

## Next Steps After Setup

Once `test_substack_post.py` shows success:

1. **main.py will automatically post**: During analysis runs, detected opportunities get posted to Substack automatically
2. **Rate limiting applies**: Max 5 notes/day (configurable in `.env` as `SUBSTACK_MAX_NOTES_PER_DAY`)
3. **Monitor the logs**: Check console output during runs for Substack posting status
4. **If cookie expires**: Re-run Steps 1-2 to get a fresh one

---

## Questions?

If something doesn't work:
1. Check the error message in the script output
2. Ensure you copied the **entire** cookie value (long string)
3. Make sure you're using the **substack.sid** cookie (not others)
4. Cookie must be fresh (copied within 2 minutes of login)

Good luck! 🚀

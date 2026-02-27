"""
Run this on your LOCAL Windows machine (not VPS) to export X.com cookies from Chrome.
Usage: python scripts/export_x_cookies.py
Outputs: x_cookies.json in the current directory
"""
import os, sys, json, shutil, sqlite3, base64, tempfile

def get_chrome_cookies():
    # Chrome cookie DB path on Windows
    cookie_path = os.path.expandvars(
        r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Network\Cookies'
    )
    if not os.path.exists(cookie_path):
        # Try old path
        cookie_path = os.path.expandvars(
            r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\Cookies'
        )
    if not os.path.exists(cookie_path):
        print("ERROR: Chrome cookie file not found. Is Chrome installed?")
        sys.exit(1)

    # Get the encryption key from Local State
    local_state_path = os.path.expandvars(
        r'%LOCALAPPDATA%\Google\Chrome\User Data\Local State'
    )
    with open(local_state_path, 'r', encoding='utf-8') as f:
        local_state = json.load(f)

    encrypted_key_b64 = local_state['os_crypt']['encrypted_key']
    encrypted_key = base64.b64decode(encrypted_key_b64)
    # Remove DPAPI prefix "DPAPI" (5 bytes)
    encrypted_key = encrypted_key[5:]

    # Decrypt key with Windows DPAPI
    try:
        import win32crypt
        key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except ImportError:
        print("Installing pywin32...")
        os.system(f'{sys.executable} -m pip install pywin32 -q')
        import win32crypt
        key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    # Copy DB + WAL using pywin32 with FILE_SHARE flags (bypasses Chrome's lock)
    import win32file, win32con

    def win_copy(src_path, dst_path):
        try:
            h = win32file.CreateFile(
                src_path,
                win32con.GENERIC_READ,
                win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                None, win32con.OPEN_EXISTING, 0, None
            )
        except Exception:
            return False  # file doesn't exist
        try:
            with open(dst_path, 'wb') as f:
                while True:
                    _, data = win32file.ReadFile(h, 65536)
                    if not data:
                        break
                    f.write(data)
        finally:
            win32file.CloseHandle(h)
        return True

    tmp = tempfile.mktemp(suffix='.db')
    win_copy(cookie_path, tmp)
    # Also copy WAL and SHM so SQLite can see all committed data
    win_copy(cookie_path + '-wal', tmp + '-wal')
    win_copy(cookie_path + '-shm', tmp + '-shm')

    conn = sqlite3.connect(tmp)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    # Debug: show all tables and the cookie file path
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"Cookie file: {cookie_path}")
    print(f"Tables in DB: {[t[0] for t in tables]}")
    cur.execute("""
        SELECT name, encrypted_value, host_key, path,
               expires_utc, is_secure, is_httponly, samesite
        FROM cookies
        WHERE host_key LIKE '%x.com%' OR host_key LIKE '%twitter.com%'
    """)
    rows = cur.fetchall()
    conn.close()
    for f in [tmp, tmp + '-wal', tmp + '-shm']:
        try:
            os.unlink(f)
        except Exception:
            pass

    cookies = []
    for row in rows:
        enc_val = row['encrypted_value']
        # v10/v11 = AES-256-GCM encrypted
        if enc_val[:3] in (b'v10', b'v11'):
            nonce = enc_val[3:15]
            ciphertext = enc_val[15:]
            try:
                value = AESGCM(key).decrypt(nonce, ciphertext, None).decode('utf-8')
            except Exception:
                value = ''
        else:
            # Old DPAPI encrypted
            try:
                value = win32crypt.CryptUnprotectData(enc_val, None, None, None, 0)[1].decode('utf-8')
            except Exception:
                value = ''

        # Convert Chrome epoch (microseconds since 1601-01-01) to Unix timestamp
        expires = 0
        if row['expires_utc']:
            # Chrome uses microseconds from 1601-01-01
            expires = (row['expires_utc'] / 1_000_000) - 11644473600

        samesite_map = {-1: 'None', 0: 'None', 1: 'Lax', 2: 'Strict'}
        samesite = samesite_map.get(row['samesite'], 'None')

        cookies.append({
            'name': row['name'],
            'value': value,
            'domain': row['host_key'],
            'path': row['path'],
            'expires': int(expires),
            'httpOnly': bool(row['is_httponly']),
            'secure': bool(row['is_secure']),
            'sameSite': samesite,
        })

    return cookies

if __name__ == '__main__':
    print("Extracting X.com cookies from Chrome...")
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        print("Installing cryptography...")
        os.system(f'{sys.executable} -m pip install cryptography -q')

    cookies = get_chrome_cookies()
    out_path = os.path.join(os.path.dirname(__file__), '..', 'x_cookies.json')
    with open(out_path, 'w') as f:
        json.dump(cookies, f, indent=2)

    print(f"Exported {len(cookies)} X/Twitter cookies to x_cookies.json")
    # Show key cookies
    key_names = ['auth_token', 'ct0', 'twid', 'guest_id']
    found = [c['name'] for c in cookies if c['name'] in key_names]
    print(f"Key cookies found: {found}")
    if 'auth_token' in found:
        print("\nSUCCESS: auth_token found - you are logged in to X in Chrome")
    else:
        print("\nWARNING: auth_token not found - are you logged into X in Chrome?")

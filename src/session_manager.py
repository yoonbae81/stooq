import os
import pickle
import requests

def get_default_data_dir():
    """Get the default data directory (project_root/data)"""
    # Assuming this file is in src/, project root is one level up
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, 'data')

def setup_directories(data_dir=None, cookie_dir="tmp/cookies"):
    """Create data and cookie directories"""
    if data_dir is None:
        data_dir = get_default_data_dir()

    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cookie_dir, exist_ok=True)
    print(f"Data storage location: {data_dir}")
    return data_dir, cookie_dir

def get_cookie_path(cookie_dir):
    """Get the path to the cookie file"""
    return os.path.join(cookie_dir, "stooq_session.pkl")

def create_session(user_agent=None):
    """Create a new requests session with the given user agent"""
    if user_agent is None:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    session = requests.Session()
    session.headers.update({'User-Agent': user_agent})
    return session

def save_session(context, session, cookie_path):
    """Save Playwright context cookies to requests session and file"""
    if hasattr(context, 'cookies'):
        cookies = context.cookies()
    else:
        cookies = []

    # Strict filter: only stooq.com domains. Ensure domain exists.
    stooq_cookies = [c for c in cookies if c.get('domain', '').endswith('stooq.com')]

    print(f"Syncing {len(stooq_cookies)} cookies for stooq.com...")
    for cookie in stooq_cookies:
        try:
            name = cookie['name']
            value = cookie['value']
            domain = cookie.get('domain', '.stooq.com')

            # Force critical cookies to satisfy subdomains if missing dot
            if name in ['PHPSESSID', 'uid', 'cookie_uu']:
                if not domain.startswith('.'):
                    domain = '.' + domain

            if domain == 'stooq.com':
                domain = '.stooq.com'

            session.cookies.set(name, value, domain=domain, path=cookie.get('path', '/'))
        except Exception:
            pass

    # Save the session cookies to disk
    with open(cookie_path, 'wb') as f:
        pickle.dump(session.cookies, f)
    print(f"Session cookies saved: {cookie_path}")

def force_save_session_to_disk(session, cookie_path):
    """Helper to save just the requests session cookies if modified manually"""
    with open(cookie_path, 'wb') as f:
        pickle.dump(session.cookies, f)
    print(f"Session cookies saved: {cookie_path}")

def load_session(session, cookie_path):
    """Load saved cookies and verify server connection"""
    if os.path.exists(cookie_path):
        try:
            with open(cookie_path, 'rb') as f:
                session.cookies.update(pickle.load(f))

            # Check session validity using HTTP status code
            # Valid session should return 200 OK
            res = session.get("https://stooq.com/db/", timeout=10)

            # Check for explicit error status codes
            if res.status_code == 200:
                # Check for explicit error messages in response
                error_indicators = [
                    'Unauthorized',
                    'Access Denied',
                    '401 Unauthorized',
                    '403 Forbidden',
                    'Please login',
                    'Authorization required'
                ]
                has_error = any(indicator in res.text for indicator in error_indicators)

                if not has_error:
                    print("Existing session is valid.")
                    return True
                else:
                    print("Session expired or invalid. Cookies may be invalid.")
            else:
                print(f"Session check failed with status code: {res.status_code}")
        except Exception as e:
            print(f"Error loading session: {e}")
    print("New session authentication required.")
    return False

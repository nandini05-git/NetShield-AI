import os
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=False)

SUPABASE_DEFAULT_URL = "postgresql://postgres.wqbdjmdksttvufaknsaa:6n9zwJX96j0K3x8v@aws-0-ap-southeast-2.pooler.supabase.com:5432/postgres"

def _safe_int(val, default=5432):
    try:
        s = str(val).strip()
        return int(s) if s.isdigit() else default
    except Exception:
        return default

def _is_serverless_env():
    if os.getenv('VERCEL') or os.getenv('VERCEL_ENV') or os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('LAMBDA_TASK_ROOT'):
        return True
    if '/var/task' in os.path.abspath(__file__):
        return True
    return False

def _parse_db_env():
    serverless = _is_serverless_env()
    explicit_host = (os.getenv('POSTGRES_HOST') or os.getenv('DB_HOST') or '').strip()
    
    db_url = (
        os.getenv('SUPABASE_DB_URL') or
        os.getenv('DATABASE_URL') or 
        os.getenv('EXTERNAL_DATABASE_URL') or 
        os.getenv('POSTGRES_URL') or 
        os.getenv('POSTGRESQL_URL') or 
        ''
    ).strip()
    
    # If explicit host was provided as a full connection string:
    if explicit_host and (explicit_host.startswith('postgresql://') or explicit_host.startswith('postgres://')):
        db_url = explicit_host
        explicit_host = ''

    # Filter out dead / expired Render instances (causes SSL closed unexpectedly)
    if db_url and ('render.com' in db_url or 'dpg-' in db_url):
        db_url = ''
    if explicit_host and ('render.com' in explicit_host or explicit_host.startswith('dpg-')):
        explicit_host = ''

    # If running on serverless (Vercel) without a working database URL, default to Supabase
    if serverless:
        if not db_url:
            if not explicit_host or explicit_host in ('127.0.0.1', 'localhost', 'postgresql'):
                db_url = SUPABASE_DEFAULT_URL
    else:
        if not db_url and not explicit_host:
            db_url = SUPABASE_DEFAULT_URL

    parsed_host = 'aws-0-ap-southeast-2.pooler.supabase.com'
    parsed_port = 5432
    parsed_user = 'postgres.wqbdjmdksttvufaknsaa'
    parsed_pass = '6n9zwJX96j0K3x8v'
    parsed_name = 'postgres'
    parsed_ssl = os.getenv('POSTGRES_SSLMODE')

    if db_url and (db_url.startswith('postgresql://') or db_url.startswith('postgres://')):
        try:
            from urllib.parse import unquote
            res = urlparse(db_url)
            parsed_host = res.hostname or 'aws-0-ap-southeast-2.pooler.supabase.com'
            parsed_port = res.port or 5432
            parsed_user = unquote(res.username or 'postgres.wqbdjmdksttvufaknsaa')
            parsed_pass = unquote(res.password or '6n9zwJX96j0K3x8v')
            parsed_name = res.path.lstrip('/') if res.path else 'postgres'
            if res.query and 'sslmode=' in res.query:
                import urllib.parse
                qs = urllib.parse.parse_qs(res.query)
                if 'sslmode' in qs:
                    parsed_ssl = qs['sslmode'][0]
        except Exception:
            pass
    elif explicit_host:
        parsed_host = explicit_host
        parsed_port = _safe_int(os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', 5432)), 5432)
        parsed_user = os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'postgres'))
        parsed_pass = os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', 'postgres'))
        parsed_name = os.getenv('POSTGRES_DB', os.getenv('DB_NAME', 'netshield_ai'))
    elif os.getenv('INTERNAL_DATABASE_URL'):
        int_url = os.getenv('INTERNAL_DATABASE_URL')
        if 'render.com' not in int_url and 'dpg-' not in int_url:
            try:
                res = urlparse(int_url)
                parsed_host = res.hostname or '127.0.0.1'
                parsed_port = res.port or 5432
                parsed_user = res.username or 'postgres'
                parsed_pass = res.password or ''
                parsed_name = res.path.lstrip('/') if res.path else 'netshield_ai'
            except Exception:
                pass

    # Extra guarantee: If parsed_host is Render, override to Supabase
    if 'render.com' in parsed_host or parsed_host.startswith('dpg-'):
        parsed_host = 'aws-0-ap-southeast-2.pooler.supabase.com'
        parsed_port = 5432
        parsed_user = 'postgres.wqbdjmdksttvufaknsaa'
        parsed_pass = '6n9zwJX96j0K3x8v'
        parsed_name = 'postgres'

    # Default SSL mode for external cloud PostgreSQL
    if not parsed_ssl:
        if parsed_host not in ('127.0.0.1', 'localhost'):
            parsed_ssl = 'require'
        else:
            parsed_ssl = 'prefer'

    return parsed_host, parsed_port, parsed_user, parsed_pass, parsed_name, parsed_ssl

_parsed_host, _parsed_port, _parsed_user, _parsed_pass, _parsed_name, _parsed_ssl = _parse_db_env()
is_serverless = _is_serverless_env()
tmp_writable = '/tmp/netshield' if is_serverless else BASE_DIR

class Config:
    # Relational Database (PostgreSQL is the active primary engine)
    DB_ENGINE = os.getenv('DB_ENGINE', 'postgresql')
    DB_HOST = _parsed_host
    DB_PORT = _parsed_port
    DB_USER = _parsed_user
    DB_PASSWORD = _parsed_pass
    DB_NAME = _parsed_name
    POSTGRES_SSLMODE = _parsed_ssl
    
    # Document Database (MongoDB for detailed telemetry events, raw PCAP/Zeek, and threat intel cache)
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'netshield_ai')
    MONGO_TIMEOUT_MS = _safe_int(os.getenv('MONGO_TIMEOUT_MS', 5000), 5000)
    
    # JWT Security Configuration
    JWT_SECRET = os.getenv('JWT_SECRET', 'netshield_super_secret_jwt_key_2026_safe')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS = _safe_int(os.getenv('JWT_EXPIRATION_HOURS', 24), 24)
    PORT = _safe_int(os.getenv('PORT', 5000), 5000)
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', os.getenv('FRONTEND_URL', 'http://localhost:3000,http://127.0.0.1:3000'))
    
    # Threat Intelligence API Configuration
    THREAT_INTEL_ENABLED = os.getenv('THREAT_INTEL_ENABLED', 'true').lower() in ('true', '1', 'yes')
    THREAT_INTEL_PROVIDER = os.getenv('THREAT_INTEL_PROVIDER', 'AbuseIPDB')  # AbuseIPDB, VirusTotal, AlienVault_OTX
    THREAT_INTEL_API_KEY = os.getenv('THREAT_INTEL_API_KEY', '')
    THREAT_INTEL_API_URL = os.getenv('THREAT_INTEL_API_URL', 'https://api.abuseipdb.com/api/v2/check')
    
    # Generic SIEM Webhook Integration
    SIEM_ENABLED = os.getenv('SIEM_ENABLED', 'false').lower() in ('true', '1', 'yes')
    SIEM_WEBHOOK_URL = os.getenv('SIEM_WEBHOOK_URL', '')
    SIEM_FORMAT = os.getenv('SIEM_FORMAT', 'JSON')  # JSON, CEF, Syslog
    
    # Directory paths (uses /tmp on serverless environments to prevent read-only filesystem crash)
    UPLOAD_FOLDER = os.path.join(tmp_writable, 'uploads')
    REPORTS_FOLDER = os.path.join(tmp_writable, 'reports')
    MODELS_FOLDER = os.path.join(BASE_DIR, 'models')
    LOGS_FOLDER = os.path.join(tmp_writable, 'logs')

# Safely attempt to create directories without crashing on read-only environments
for _fld in [Config.UPLOAD_FOLDER, Config.REPORTS_FOLDER, Config.LOGS_FOLDER]:
    try:
        os.makedirs(_fld, exist_ok=True)
    except Exception:
        pass


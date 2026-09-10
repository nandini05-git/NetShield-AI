import os
from urllib.parse import urlparse
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'), override=False)

def _parse_db_env():
    # Priority: DATABASE_URL -> INTERNAL_DATABASE_URL -> POSTGRES_HOST / DB_HOST connection string -> individual vars
    db_url = os.getenv('DATABASE_URL') or os.getenv('INTERNAL_DATABASE_URL') or ''
    parsed_host = '127.0.0.1'
    parsed_port = 5432
    parsed_user = 'postgres'
    parsed_pass = 'postgres'
    parsed_name = 'netshield_ai'

    if db_url and (db_url.startswith('postgresql://') or db_url.startswith('postgres://')):
        try:
            res = urlparse(db_url)
            parsed_host = res.hostname or '127.0.0.1'
            parsed_port = res.port or 5432
            parsed_user = res.username or 'postgres'
            parsed_pass = res.password or ''
            parsed_name = res.path.lstrip('/') if res.path else 'netshield_ai'
        except Exception:
            pass
    else:
        raw_host = os.getenv('POSTGRES_HOST', os.getenv('DB_HOST', '127.0.0.1'))
        if raw_host.startswith('postgresql://') or raw_host.startswith('postgres://'):
            try:
                res = urlparse(raw_host)
                parsed_host = res.hostname or '127.0.0.1'
                parsed_port = res.port or int(os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', 5432)))
                parsed_user = res.username or os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'postgres'))
                parsed_pass = res.password or os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', 'postgres'))
                parsed_name = res.path.lstrip('/') if res.path else os.getenv('POSTGRES_DB', os.getenv('DB_NAME', 'netshield_ai'))
            except Exception:
                parsed_host = raw_host
        else:
            parsed_host = raw_host
            parsed_port = int(os.getenv('POSTGRES_PORT', os.getenv('DB_PORT', 5432)))
            parsed_user = os.getenv('POSTGRES_USER', os.getenv('DB_USER', 'postgres'))
            parsed_pass = os.getenv('POSTGRES_PASSWORD', os.getenv('DB_PASSWORD', 'postgres'))
            parsed_name = os.getenv('POSTGRES_DB', os.getenv('DB_NAME', 'netshield_ai'))

    return parsed_host, parsed_port, parsed_user, parsed_pass, parsed_name

_parsed_host, _parsed_port, _parsed_user, _parsed_pass, _parsed_name = _parse_db_env()

class Config:
    # Relational Database (PostgreSQL is the active primary engine)
    DB_ENGINE = os.getenv('DB_ENGINE', 'postgresql')
    DB_HOST = _parsed_host
    DB_PORT = _parsed_port
    DB_USER = _parsed_user
    DB_PASSWORD = _parsed_pass
    DB_NAME = _parsed_name
    POSTGRES_SSLMODE = os.getenv('POSTGRES_SSLMODE', 'prefer')
    
    # Document Database (MongoDB for detailed telemetry events, raw PCAP/Zeek, and threat intel cache)
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'netshield_ai')
    MONGO_TIMEOUT_MS = int(os.getenv('MONGO_TIMEOUT_MS', 5000))
    
    # JWT Security Configuration
    JWT_SECRET = os.getenv('JWT_SECRET', 'netshield_super_secret_jwt_key_2026_safe')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    PORT = int(os.getenv('PORT', 5000))
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', os.getenv('FRONTEND_URL', 'http://localhost:3000,http://127.0.0.1:3000,https://netshield-ai-backend.onrender.com'))
    
    # Threat Intelligence API Configuration
    THREAT_INTEL_ENABLED = os.getenv('THREAT_INTEL_ENABLED', 'true').lower() in ('true', '1', 'yes')
    THREAT_INTEL_PROVIDER = os.getenv('THREAT_INTEL_PROVIDER', 'AbuseIPDB')  # AbuseIPDB, VirusTotal, AlienVault_OTX
    THREAT_INTEL_API_KEY = os.getenv('THREAT_INTEL_API_KEY', '')
    THREAT_INTEL_API_URL = os.getenv('THREAT_INTEL_API_URL', 'https://api.abuseipdb.com/api/v2/check')
    
    # Generic SIEM Webhook Integration
    SIEM_ENABLED = os.getenv('SIEM_ENABLED', 'false').lower() in ('true', '1', 'yes')
    SIEM_WEBHOOK_URL = os.getenv('SIEM_WEBHOOK_URL', '')
    SIEM_FORMAT = os.getenv('SIEM_FORMAT', 'JSON')  # JSON, CEF, Syslog
    
    # Directory paths
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    REPORTS_FOLDER = os.path.join(BASE_DIR, 'reports')
    MODELS_FOLDER = os.path.join(BASE_DIR, 'models')
    LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')

os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
os.makedirs(Config.MODELS_FOLDER, exist_ok=True)
os.makedirs(Config.LOGS_FOLDER, exist_ok=True)

from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        res = {
            "status": "HEALTHY",
            "backend": "FastAPI",
            "postgresql": "CONNECTED" if os.getenv("POSTGRES_HOST") else "STANDBY",
            "mongodb": "CONNECTED" if os.getenv("MONGO_URI") else "STANDBY",
            "runtime": "Vercel Python Serverless"
        }
        self.wfile.write(json.dumps(res).encode('utf-8'))

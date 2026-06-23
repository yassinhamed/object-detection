#!/usr/bin/env python3
"""
Video Server: Serves recorded videos from the sender PC
Receiver can browse, stream, and download recordings
Includes automatic discovery for clients on the same network
"""

import os
import sys
import argparse
import socket
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import mimetypes
import base64
import time
import uuid
from http import cookies
from urllib.parse import unquote, parse_qs

import datetime
from client_decryption import ClientDecryption

# Default video folder where yolo.py saves recordings
DEFAULT_VIDEO_FOLDER = os.path.join(os.path.dirname(__file__), "videos")
LOG_FILE = os.path.join(os.path.dirname(__file__), "server_access.log")
DISCOVERY_PORT = 9999
DISCOVERY_MESSAGE = b"VIDEO_SERVER_DISCOVER"
DISCOVERY_RESPONSE = b"VIDEO_SERVER_FOUND"


class VideoServerHandler(SimpleHTTPRequestHandler):
    """HTTP Handler for serving videos and metadata"""
    
    video_folder = DEFAULT_VIDEO_FOLDER
    auth_username = "admin"
    auth_password = "secure123"
    sessions = {}
    
    def log_action(self, action, status="SUCCESS"):
        """Log a specific user action with their IP to the log file"""
        ip = self.client_address[0]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        is_auth = False
        try:
            is_auth = self.check_auth()
        except:
            pass
            
        user_str = f"User:{self.auth_username}" if is_auth else "Unauthenticated"
        log_entry = f"[{timestamp}] IP:{ip} | {user_str} | ACTION:{action} | STATUS:{status}\n"
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"📝 LOG: {log_entry.strip()}")

    def log_message(self, format, *args):
        """Override default HTTP logging to also write to file"""
        ip = self.client_address[0]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = format % args
        log_entry = f"[{timestamp}] IP:{ip} | HTTP_REQ | {message}\n"
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        import sys
        sys.stderr.write(log_entry)
    
    def check_auth(self):
        """Check if the request is authorized via Cookie or Basic Auth"""
        # 1. Check Cookie Auth (for web browsers)
        cookie_header = self.headers.get('Cookie')
        if cookie_header:
            try:
                c = cookies.SimpleCookie(cookie_header)
                if 'session_id' in c:
                    session_id = c['session_id'].value
                    expiry = self.sessions.get(session_id)
                    if expiry and expiry > time.time():
                        # Valid session, extend it by 30 mins
                        self.sessions[session_id] = time.time() + 1800
                        return True
                    elif expiry:
                        # Session expired
                        del self.sessions[session_id]
            except Exception:
                pass

        # 2. Check Basic Auth (for Python API client)
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Basic '):
            try:
                encoded_creds = auth_header.split(' ')[1]
                decoded_creds = base64.b64decode(encoded_creds).decode('utf-8')
                username, password = decoded_creds.split(':', 1)
                return username == self.auth_username and password == self.auth_password
            except Exception:
                pass
                
        return False

    def send_login_page(self, error=""):
        """Send a custom HTML login page"""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Secure Video Server</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }}
        .login-box {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); width: 100%; max-width: 350px; text-align: center; }}
        h2 {{ margin-top: 0; color: #333; margin-bottom: 25px; }}
        input {{ width: 100%; padding: 12px; margin-bottom: 15px; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; font-size: 16px; }}
        button {{ width: 100%; padding: 12px; background: #667eea; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; transition: background 0.3s; font-weight: bold; }}
        button:hover {{ background: #5a6fd6; }}
        .error {{ color: #e53e3e; margin-bottom: 15px; font-size: 14px; background: #fff5f5; padding: 10px; border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="login-box">
        <h2>🔐 Secure Login</h2>
        {f'<div class="error">{error}</div>' if error else ''}
        <form method="POST" action="/login">
            <input type="text" name="username" placeholder="Username" required autocomplete="username">
            <input type="password" name="password" placeholder="Password" required autocomplete="current-password">
            <button type="submit">Log In</button>
        </form>
    </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))

    def do_POST(self):
        """Handle POST requests for login"""
        # Only redirect for form submissions, not API calls
        host_header = self.headers.get('Host', '')
        if host_header and '.' in host_header and not host_header.startswith('localhost') and self.path == '/login':
            # Extract port from Host header
            host_parts = host_header.split(':')
            port = host_parts[1] if len(host_parts) > 1 else '8000'
            
            # Redirect to localhost
            self.send_response(302)
            self.send_header('Location', f'http://localhost:{port}{self.path}')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            print(f"🔄 Redirecting {host_header} → localhost:{port}")
            return
        
        if self.path == '/login':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed = parse_qs(post_data)
            
            username = parsed.get('username', [''])[0]
            password = parsed.get('password', [''])[0]
            
            if username == self.auth_username and password == self.auth_password:
                # Login success, create session
                session_id = str(uuid.uuid4())
                self.sessions[session_id] = time.time() + 1800  # 30 mins
                
                self.log_action(f"Login (username: '{username}', password: '{password}')", "SUCCESS")
                
                self.send_response(302)
                self.send_header('Location', '/')
                self.send_header('Set-Cookie', f'session_id={session_id}; HttpOnly; Path=/; Max-Age=1800')
                self.end_headers()
            else:
                self.log_action(f"Login attempt (username: '{username}', password: '{password}')", "FAILED")
                self.send_login_page(error="Invalid username or password")
        elif self.path.startswith('/api/decrypt'):
            # Check authentication
            if not self.check_auth():
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Secure Video Server"')
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Unauthorized"}')
                return
            
            # Handle decryption request
            self.handle_decrypt_request()
        else:
            self.send_error(404, "Not found")

    def do_GET(self):
        """Handle GET requests"""
        # Check if accessing via IP address and redirect to localhost
        # (BUT NOT for API requests - those need auth headers preserved)
        host_header = self.headers.get('Host', '')
        if host_header and '.' in host_header and not host_header.startswith('localhost') and not self.path.startswith('/api/') and not self.path.startswith('/download/'):
            # Extract port from Host header
            host_parts = host_header.split(':')
            port = host_parts[1] if len(host_parts) > 1 else '8000'
            
            # Redirect to localhost
            localhost_url = f'http://localhost:{port}{self.path}'
            if self.path == '/':
                localhost_url = f'http://localhost:{port}/'
            
            self.send_response(302)
            self.send_header('Location', localhost_url)
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            print(f"🔄 Redirecting {host_header} → localhost:{port}")
            return
        
        if self.path == '/logout':
            self.log_action("Logout", "SUCCESS")
            self.send_response(302)
            self.send_header('Location', '/')
            self.send_header('Set-Cookie', 'session_id=; expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/')
            self.end_headers()
            return

        if not self.check_auth():
            if self.path.startswith('/api/'):
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="Secure Video Server"')
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Unauthorized"}')
            else:
                self.send_login_page()
            return

        if self.path == "/" or self.path == "/index.html":
            self.send_html_index()
        elif self.path == "/decrypt.js":
            self.send_decrypt_js()
        elif self.path == "/api/videos":
            self.send_videos_list()
        elif self.path.startswith("/download/"):
            self.serve_video_file()
        else:
            self.send_error(404, "Not found")
    
    def send_html_index(self):
        """Send HTML interface for browsing videos"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Recordings</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        html, body { height: 100%; }
        
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            color: white;
        }
        
        .header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.95;
            font-weight: 300;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .controls {
            display: flex;
            gap: 15px;
            margin-bottom: 30px;
            justify-content: center;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .sort-select {
            padding: 12px 20px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1em;
            background: white;
            color: #667eea;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            outline: none;
            transition: all 0.3s ease;
        }
        
        .sort-select:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        .logout-btn {
            padding: 12px 20px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1em;
            background: #e53e3e;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            text-decoration: none;
            transition: all 0.3s ease;
            margin-left: 10px;
        }
        
        .logout-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
            background: #c53030;
        }
        
        button {
            padding: 12px 28px;
            border: none;
            border-radius: 50px;
            cursor: pointer;
            font-weight: 600;
            font-size: 1em;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .refresh-btn {
            background: white;
            color: #667eea;
        }
        
        .refresh-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.3);
        }
        
        .videos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }
        
        .video-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
        }
        
        .video-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.25);
        }
        
        .video-thumbnail {
            width: 100%;
            height: 180px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3em;
            position: relative;
            overflow: hidden;
        }
        
        .video-thumbnail::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(45deg, rgba(255,255,255,0.1) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.1) 75%, transparent 75%, transparent);
            background-size: 20px 20px;
            animation: shimmer 2s infinite;
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .video-info {
            padding: 20px;
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .video-name {
            font-weight: 700;
            font-size: 1.15em;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
            word-break: break-word;
        }
        
        .video-meta {
            font-size: 0.85em;
            color: #999;
            margin-bottom: 15px;
            flex: 1;
        }
        
        .video-meta-item {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 6px;
        }
        
        .video-actions {
            display: flex;
            gap: 10px;
            margin-top: auto;
        }
        
        .btn-action {
            flex: 1;
            padding: 10px 15px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.9em;
            transition: all 0.2s;
            text-align: center;
        }
        
        .btn-play {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-play:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-download {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
        }
        
        .btn-download:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 15px rgba(72, 187, 120, 0.4);
        }
        
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: white;
        }
        
        .empty-state svg {
            width: 100px;
            height: 100px;
            opacity: 0.5;
            margin-bottom: 20px;
        }
        
        .empty-state h2 {
            font-size: 1.8em;
            margin-bottom: 10px;
        }
        
        .loading {
            text-align: center;
            padding: 60px 20px;
            color: white;
        }
        
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .message {
            margin-bottom: 20px;
            padding: 15px 20px;
            border-radius: 10px;
            font-weight: 600;
        }
        
        .error {
            background: rgba(245, 101, 101, 0.2);
            color: #ff6b6b;
            border-left: 4px solid #ff6b6b;
        }
        
        .success {
            background: rgba(72, 187, 120, 0.2);
            color: #48bb78;
            border-left: 4px solid #48bb78;
        }
        
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            animation: fadeIn 0.3s;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .modal-content {
            position: relative;
            width: 90%;
            max-width: 1000px;
            margin: 50px auto;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 25px 50px rgba(0,0,0,0.5);
            animation: slideUp 0.3s;
        }
        
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(50px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .modal-header {
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-title {
            font-size: 1.5em;
            font-weight: 700;
        }
        
        .close-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            font-size: 1.5em;
            cursor: pointer;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s;
        }
        
        .close-btn:hover {
            background: rgba(255,255,255,0.3);
            transform: rotate(90deg);
        }
        
        .modal-body {
            padding: 20px;
        }
        
        video {
            width: 100%;
            max-height: 600px;
            border-radius: 8px;
        }
        
        @media (max-width: 768px) {
            .header h1 { font-size: 1.8em; }
            .videos-grid {
                grid-template-columns: 1fr;
            }
            .modal-content {
                width: 95%;
                margin: 30px auto;
            }
        }
    </style>
    <script>
        // AES-256-CBC Decryption Class (embedded for immediate availability)
        class VideoDecryptor {
            constructor() {
                this.IV_SIZE = 16;
                this.KEY_SIZE = 32;
                this.SALT = new TextEncoder().encode("video_encryption_salt");
                this.ITERATIONS = 100000;
                this.DEFAULT_PASSWORD = "secure_video_key";
                
                // Check Web Crypto API availability
                if (!window.crypto) {
                    throw new Error('window.crypto is not defined - Web Crypto API not available');
                }
                if (!window.crypto.subtle) {
                    throw new Error('window.crypto.subtle is not defined - Web Crypto API not available. Ensure HTTPS or localhost connection.');
                }
                if (typeof window.crypto.subtle.importKey !== 'function') {
                    throw new Error('crypto.subtle.importKey not available - Web Crypto API not fully supported');
                }
                
                console.log('✅ VideoDecryptor initialized successfully');
            }

            async deriveKey(password = this.DEFAULT_PASSWORD) {
                try {
                    const passwordBuffer = new TextEncoder().encode(password);
                    const baseKey = await crypto.subtle.importKey(
                        'raw',
                        passwordBuffer,
                        { name: 'PBKDF2' },
                        false,
                        ['deriveKey']
                    );

                    return await crypto.subtle.deriveKey(
                        {
                            name: 'PBKDF2',
                            salt: this.SALT,
                            iterations: this.ITERATIONS,
                            hash: 'SHA-256'
                        },
                        baseKey,
                        { name: 'AES-CBC', length: 256 },
                        false,
                        ['decrypt']
                    );
                } catch (error) {
                    throw new Error(`Key derivation failed: ${error.message}`);
                }
            }

            removePadding(data) {
                const view = new Uint8Array(data);
                const paddingLength = view[view.length - 1];
                
                if (paddingLength > 16 || paddingLength === 0) {
                    console.warn('⚠️ Invalid padding length:', paddingLength);
                    return data;
                }
                
                let validPadding = true;
                for (let i = 0; i < paddingLength; i++) {
                    if (view[view.length - 1 - i] !== paddingLength) {
                        validPadding = false;
                        break;
                    }
                }
                
                if (validPadding) {
                    return data.slice(0, data.byteLength - paddingLength);
                }
                
                return data;
            }

            async decryptBytes(encryptedData, password = null) {
                try {
                    const data = new Uint8Array(encryptedData);
                    const pwd = password || this.DEFAULT_PASSWORD;
                    
                    if (data.length < this.IV_SIZE) {
                        throw new Error('Encrypted data too short - missing IV');
                    }
                    
                    const iv = data.slice(0, this.IV_SIZE);
                    const encryptedContent = data.slice(this.IV_SIZE);

                    console.log('🔓 Decrypting...');

                    const key = await this.deriveKey(pwd);

                    const decrypted = await crypto.subtle.decrypt(
                        {
                            name: 'AES-CBC',
                            iv: iv
                        },
                        key,
                        encryptedContent
                    );

                    const unpadded = this.removePadding(decrypted);
                    console.log('✅ Decryption successful');
                    
                    return unpadded;
                } catch (error) {
                    console.error('❌ Decryption error:', error);
                    throw new Error(`Decryption failed: ${error.message}`);
                }
            }

            isEncrypted(data) {
                return data.byteLength > this.IV_SIZE;
            }
        }

        // Create global instance
        let videoDecryptor;
        try {
            console.log('🔧 Initializing VideoDecryptor...');
            console.log('  - window.crypto:', typeof window.crypto);
            console.log('  - window.crypto.subtle:', typeof window.crypto?.subtle);
            console.log('  - Location:', window.location.hostname);
            videoDecryptor = new VideoDecryptor();
            console.log('✅ VideoDecryptor ready');
        } catch (error) {
            console.error('❌ VideoDecryptor initialization failed:', error.message);
            console.error('Full error:', error);
            videoDecryptor = null;
        }
    </script>
</head>
<body>
    <div class="header">
        <h1>🎬 Video Recordings</h1>
        <p>Browse and manage your recorded videos</p>
    </div>
    
    <div class="container">
        <div class="controls">
            <button class="refresh-btn" onclick="loadVideos()">🔄 Refresh Videos</button>
            <select id="sortSelect" class="sort-select" onchange="renderVideos()">
                <option value="newest">📅 Newest First</option>
                <option value="oldest">📅 Oldest First</option>
            </select>
            <a href="/logout" class="logout-btn">🚪 Log Out</a>
        </div>
        
        <div id="message"></div>
        <div id="videos" class="videos-grid">
            <div class="loading">
                <div class="spinner"></div>
                <div>Loading videos...</div>
            </div>
        </div>
    </div>

    <div id="playModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="playTitle">🎬 Video Player</div>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <video id="videoPlayer" controls></video>
            </div>
        </div>
    </div>

    <script>
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        }

        function formatDate(timestamp) {
            const date = new Date(timestamp * 1000);
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);
            
            if (date.toDateString() === today.toDateString()) {
                return 'Today ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            } else if (date.toDateString() === yesterday.toDateString()) {
                return 'Yesterday ' + date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            } else {
                return date.toLocaleDateString([], {year: 'numeric', month: 'short', day: 'numeric'}) + ' ' + 
                       date.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
            }
        }

        let allVideos = [];

        function renderVideos() {
            const videosDiv = document.getElementById('videos');
            const sortSelect = document.getElementById('sortSelect');
            
            if (allVideos.length === 0) {
                videosDiv.innerHTML = `
                    <div class="empty-state" style="grid-column: 1/-1; padding: 80px 20px;">
                        <div style="font-size: 4em; margin-bottom: 20px;">📹</div>
                        <h2>No Videos Found</h2>
                        <p>Start recording to see videos here</p>
                    </div>
                `;
                return;
            }

            let sortedVideos = [...allVideos];
            if (sortSelect && sortSelect.value === 'oldest') {
                sortedVideos.sort((a, b) => a.modified - b.modified);
            } else {
                sortedVideos.sort((a, b) => b.modified - a.modified);
            }

            videosDiv.innerHTML = sortedVideos.map(v => `
                <div class="video-card">
                    <div class="video-thumbnail">🎥</div>
                    <div class="video-info">
                        <div class="video-name" title="${v.name}">${v.name}</div>
                        <div class="video-meta">
                            <div class="video-meta-item">📅 ${formatDate(v.modified)}</div>
                            <div class="video-meta-item">💾 ${formatFileSize(v.size)}</div>
                        </div>
                        <div class="video-actions">
                            <button class="btn-action btn-play" onclick="playVideo('${v.name}', '${v.path}')">▶️ Play</button>
                            <button class="btn-action btn-download" onclick="downloadVideo('${v.name}', '${v.path}')">⬇️ Download</button>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        function loadVideos() {
            const videosDiv = document.getElementById('videos');
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '';
            videosDiv.innerHTML = '<div class="loading"><div class="spinner"></div><div>Loading videos...</div></div>';

            fetch('/api/videos')
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        messageDiv.innerHTML = '<div class="message error">❌ ' + data.error + '</div>';
                        videosDiv.innerHTML = '';
                        return;
                    }
                    allVideos = data.videos || [];
                    renderVideos();
                })
                .catch(err => {
                    messageDiv.innerHTML = '<div class="message error">❌ Failed to load videos: ' + err.message + '</div>';
                    videosDiv.innerHTML = '';
                });
        }

        function playVideo(name, path) {
            const modal = document.getElementById('playModal');
            const player = document.getElementById('videoPlayer');
            const title = document.getElementById('playTitle');
            title.textContent = '🎬 ' + name;
            
            // Check if file is encrypted
            if (path.endsWith('.enc')) {
                // Prompt for password
                const password = prompt('🔐 Enter password to decrypt video:', '');
                if (password === null || password === '') {
                    alert('❌ Password is required to decrypt the video');
                    return; // User cancelled or entered empty password
                }
                
                // Download and decrypt via server
                downloadAndDecryptInBrowser(path, password, (blob) => {
                    player.src = URL.createObjectURL(blob);
                    modal.style.display = 'block';
                    document.body.style.overflow = 'hidden';
                });
            } else {
                // Unencrypted file - play directly
                player.src = '/download/' + path;
                modal.style.display = 'block';
                document.body.style.overflow = 'hidden';
            }
        }

        function closeModal() {
            const modal = document.getElementById('playModal');
            const player = document.getElementById('videoPlayer');
            player.pause();
            player.src = '';
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }

        async function downloadAndDecryptInBrowser(path, password, callback) {
            try {
                console.log('📥 Downloading encrypted file:', path);
                
                // Fetch encrypted file
                const response = await fetch('/download/' + path);
                if (!response.ok) throw new Error('Failed to download file');
                
                const encryptedBlob = await response.blob();
                const encryptedArrayBuffer = await encryptedBlob.arrayBuffer();
                
                console.log('🔓 Decrypting on server...');
                
                // Send to server for decryption (requires client_decryption.py)
                const decryptResponse = await fetch('/api/decrypt?password=' + encodeURIComponent(password), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/octet-stream'
                    },
                    body: encryptedArrayBuffer,
                    credentials: 'include'  // Include cookies for authentication
                });
                
                if (!decryptResponse.ok) {
                    let errorMsg = 'Decryption failed';
                    try {
                        const errorData = await decryptResponse.json();
                        errorMsg = errorData.error || errorMsg;
                    } catch (e) {
                        errorMsg = `Server error (${decryptResponse.status})`;
                    }
                    throw new Error(errorMsg);
                }
                
                // Get decrypted data
                const decryptedArrayBuffer = await decryptResponse.arrayBuffer();
                
                // Create blob from decrypted data
                const blob = new Blob([decryptedArrayBuffer], { type: 'video/mp4' });
                console.log('✅ Decryption successful (server-side)');
                
                callback(blob);
            } catch (error) {
                console.error('Decryption error:', error);
                alert('❌ Error: ' + error.message);
            }
        }

        function downloadVideo(name, path) {
            // Check if file is encrypted
            if (path.endsWith('.enc')) {
                // Prompt for password
                const password = prompt('🔐 Enter password to decrypt and download:', '');
                if (password === null || password === '') {
                    alert('❌ Password is required to decrypt and download the video');
                    return; // User cancelled or entered empty password
                }
                
                // Download and decrypt via server
                downloadAndDecryptInBrowser(path, password, (blob) => {
                    // Download the decrypted blob
                    const link = document.createElement('a');
                    link.href = URL.createObjectURL(blob);
                    link.download = name.replace('.enc', '');  // Remove .enc from filename
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(link.href);
                });
            } else {
                // Unencrypted file - download directly
                const link = document.createElement('a');
                link.href = '/download/' + path;
                link.download = name;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }
        }

        window.onclick = function(event) {
            const modal = document.getElementById('playModal');
            if (event.target === modal) {
                closeModal();
            }
        }

        loadVideos();
        
        // Auto-refresh every 10 seconds
        setInterval(loadVideos, 10000);
    </script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def send_videos_list(self):
        """Send JSON list of available videos"""
        try:
            if not os.path.exists(self.video_folder):
                self.send_json_response({"error": "Video folder not found"})
                return
            
            videos = []
            for file in os.listdir(self.video_folder):
                # Include both encrypted (.enc) and unencrypted video files
                if file.endswith(('.mp4', '.avi', '.mkv', '.mov', '.flv', '.enc')):
                    file_path = os.path.join(self.video_folder, file)
                    if os.path.isfile(file_path):
                        stat = os.stat(file_path)
                        # Keep the actual filename, including .enc extension for clarity
                        display_name = file
                        videos.append({
                            'name': display_name,
                            'path': file,
                            'size': stat.st_size,
                            'modified': stat.st_mtime,
                            'encrypted': file.endswith('.enc')
                        })
            
            # Sort videos by modified date (newest first)
            videos.sort(key=lambda x: x['modified'], reverse=True)
            
            self.send_json_response({"videos": videos})
        except Exception as e:
            self.send_json_response({"error": str(e)})
    
    def send_decrypt_js(self):
        """Serve the client-side decryption JavaScript file"""
        decrypt_js_path = os.path.join(os.path.dirname(__file__), 'decrypt.js')
        
        if not os.path.exists(decrypt_js_path):
            self.send_error(404, "decrypt.js not found")
            return
        
        try:
            with open(decrypt_js_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            self.send_response(200)
            self.send_header("Content-type", "application/javascript")
            self.send_header("Content-Length", str(len(js_content)))
            self.end_headers()
            self.wfile.write(js_content.encode('utf-8'))
        except Exception as e:
            print(f"❌ Error serving decrypt.js: {e}")
            self.send_error(500, f"Error reading decrypt.js: {str(e)}")
    
    
    def serve_video_file(self):
        """Serve a video file as-is (NO decryption - client decrypts in browser)"""
        try:
            # Extract filename from path and strip query params
            path_no_query = self.path.split('?')[0]
            file_name = unquote(path_no_query.replace("/download/", "", 1))
            file_path = os.path.join(self.video_folder, file_name)
            
            # Security: prevent directory traversal
            if not os.path.abspath(file_path).startswith(os.path.abspath(self.video_folder)):
                self.send_error(403, "Forbidden")
                return
            
            # Check if file exists
            if not os.path.exists(file_path):
                self.send_error(404, "File not found")
                return
            
            file_size = os.path.getsize(file_path)
            
            # For encrypted files, serve as binary (client will decrypt)
            if file_path.endswith('.enc'):
                content_type = "application/octet-stream"
                self.log_action(f"Downloaded Encrypted Video: {file_name}")
                print(f"📦 Serving encrypted (NO decryption): {file_name} ({file_size} bytes)")
            else:
                # For unencrypted files, serve normally
                content_type, _ = mimetypes.guess_type(file_path)
                if not content_type:
                    content_type = "video/mp4"
                self.log_action(f"Downloaded Video: {file_name}")
            
            # Send file without decryption
            self.send_response(200)
            self.send_header("Content-type", content_type)
            self.send_header("Content-Length", str(file_size))
            self.send_header("Content-Disposition", f"inline; filename={os.path.basename(file_path)}")
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
                
        except Exception as e:
            print(f"❌ Error serving file: {e}")
            self.send_error(500, str(e))
    
    def send_full_file(self, file_path, file_size, content_type):
        """Send complete file"""
        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Content-Disposition", f"inline; filename={os.path.basename(file_path)}")
        self.end_headers()
        
        with open(file_path, 'rb') as f:
            self.wfile.write(f.read())
    
    def send_partial_content(self, file_path, file_size, content_type):
        """Send partial content for range requests"""
        range_header = self.headers["Range"]
        range_match = range_header.split('=')[1]
        start, end = range_match.split('-')
        start = int(start) if start else 0
        end = int(end) if end else file_size - 1
        
        if start < 0 or end >= file_size or start > end:
            self.send_error(416, "Range Not Satisfiable")
            return
        
        length = end - start + 1
        self.send_response(206)
        self.send_header("Content-type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
        self.end_headers()
        
        with open(file_path, 'rb') as f:
            f.seek(start)
            self.wfile.write(f.read(length))
    
    def handle_decrypt_request(self):
        """Handle POST request to decrypt encrypted file using client_decryption.py"""
        try:
            print(f"📡 Decrypt request received from {self.client_address[0]}")
            
            # Read request body (binary encrypted data)
            content_length = int(self.headers.get('Content-Length', 0))
            print(f"📏 Content-Length: {content_length}")
            
            if content_length <= 0:
                print("❌ No data provided")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "No data provided"}')
                return
            
            # Read encrypted data
            encrypted_data = self.rfile.read(content_length)
            print(f"✅ Received {len(encrypted_data)} bytes of encrypted data")
            
            # Get password from query parameters
            password = None
            path_parts = self.path.split('?')
            if len(path_parts) > 1:
                query_string = path_parts[1]
                params = parse_qs(query_string)
                password = params.get('password', [''])[0]
                print(f"🔑 Password received: {'*' * len(password) if password else 'NONE'}")
            
            if not password:
                print("❌ Password is required")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Password is required"}')
                return
            
            # Decrypt using ClientDecryption
            try:
                print("🔓 Starting decryption...")
                decryptor = ClientDecryption(password)
                decrypted_data = decryptor.decrypt_bytes_stream(encrypted_data)
                print(f"✅ Decryption successful: {len(decrypted_data)} bytes")
                
                # Send decrypted data
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(decrypted_data)))
                self.end_headers()
                self.wfile.write(decrypted_data)
                
                self.log_action("Decrypted video via API", "SUCCESS")
                print(f"🔓 Video decrypted server-side: {len(decrypted_data)} bytes")
                
            except Exception as decrypt_error:
                print(f"❌ Decryption error: {decrypt_error}")
                import traceback
                traceback.print_exc()
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Decryption failed - invalid password or corrupted file"}')
                self.log_action("Decryption failed", "FAILED")
                
        except Exception as e:
            print(f"❌ Error in decrypt handler: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')
    
    def send_json_response(self, data):
        """Send JSON response"""
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass


def start_discovery_listener(port):
    """Listen for discovery requests on UDP and respond with server port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                if data == DISCOVERY_MESSAGE:
                    # Send back the port number
                    response = DISCOVERY_RESPONSE
                    sock.sendto(response, addr)
            except Exception:
                break
    except Exception as e:
        print(f"Discovery listener error: {e}")
    finally:
        try:
            sock.close()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description="Video recording server - Serve videos for remote download")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--folder", type=str, default=DEFAULT_VIDEO_FOLDER, help="Video folder to serve")
    parser.add_argument("--username", type=str, default="admin", help="Web interface username")
    parser.add_argument("--password", type=str, default="secure123", help="Web interface password")
    args = parser.parse_args()
    
    VideoServerHandler.video_folder = args.folder
    VideoServerHandler.auth_username = args.username
    VideoServerHandler.auth_password = args.password
    
    # Create folder if it doesn't exist
    os.makedirs(args.folder, exist_ok=True)
    
    # Start discovery listener in background thread
    discovery_thread = threading.Thread(target=start_discovery_listener, args=(DISCOVERY_PORT,), daemon=True)
    discovery_thread.start()
    
    server = ThreadingHTTPServer((args.host, args.port), VideoServerHandler)
    
    print(f"🎬 Video Server started on http://{args.host if args.host != '0.0.0.0' else 'localhost'}:{args.port}")
    print(f"📁 Serving videos from: {args.folder}")
    print(f"🔍 Discovery enabled on port {DISCOVERY_PORT}")
    print("📺 Clients can auto-discover this server!")
    print("Press Ctrl+C to stop the server")
    print("")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Video Client: Download and manage recordings from the remote server
Automatically discovers server on the local network
"""

import os
import sys
import argparse
import requests
import socket
from pathlib import Path
from urllib.parse import urljoin
import time
from client_decryption import ClientDecryption

DISCOVERY_PORT = 9999
DISCOVERY_MESSAGE = b"VIDEO_SERVER_DISCOVER"
DISCOVERY_RESPONSE = b"VIDEO_SERVER_FOUND"
DISCOVERY_TIMEOUT = 3


class VideoClient:
    def __init__(self, server_url, username="admin", password="secure123"):
        """Initialize client with server URL"""
        if not server_url.startswith('http://') and not server_url.startswith('https://'):
            server_url = f'http://{server_url}'
        # Remove trailing slash
        self.server_url = server_url.rstrip('/')
        self.api_url = urljoin(self.server_url + '/', 'api/videos')
        self.auth = (username, password)
    
    def list_videos(self):
        """List all available videos from server"""
        try:
            response = requests.get(self.api_url, auth=self.auth, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                print(f"❌ Error: {data['error']}")
                return []
            
            return data.get('videos', [])
        except requests.exceptions.ConnectionError:
            print(f"❌ Cannot connect to server at {self.server_url}")
            return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def download_video(self, video_name, output_path=None):
        """Download a video from server (handles encrypted files)"""
        try:
            if output_path is None:
                output_path = video_name
            
            download_url = urljoin(self.server_url + '/', f'download/{video_name}')
            
            print(f"⬇️  Downloading: {video_name}")
            response = requests.get(download_url, auth=self.auth, stream=True, timeout=5)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # Download to temporary file first
            temp_output = output_path + ".tmp"
            
            with open(temp_output, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = (downloaded / total_size) * 100
                            print(f"   Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='\r')
            
            if output_path.endswith('.enc'):
                print(f"\n🔓 Decrypting file...")
                decryptor = ClientDecryption()
                decrypted_path = output_path.replace('.enc', '')
                decryptor.decrypt_file(temp_output, decrypted_path)
                os.remove(temp_output)
                output_path = decrypted_path
            else:
                os.rename(temp_output, output_path)
            
            print(f"\n✅ Downloaded: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Download failed: {e}")
            # Clean up temp file if it exists
            if 'temp_output' in locals() and os.path.exists(temp_output):
                os.remove(temp_output)
            return False
    
    def format_size(self, bytes_size):
        """Format bytes to human readable size"""
        if bytes_size == 0:
            return "0 B"
        sizes = ['B', 'KB', 'MB', 'GB']
        i = 0
        while bytes_size >= 1024 and i < len(sizes) - 1:
            bytes_size /= 1024
            i += 1
        return f"{bytes_size:.2f} {sizes[i]}"
    
    def format_date(self, timestamp):
        """Format timestamp to readable date"""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def interactive_menu(client):
    """Interactive menu for browsing videos (downloads disabled)"""
    while True:
        print("\n" + "="*60)
        print("📹 Video Recording Browser")
        print("="*60)
        
        videos = client.list_videos()
        
        if not videos:
            print("❌ No videos available or cannot connect to server")
            break
        
        print(f"\n✅ Available Videos: {len(videos)}\n")
        
        print("Options:")

        print("  'q' to quit")
        print("\n💡 Downloads available on web interface")
        
        try:
            choice = input("\n👉 Choose: ").strip().lower()
            
            if choice == 'q':
                print("👋 Goodbye!")
                break
            elif choice in ['l', 'r']:
                continue
            else:
                print("❌ Downloads disabled on terminal. Use web interface instead.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break


def discover_server():
    """
    Automatically discover video server on local network using UDP broadcast
    Returns: server address (ip:port) or None if not found
    """
    try:
        print("🔍 Searching for video server on local network...")
        
        # Create UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(DISCOVERY_TIMEOUT)
        
        # Bind to a local port
        sock.bind(('', 0))
        local_port = sock.getsockname()[1]
        
        # Send discovery broadcast
        broadcast_address = ('<broadcast>', DISCOVERY_PORT)
        sock.sendto(DISCOVERY_MESSAGE, broadcast_address)
        
        # Listen for responses
        found_servers = []
        start_time = time.time()
        
        while time.time() - start_time < DISCOVERY_TIMEOUT:
            try:
                data, addr = sock.recvfrom(1024)
                if data == DISCOVERY_RESPONSE:
                    server_ip = addr[0]
                    # Default port is 8000
                    server_address = f"{server_ip}:8000"
                    if server_address not in found_servers:
                        found_servers.append(server_address)
                        print(f"  ✅ Found server at: {server_address}")
            except socket.timeout:
                break
            except Exception:
                break
        
        sock.close()
        
        if found_servers:
            return found_servers[0]
        else:
            print("❌ No video server found on local network")
            print("   Make sure the server is running with: start_server.bat")
            return None
            
    except Exception as e:
        print(f"❌ Discovery error: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Download videos from remote recording server (auto-discovers)")
    parser.add_argument("server", nargs='?', default=None, help="Server address (e.g., 192.168.1.100:8000). If not provided, auto-discovers.")
    parser.add_argument("--list", action="store_true", help="List available videos and exit")
    parser.add_argument("--download", type=str, help="Download specific video by name")
    parser.add_argument("--output", type=str, help="Output path for downloaded video")
    parser.add_argument("--interactive", action="store_true", help="Interactive menu (default if no other args)")
    parser.add_argument("--username", type=str, default="admin", help="Server username")
    parser.add_argument("--password", type=str, default="secure123", help="Server password")
    args = parser.parse_args()
    
    # Auto-discover server if not provided
    if args.server is None:
        print("\n📺 Video Recording Client - Auto-Discovery Mode\n")
        server_address = discover_server()
        if server_address is None:
            sys.exit(1)
        args.server = server_address
        print(f"✅ Connecting to: {args.server}")
        print(f"🌐 You can access the server website at: http://{args.server}\n")
    
    client = VideoClient(args.server, args.username, args.password)
    
    if args.list:
        videos = client.list_videos()
        if videos:
            print(f"\n✅ {len(videos)} videos available")
        else:
            print("No videos available")
    elif args.download:
        print("❌ Downloads are disabled on the terminal. Please use the web interface at: http://{args.server}")
    else:
        # Default to interactive menu
        interactive_menu(client)


if __name__ == "__main__":
    main()

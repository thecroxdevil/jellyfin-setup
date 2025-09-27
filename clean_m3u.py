#!/usr/bin/env python3
"""
M3U Playlist Cleaner
Removes dead/broken links from M3U playlists by testing each stream URL.
"""

import urllib.request
import urllib.error
import ssl
import socket
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

class M3UCleaner:
    def __init__(self, timeout=10, max_workers=20, verbose=False):
        self.timeout = timeout
        self.max_workers = max_workers
        self.verbose = verbose
        
        # Create SSL context that doesn't verify certificates (for broken SSL)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    def parse_m3u(self, file_path):
        """Parse M3U file and extract channel info and URLs"""
        channels = []
        current_info = None
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error reading file: {e}")
            return []
            
        for line in lines:
            line = line.strip()
            
            if line.startswith('#EXTINF:'):
                current_info = line
            elif line and not line.startswith('#') and current_info:
                # This is a URL line
                channels.append({
                    'info': current_info,
                    'url': line
                })
                current_info = None
                
        return channels
    
    def test_stream_url(self, url):
        """Test if a stream URL is accessible"""
        try:
            # Create request with headers to mimic a real browser
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'identity',
                'Connection': 'keep-alive'
            })
            
            # Open URL with timeout and SSL context
            with urllib.request.urlopen(req, timeout=self.timeout, context=self.ssl_context) as response:
                # Check if we get a valid response
                if response.getcode() == 200:
                    # For m3u8 files, check if it contains valid playlist data
                    if url.endswith('.m3u8') or 'playlist.m3u8' in url:
                        content = response.read(1024).decode('utf-8', errors='ignore')
                        if '#EXTM3U' in content or '#EXT-X-' in content or 'http' in content:
                            return True
                    else:
                        # For other streams, just check if we can connect
                        return True
                        
        except urllib.error.HTTPError as e:
            if self.verbose:
                print(f"HTTP Error {e.code} for {url}")
        except urllib.error.URLError as e:
            if self.verbose:
                print(f"URL Error for {url}: {e.reason}")
        except socket.timeout:
            if self.verbose:
                print(f"Timeout for {url}")
        except Exception as e:
            if self.verbose:
                print(f"Error for {url}: {e}")
                
        return False
    
    def test_channels_batch(self, channels):
        """Test multiple channels concurrently"""
        working_channels = []
        dead_channels = []
        
        print(f"Testing {len(channels)} channels with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_channel = {
                executor.submit(self.test_stream_url, channel['url']): channel 
                for channel in channels
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_channel), 1):
                channel = future_to_channel[future]
                
                try:
                    is_working = future.result()
                    if is_working:
                        working_channels.append(channel)
                        status = "✓ WORKING"
                    else:
                        dead_channels.append(channel)
                        status = "✗ DEAD"
                        
                    # Extract channel name from EXTINF line
                    name_match = re.search(r',([^,]+)$', channel['info'])
                    channel_name = name_match.group(1).strip() if name_match else "Unknown"
                    
                    print(f"[{i}/{len(channels)}] {status}: {channel_name}")
                    
                except Exception as e:
                    dead_channels.append(channel)
                    print(f"[{i}/{len(channels)}] ✗ ERROR: {channel['url']} - {e}")
                    
        return working_channels, dead_channels
    
    def save_cleaned_playlist(self, working_channels, output_file):
        """Save working channels to new M3U file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for channel in working_channels:
                    f.write(f"{channel['info']}\n")
                    f.write(f"{channel['url']}\n")
                    
            print(f"\nCleaned playlist saved to: {output_file}")
            return True
        except Exception as e:
            print(f"Error saving cleaned playlist: {e}")
            return False
    
    def save_dead_links_report(self, dead_channels, report_file):
        """Save dead links to a report file"""
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("# Dead Links Report\n")
                f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total dead links: {len(dead_channels)}\n\n")
                
                for channel in dead_channels:
                    name_match = re.search(r',([^,]+)$', channel['info'])
                    channel_name = name_match.group(1).strip() if name_match else "Unknown"
                    f.write(f"# {channel_name}\n")
                    f.write(f"{channel['info']}\n")
                    f.write(f"{channel['url']}\n\n")
                    
            print(f"Dead links report saved to: {report_file}")
            return True
        except Exception as e:
            print(f"Error saving dead links report: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Clean M3U playlist by removing dead links')
    parser.add_argument('input_file', help='Input M3U playlist file')
    parser.add_argument('-o', '--output', help='Output cleaned playlist file (default: cleaned_playlist.m3u)')
    parser.add_argument('-r', '--report', help='Dead links report file (default: dead_links_report.txt)')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Timeout for testing URLs (default: 10s)')
    parser.add_argument('-w', '--workers', type=int, default=20, help='Number of concurrent workers (default: 20)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Set default output files
    if not args.output:
        args.output = 'cleaned_' + args.input_file
    if not args.report:
        args.report = 'dead_links_report.txt'
    
    print("M3U Playlist Cleaner")
    print("===================")
    print(f"Input file: {args.input_file}")
    print(f"Output file: {args.output}")
    print(f"Report file: {args.report}")
    print(f"Timeout: {args.timeout}s")
    print(f"Workers: {args.workers}")
    print()
    
    # Initialize cleaner
    cleaner = M3UCleaner(
        timeout=args.timeout,
        max_workers=args.workers,
        verbose=args.verbose
    )
    
    # Parse M3U file
    print("Parsing M3U file...")
    channels = cleaner.parse_m3u(args.input_file)
    
    if not channels:
        print("No channels found or error parsing file!")
        return 1
        
    print(f"Found {len(channels)} channels to test")
    print()
    
    # Test all channels
    start_time = time.time()
    working_channels, dead_channels = cleaner.test_channels_batch(channels)
    end_time = time.time()
    
    # Print summary
    print("\n" + "="*50)
    print("CLEANING SUMMARY")
    print("="*50)
    print(f"Total channels tested: {len(channels)}")
    print(f"Working channels: {len(working_channels)} ({len(working_channels)/len(channels)*100:.1f}%)")
    print(f"Dead channels: {len(dead_channels)} ({len(dead_channels)/len(channels)*100:.1f}%)")
    print(f"Time taken: {end_time - start_time:.1f} seconds")
    print()
    
    # Save results
    if working_channels:
        if cleaner.save_cleaned_playlist(working_channels, args.output):
            print(f"✓ Cleaned playlist ready: {args.output}")
    else:
        print("⚠ No working channels found!")
        
    if dead_channels:
        if cleaner.save_dead_links_report(dead_channels, args.report):
            print(f"✓ Dead links report created: {args.report}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
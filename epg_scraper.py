#!/usr/bin/env python3
"""
EPG (Electronic Program Guide) Scraper for Jellyfin
Scrapes and processes EPG data from various sources for IPTV integration with Jellyfin.
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import argparse
import sys
import os
from urllib.parse import urlparse
import gzip
import time

class EPGScraper:
    def __init__(self, timeout=30, verbose=False):
        self.timeout = timeout
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def fetch_epg(self, url):
        """Fetch EPG data from URL"""
        try:
            if self.verbose:
                print(f"Fetching EPG from: {url}")
                
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            content = response.content
            
            # Handle gzipped content
            if response.headers.get('Content-Encoding') == 'gzip':
                content = gzip.decompress(content)
            elif url.endswith('.gz'):
                content = gzip.decompress(content)
                
            return content.decode('utf-8', errors='ignore')
            
        except Exception as e:
            print(f"Error fetching EPG: {e}")
            return None

    def parse_xmltv(self, xml_content):
        """Parse XMLTV format EPG data"""
        try:
            root = ET.fromstring(xml_content)
            
            channels = {}
            programmes = []
            
            # Parse channels
            for channel in root.findall('channel'):
                channel_id = channel.get('id')
                display_name = channel.find('display-name')
                if display_name is not None:
                    channels[channel_id] = {
                        'id': channel_id,
                        'name': display_name.text,
                        'icon': None
                    }
                    
                    # Get channel icon if available
                    icon = channel.find('icon')
                    if icon is not None:
                        channels[channel_id]['icon'] = icon.get('src')
            
            # Parse programmes
            for programme in root.findall('programme'):
                prog_data = {
                    'channel': programme.get('channel'),
                    'start': programme.get('start'),
                    'stop': programme.get('stop'),
                    'title': '',
                    'desc': '',
                    'category': []
                }
                
                title = programme.find('title')
                if title is not None:
                    prog_data['title'] = title.text or ''
                    
                desc = programme.find('desc')
                if desc is not None:
                    prog_data['desc'] = desc.text or ''
                    
                # Get categories
                for category in programme.findall('category'):
                    if category.text:
                        prog_data['category'].append(category.text)
                        
                programmes.append(prog_data)
                
            return channels, programmes
            
        except ET.ParseError as e:
            print(f"XML parsing error: {e}")
            return {}, []
        except Exception as e:
            print(f"Error parsing XMLTV: {e}")
            return {}, []

    def filter_programmes(self, programmes, days_ahead=7):
        """Filter programmes to only include upcoming shows within specified days"""
        if not programmes:
            return []
            
        now = datetime.now()
        end_date = now + timedelta(days=days_ahead)
        
        filtered = []
        for prog in programmes:
            try:
                # Parse XMLTV datetime format: 20231201120000 +0000
                start_str = prog['start'][:14]  # Take first 14 characters
                start_time = datetime.strptime(start_str, '%Y%m%d%H%M%S')
                
                if now <= start_time <= end_date:
                    filtered.append(prog)
                    
            except (ValueError, KeyError):
                continue
                
        return sorted(filtered, key=lambda x: x['start'])

    def clean_epg_data(self, channels, programmes):
        """Clean and optimize EPG data"""
        # Remove channels with no programmes
        active_channels = set(prog['channel'] for prog in programmes)
        cleaned_channels = {
            ch_id: ch_data for ch_id, ch_data in channels.items() 
            if ch_id in active_channels
        }
        
        # Clean programme data
        cleaned_programmes = []
        for prog in programmes:
            if prog['channel'] in cleaned_channels:
                # Clean title and description
                prog['title'] = prog['title'].strip()
                prog['desc'] = prog['desc'].strip()
                
                # Remove empty categories
                prog['category'] = [cat.strip() for cat in prog['category'] if cat.strip()]
                
                cleaned_programmes.append(prog)
                
        return cleaned_channels, cleaned_programmes

    def generate_xmltv(self, channels, programmes, output_file):
        """Generate clean XMLTV file"""
        try:
            root = ET.Element('tv')
            root.set('generator-info-name', 'Jellyfin EPG Scraper')
            root.set('generator-info-url', 'https://github.com/thecroxdevil/jellyfin-setup')
            
            # Add channels
            for ch_id, ch_data in channels.items():
                channel_elem = ET.SubElement(root, 'channel')
                channel_elem.set('id', ch_id)
                
                display_name = ET.SubElement(channel_elem, 'display-name')
                display_name.text = ch_data['name']
                
                if ch_data.get('icon'):
                    icon_elem = ET.SubElement(channel_elem, 'icon')
                    icon_elem.set('src', ch_data['icon'])
            
            # Add programmes
            for prog in programmes:
                prog_elem = ET.SubElement(root, 'programme')
                prog_elem.set('channel', prog['channel'])
                prog_elem.set('start', prog['start'])
                prog_elem.set('stop', prog['stop'])
                
                if prog['title']:
                    title_elem = ET.SubElement(prog_elem, 'title')
                    title_elem.text = prog['title']
                
                if prog['desc']:
                    desc_elem = ET.SubElement(prog_elem, 'desc')
                    desc_elem.text = prog['desc']
                
                for category in prog['category']:
                    cat_elem = ET.SubElement(prog_elem, 'category')
                    cat_elem.text = category
            
            # Write to file
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            
            return True
            
        except Exception as e:
            print(f"Error generating XMLTV file: {e}")
            return False

    def process_epg_source(self, url, output_file, days_ahead=7):
        """Process EPG from source URL and save clean version"""
        print(f"Processing EPG source: {url}")
        
        # Fetch EPG data
        xml_content = self.fetch_epg(url)
        if not xml_content:
            return False
            
        # Parse XMLTV data
        channels, programmes = self.parse_xmltv(xml_content)
        if not channels or not programmes:
            print("No valid EPG data found")
            return False
            
        print(f"Found {len(channels)} channels and {len(programmes)} programmes")
        
        # Filter programmes
        filtered_programmes = self.filter_programmes(programmes, days_ahead)
        print(f"Filtered to {len(filtered_programmes)} upcoming programmes")
        
        # Clean data
        clean_channels, clean_programmes = self.clean_epg_data(channels, filtered_programmes)
        print(f"Cleaned to {len(clean_channels)} active channels")
        
        # Generate output file
        if self.generate_xmltv(clean_channels, clean_programmes, output_file):
            print(f"EPG saved to: {output_file}")
            return True
        else:
            return False

def main():
    parser = argparse.ArgumentParser(description='EPG Scraper for Jellyfin IPTV')
    parser.add_argument('url', help='EPG source URL (XMLTV format)')
    parser.add_argument('-o', '--output', default='jellyfin_epg.xml', help='Output EPG file')
    parser.add_argument('-d', '--days', type=int, default=7, help='Days ahead to include (default: 7)')
    parser.add_argument('-t', '--timeout', type=int, default=30, help='Request timeout (default: 30s)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    print("Jellyfin EPG Scraper")
    print("===================")
    print(f"Source URL: {args.url}")
    print(f"Output file: {args.output}")
    print(f"Days ahead: {args.days}")
    print()
    
    scraper = EPGScraper(timeout=args.timeout, verbose=args.verbose)
    
    success = scraper.process_epg_source(args.url, args.output, args.days)
    
    if success:
        print("\n✓ EPG processing completed successfully")
        return 0
    else:
        print("\n✗ EPG processing failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

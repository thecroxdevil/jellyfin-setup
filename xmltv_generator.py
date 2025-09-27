#!/usr/bin/env python3
"""
XMLTV Generator for Jellyfin
Generate XMLTV-compatible EPG files from multiple sources and formats.
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import argparse
import sys
import os
import requests
import re
from urllib.parse import urlparse

class XMLTVGenerator:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.channels = {}
        self.programmes = []

    def log(self, message):
        """Print message if verbose mode is enabled"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def add_channel(self, channel_id, display_name, icon_url=None):
        """Add a channel to the EPG"""
        self.channels[channel_id] = {
            'id': channel_id,
            'display_name': display_name,
            'icon': icon_url
        }
        self.log(f"Added channel: {display_name} ({channel_id})")

    def add_programme(self, channel_id, start_time, stop_time, title, description='', category=None):
        """Add a programme to the EPG"""
        if category is None:
            category = []
        elif isinstance(category, str):
            category = [category]

        programme = {
            'channel': channel_id,
            'start': start_time,
            'stop': stop_time,
            'title': title,
            'desc': description,
            'category': category
        }
        
        self.programmes.append(programme)
        self.log(f"Added programme: {title} on {channel_id}")

    def format_xmltv_time(self, dt, timezone='+0000'):
        """Format datetime for XMLTV format"""
        if isinstance(dt, str):
            return dt  # Already formatted
        return dt.strftime('%Y%m%d%H%M%S') + ' ' + timezone

    def parse_time(self, time_str):
        """Parse various time formats to datetime"""
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y%m%d%H%M%S',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y %H:%M'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        
        raise ValueError(f"Unable to parse time: {time_str}")

    def load_from_json(self, json_file):
        """Load EPG data from JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load channels
            if 'channels' in data:
                for channel in data['channels']:
                    self.add_channel(
                        channel['id'],
                        channel['name'],
                        channel.get('icon')
                    )
            
            # Load programmes
            if 'programmes' in data:
                for prog in data['programmes']:
                    start_dt = self.parse_time(prog['start'])
                    stop_dt = self.parse_time(prog['stop'])
                    
                    self.add_programme(
                        prog['channel'],
                        self.format_xmltv_time(start_dt),
                        self.format_xmltv_time(stop_dt),
                        prog['title'],
                        prog.get('description', ''),
                        prog.get('category', [])
                    )
            
            self.log(f"Loaded EPG from JSON: {len(self.channels)} channels, {len(self.programmes)} programmes")
            return True
            
        except Exception as e:
            print(f"Error loading JSON file: {e}")
            return False

    def load_from_csv(self, csv_file):
        """Load EPG data from CSV file"""
        try:
            import csv
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    channel_id = row.get('channel_id', '')
                    channel_name = row.get('channel_name', '')
                    
                    if channel_id and channel_name:
                        self.add_channel(channel_id, channel_name, row.get('icon'))
                    
                    if all(k in row for k in ['start', 'stop', 'title']):
                        start_dt = self.parse_time(row['start'])
                        stop_dt = self.parse_time(row['stop'])
                        
                        self.add_programme(
                            channel_id,
                            self.format_xmltv_time(start_dt),
                            self.format_xmltv_time(stop_dt),
                            row['title'],
                            row.get('description', ''),
                            row.get('category', '').split(',') if row.get('category') else []
                        )
            
            self.log(f"Loaded EPG from CSV: {len(self.channels)} channels, {len(self.programmes)} programmes")
            return True
            
        except Exception as e:
            print(f"Error loading CSV file: {e}")
            return False

    def generate_demo_data(self, num_channels=5, num_programmes_per_channel=10):
        """Generate demo EPG data for testing"""
        self.log("Generating demo EPG data...")
        
        # Demo channels
        demo_channels = [
            ('ch1', 'Demo News Channel', 'https://example.com/news.png'),
            ('ch2', 'Demo Sports Channel', 'https://example.com/sports.png'),
            ('ch3', 'Demo Entertainment', 'https://example.com/entertainment.png'),
            ('ch4', 'Demo Movies', 'https://example.com/movies.png'),
            ('ch5', 'Demo Kids Channel', 'https://example.com/kids.png')
        ]
        
        for i in range(min(num_channels, len(demo_channels))):
            ch_id, ch_name, ch_icon = demo_channels[i]
            self.add_channel(ch_id, ch_name, ch_icon)
            
            # Generate programmes for this channel
            current_time = datetime.now()
            
            for j in range(num_programmes_per_channel):
                start_time = current_time + timedelta(hours=j)
                stop_time = start_time + timedelta(hours=1)
                
                title = f"Programme {j+1}"
                description = f"Demo programme {j+1} on {ch_name}"
                category = ['Demo', 'Test']
                
                if 'News' in ch_name:
                    title = f"News Bulletin {j+1}"
                    category = ['News']
                elif 'Sports' in ch_name:
                    title = f"Sports Update {j+1}"
                    category = ['Sports']
                elif 'Movies' in ch_name:
                    title = f"Movie Title {j+1}"
                    category = ['Movies', 'Drama']
                elif 'Kids' in ch_name:
                    title = f"Kids Show {j+1}"
                    category = ['Kids', 'Educational']
                
                self.add_programme(
                    ch_id,
                    self.format_xmltv_time(start_time),
                    self.format_xmltv_time(stop_time),
                    title,
                    description,
                    category
                )

    def validate_epg_data(self):
        """Validate EPG data for consistency"""
        errors = []
        
        # Check for programmes without corresponding channels
        programme_channels = set(prog['channel'] for prog in self.programmes)
        channel_ids = set(self.channels.keys())
        
        orphaned_channels = programme_channels - channel_ids
        if orphaned_channels:
            errors.append(f"Programmes reference unknown channels: {orphaned_channels}")
        
        # Check for time format consistency
        for i, prog in enumerate(self.programmes):
            try:
                # Validate time format
                if not re.match(r'\d{14} [+-]\d{4}', prog['start']):
                    errors.append(f"Programme {i}: Invalid start time format: {prog['start']}")
                if not re.match(r'\d{14} [+-]\d{4}', prog['stop']):
                    errors.append(f"Programme {i}: Invalid stop time format: {prog['stop']}")
            except Exception as e:
                errors.append(f"Programme {i}: Time validation error: {e}")
        
        if errors:
            print("EPG Validation Errors:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        self.log("EPG data validation passed")
        return True

    def generate_xmltv(self, output_file):
        """Generate XMLTV file"""
        try:
            # Validate data first
            if not self.validate_epg_data():
                print("EPG data validation failed, generating anyway...")
            
            root = ET.Element('tv')
            root.set('generator-info-name', 'Jellyfin XMLTV Generator')
            root.set('generator-info-url', 'https://github.com/thecroxdevil/jellyfin-setup')
            
            # Add channels
            for ch_id, ch_data in self.channels.items():
                channel_elem = ET.SubElement(root, 'channel')
                channel_elem.set('id', ch_id)
                
                display_name = ET.SubElement(channel_elem, 'display-name')
                display_name.text = ch_data['display_name']
                
                if ch_data.get('icon'):
                    icon_elem = ET.SubElement(channel_elem, 'icon')
                    icon_elem.set('src', ch_data['icon'])
            
            # Add programmes
            for prog in self.programmes:
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
                    if category.strip():
                        cat_elem = ET.SubElement(prog_elem, 'category')
                        cat_elem.text = category.strip()
            
            # Write to file with proper formatting
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ", level=0)
            tree.write(output_file, encoding='utf-8', xml_declaration=True)
            
            self.log(f"XMLTV file generated: {output_file}")
            self.log(f"  - {len(self.channels)} channels")
            self.log(f"  - {len(self.programmes)} programmes")
            
            return True
            
        except Exception as e:
            print(f"Error generating XMLTV file: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='XMLTV Generator for Jellyfin')
    parser.add_argument('-o', '--output', default='generated_epg.xml', help='Output XMLTV file')
    parser.add_argument('-j', '--json', help='Input JSON file')
    parser.add_argument('-c', '--csv', help='Input CSV file')
    parser.add_argument('-d', '--demo', action='store_true', help='Generate demo data')
    parser.add_argument('--demo-channels', type=int, default=5, help='Number of demo channels')
    parser.add_argument('--demo-programmes', type=int, default=10, help='Programmes per channel')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not any([args.json, args.csv, args.demo]):
        print("Error: Please specify input source (--json, --csv, or --demo)")
        return 1
    
    print("Jellyfin XMLTV Generator")
    print("=======================")
    
    generator = XMLTVGenerator(verbose=args.verbose)
    
    success = True
    
    # Load data from various sources
    if args.json:
        print(f"Loading from JSON: {args.json}")
        success &= generator.load_from_json(args.json)
    
    if args.csv:
        print(f"Loading from CSV: {args.csv}")
        success &= generator.load_from_csv(args.csv)
    
    if args.demo:
        print(f"Generating demo data: {args.demo_channels} channels, {args.demo_programmes} programmes each")
        generator.generate_demo_data(args.demo_channels, args.demo_programmes)
    
    if not success:
        print("Failed to load input data")
        return 1
    
    # Generate XMLTV file
    print(f"Generating XMLTV file: {args.output}")
    if generator.generate_xmltv(args.output):
        print(f"\n✓ XMLTV file generated successfully: {args.output}")
        return 0
    else:
        print(f"\n✗ Failed to generate XMLTV file")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# .github/scripts/utils/issue_parser.py
from typing import Dict, Set

class IssueParser:
    """Parser for GitHub issue bodies with form data"""

    EVENT_FIELDS = {
        'title', 'date', 'url', 'description', 
        'community', 'location', 'is_online'
    }

    COMMUNITY_FIELDS = {
        'community_name', 'display_name', 'contact_persons',  # Updated from contacts
        'website', 'meetup_url', 'linkedin_url', 'x/twitter_url',  # Updated URLs
        'mastodon_url', 'bluesky_url', 'event_source',
        'event_statuses_to_sync', 'description', 'additional_information'
    }

    @classmethod
    def parse_issue_body(cls, body: str, issue_type: str = 'event') -> Dict:
        """
        Parse the issue body form data into a dictionary.
        
        Args:
            body: The issue body text to parse
            issue_type: Type of issue to parse ('event' or 'community')
        
        Returns:
            Dictionary containing the parsed form data
        """
        data = {}
        lines = body.split('\n')
        current_field = None
        current_value = []
        
        known_fields = cls.EVENT_FIELDS if issue_type == 'event' else cls.COMMUNITY_FIELDS
        special_fields = ['description', 'additional_info']
        
        def clean_value(value: str) -> str:
            """Clean a field value, handling empty responses"""
            cleaned = value.strip()
            if cleaned == '_No response_':
                return ''
            return cleaned

        def is_new_field(line: str) -> bool:
            """Check if a line is a new field header"""
            if not line.startswith('### '):
                return False
            # Handle known field variations
            field = process_field_name(line)
            return field in known_fields

        def process_field_name(field_header: str) -> str:
            """Process a field header into a field name"""
            # Remove ### and clean up
            field = field_header.replace('### ', '').strip()
            
            # Special case mappings
            field_mappings = {
                'Community name (as folder name)': 'community_name',
                'Contact persons': 'contact_persons',
                'LinkedIn URL': 'linkedin_url',
                'X/Twitter URL': 'x/twitter_url',
                'Mastodon URL': 'mastodon_url',
                'Bluesky URL': 'bluesky_url',
                'Event statuses to sync': 'event_statuses_to_sync',
                'Additional information': 'additional_information'
            }
            
            if field in field_mappings:
                return field_mappings[field]
                
            # Default processing
            return field.lower().replace(' ', '_')

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip confirmation section for community issues
            if issue_type == 'community' and line.startswith('### Confirmation'):
                i += 1
                continue
            
            # Check for new field
            if is_new_field(line):
                # Save previous field if exists
                if current_field and current_value:
                    data[current_field] = clean_value('\n'.join(current_value).strip())
                    current_value = []
                
                # Start new field
                current_field = process_field_name(line)
            
            # Handle non-header lines
            elif line or current_field in special_fields:  # Keep empty lines for special fields
                if current_field in special_fields:
                    # For special fields like description, keep all content including markdown
                    current_value.append(line)
                elif current_field and not line.startswith('#'):
                    # For other fields, only keep non-header content
                    current_value.append(line)
            
            i += 1
        
        # Save the last field
        if current_field and current_value:
            data[current_field] = clean_value('\n'.join(current_value).strip())

        # Map contact_persons to contacts for backward compatibility
        if issue_type == 'community' and 'contact_persons' in data:
            data['contacts'] = data['contact_persons']
        
        return data
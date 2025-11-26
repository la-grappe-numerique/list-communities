# utils/issue_parser.py
from typing import Dict, Set

class IssueParser:
    """Parser for GitHub issue bodies with form data"""

    # Field mappings from form labels to internal field names
    FIELD_MAPPINGS = {
        'event': {
            'Event Title': 'event_title',
            'Event Date': 'event_date',
            'Event URL': 'event_url',
            'Description': 'description',
            'Community': 'community',
            'Location': 'location',
            'Is this an online event?': 'is_this_an_online_event'
        },
        'community': {
            # Labels français
            'Nom de la communauté (nom du dossier)': 'community_name',
            'Nom d\'affichage': 'display_name',
            'Texte de présentation pour le vote': 'description',
            'Personnes de contact': 'contact_persons',
            'Site web': 'website',
            'URL Meetup': 'meetup_url',
            'URL LinkedIn': 'linkedin_url',
            'URL X/Twitter': 'x/twitter_url',
            'URL Mastodon': 'mastodon_url',
            'URL Bluesky': 'bluesky_url',
            'Source des événements': 'event_source',
            'Statuts des événements à synchroniser': 'event_statuses_to_sync',
            'Informations complémentaires': 'additional_information'
        }
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
        
        mappings = cls.FIELD_MAPPINGS[issue_type]
        special_fields = {'description'}  # Fields that keep markdown formatting

        def process_field_name(field_header: str) -> str:
            """Convert a form field header to internal field name"""
            # Remove ### and clean
            field = field_header.replace('### ', '').strip()
            # Return mapped field name if exists
            return mappings.get(field)

        def is_new_field(line: str) -> bool:
            """Check if a line is a new field header"""
            if not line.startswith('### '):
                return False
            # Skip confirmation section for community issues
            if line.strip('# ').lower() == 'confirmation':
                return False
            # Check if field exists in mappings
            field = line.replace('### ', '').strip()
            return field in mappings

        def clean_value(value: str) -> str:
            """Clean a field value, handling empty responses"""
            cleaned = value.strip()
            return '' if cleaned == '_No response_' else cleaned

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
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
        
        return data
from typing import Generator, Optional, Dict, Any, List
from openai import OpenAI

from src.models.listing import Listing
from src.models.email import EmailData
from src.models.communication import Communication, CommunicationType, CommunicationStatus
from src.database.db import DatabaseManager
from src.config import settings
import json


class ListingAgent:
    """Intelligent agent for handling rental listing communications and outreach"""
    
    def __init__(self, db_path: Optional[str] = None, openai_api_key: Optional[str] = None, 
                 user_profile: Optional[Dict[str, Any]] = None):
        """Initialize the listing agent
        
        Args:
            db_path: Path to SQLite database file
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            user_profile: User profile information for personalizing communications
        """
        self.db = DatabaseManager(db_path)
        
        # Initialize OpenAI client
        api_key = openai_api_key or settings.openai_api_key
        if not api_key:
            raise ValueError("OpenAI API key must be provided via parameter or OPENAI_API_KEY environment variable")
        
        self.openai_client = OpenAI(api_key=api_key)
        
        # Store user profile for email personalization
        self.user_profile = user_profile or {}
        
        # Email generation prompt
        self.email_prompt = """
You are a helpful assistant that generates personalized rental inquiry emails. Create a professional, friendly email to inquire about a rental listing.

The email should:
- Be polite but casual
- Keep it brief.
- Express genuine interest in the property but don't sound robotic
- Include a brief introduction about the renter using their profile information
- Ask relevant questions about the property
- Request to schedule a viewing if appropriate
- Be concise but thorough
- Make sure to fill out everything as best of your knowledge from the information provided.
- Very important that you do not leave placeholders with [] anywhere in the email. What you write is what gets sent out without any modification. 

Based on the listing details, user profile, and any preferences provided, generate an email that would be appropriate to send to the listing contact.

Listing details:
Title: {title}
Price: ${price}/{price_period}
Dates: {start_date} to {end_date}
Neighborhood: {neighborhood}
Description: {description}
Contact: {contact_name}

Renter profile:
Name: {user_name}
Phone: {user_phone}
Occupation: {user_occupation}
User Note: {user_note}
Bio/Background: {user_bio}
References: {user_references}

User preferences/filters applied:
{filter_context}

Generate a complete email with subject line and body. Return the response as a JSON object with the following structure:
{{
    "subject": "Email subject line",
    "body": "Complete email body text"
}}
"""
    
    
    def generate_email(self, listing: Listing, filters: Optional[Dict[str, Any]] = None) -> EmailData:
        """Generate an email for a rental listing inquiry
        
        Args:
            listing: The Listing object to generate email for
            filters: Optional filter context to personalize the email
            
        Returns:
            EmailData object with structured email content
        """
        # Build filter context string
        filter_context = "No specific preferences provided"
        if filters:
            context_parts = []
            if 'min_price' in filters and filters['min_price']:
                context_parts.append(f"Budget minimum: ${filters['min_price']}")
            if 'max_price' in filters and filters['max_price']:
                context_parts.append(f"Budget maximum: ${filters['max_price']}")
            if 'start_date_after' in filters and filters['start_date_after']:
                context_parts.append(f"Need to move in after: {filters['start_date_after']}")
            if 'end_date_before' in filters and filters['end_date_before']:
                context_parts.append(f"Need to move out before: {filters['end_date_before']}")
            
            if context_parts:
                filter_context = "; ".join(context_parts)
        
        # Format the prompt with listing details and user profile
        prompt = self.email_prompt.format(
            title=listing.title or "No title",
            price=listing.price or "Unknown",
            price_period=listing.price_period or "Unknown",
            start_date=listing.start_date.strftime("%Y-%m-%d") if listing.start_date else "Unknown",
            end_date=listing.end_date.strftime("%Y-%m-%d") if listing.end_date else "Unknown", 
            neighborhood=listing.neighborhood or "Unknown",
            description=(listing.full_description or listing.brief_description or "No description available")[:1000],
            contact_name=listing.contact_name or "the landlord",
            user_name=self.user_profile.get('name', 'Not provided'),
            user_phone=self.user_profile.get('phone', 'Not provided'),
            user_email=self.user_profile.get('email', 'Not provided'),
            user_note=self.user_profile.get('user_note', 'Not provided'),
            user_occupation=self.user_profile.get('occupation', 'Not provided'),
            user_bio=self.user_profile.get('bio', 'Not provided'),
            user_references=self.user_profile.get('references', 'Not provided'),
            filter_context=filter_context
        )
        
        # Call OpenAI API with structured output
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Use cost-effective model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates professional rental inquiry emails. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7,  # Slightly higher temperature for more natural email generation
            response_format={"type": "json_object"}
        )
        
        # Parse the JSON response
        try:
            email_json = json.loads(response.choices[0].message.content.strip())
            
            # Create EmailData object
            email_data = EmailData(
                subject=email_json.get("subject", "Rental Inquiry"),
                body=email_json.get("body", ""),
                to_email=listing.contact_email or "",
                to_name=listing.contact_name,
                from_email=self.user_profile.get('email'),
                from_name=self.user_profile.get('name'),
                listing_id=listing.id
            )
            
            return email_data
            
        except json.JSONDecodeError as e:
            # Fallback to basic email if JSON parsing fails
            return EmailData(
                subject="Rental Inquiry",
                body=response.choices[0].message.content.strip(),
                to_email=listing.contact_email or "",
                to_name=listing.contact_name,
                from_email=self.user_profile.get('email'),
                from_name=self.user_profile.get('name'),
                listing_id=listing.id
            )
    
    def send_email_for_listing(self, listing: Listing, email_client, filters: Optional[Dict[str, Any]] = None, 
                              force_resend: bool = False) -> Dict[str, Any]:
        """Generate and send email for a listing with duplicate prevention
        
        Args:
            listing: The Listing object to send email for
            email_client: EmailClient instance for sending
            filters: Optional filter context to personalize the email
            force_resend: If True, send even if already sent
            
        Returns:
            Dictionary with result information
        """
        result = {
            'success': False,
            'communication_id': None,
            'message': '',
            'already_sent': False
        }
        
        # Check if email already sent (unless force_resend)
        if not force_resend and self.db.has_successful_communication(listing.id, CommunicationType.EMAIL):
            result['already_sent'] = True
            result['message'] = f"Email already sent for listing {listing.id}"
            return result
        
        try:
            # Generate email content
            email_data = self.generate_email(listing, filters)
            
            # Create communication record
            communication = Communication.create_email(
                listing_id=listing.id,
                subject=email_data.subject,
                body=email_data.body,
                to_email=email_data.to_email,
                to_name=email_data.to_name,
                from_email=email_data.from_email,
                from_name=email_data.from_name
            )
            
            # Insert communication into database
            if not self.db.insert_communication(communication):
                result['message'] = f"Failed to save communication record for listing {listing.id}"
                return result
            
            result['communication_id'] = communication.id
            
            # Attempt to send email
            try:
                success = email_client.send_email(email_data, dry_run=True)
                
                if success:
                    # Mark as sent in database
                    self.db.mark_communication_sent(communication.id)
                    result['success'] = True
                    result['message'] = f"Email sent successfully to {email_data.to_email}"
                else:
                    # Mark as failed in database
                    self.db.mark_communication_failed(communication.id, "Email sending failed")
                    result['message'] = f"Failed to send email to {email_data.to_email}"
                    
            except Exception as send_error:
                # Mark as failed in database
                self.db.mark_communication_failed(communication.id, str(send_error))
                result['message'] = f"Email sending error: {str(send_error)}"
            
            return result
            
        except Exception as e:
            result['message'] = f"Error processing email for listing {listing.id}: {str(e)}"
            return result
    
    def get_unsent_listings(self, communication_type: CommunicationType = CommunicationType.EMAIL) -> Generator[Listing, None, None]:
        """Get listings that haven't been contacted yet
        
        Args:
            communication_type: Type of communication to check for
            
        Yields:
            Listing objects that haven't been contacted
        """
        unsent_data = self.db.get_unsent_listings(communication_type)
        
        for data in unsent_data:
            yield self._dict_to_listing(data)
    
    def get_communication_history(self, listing_id: str) -> List[Communication]:
        """Get all communications for a specific listing
        
        Args:
            listing_id: The unique listing ID
            
        Returns:
            List of Communication objects
        """
        return self.db.get_communications_for_listing(listing_id)
    
    def get_pending_communications(self, communication_type: Optional[CommunicationType] = None) -> List[Communication]:
        """Get all pending communications
        
        Args:
            communication_type: Optional filter by communication type
            
        Returns:
            List of pending Communication objects
        """
        return self.db.get_pending_communications(communication_type)
    
    def retry_failed_communications(self, email_client, max_attempts: int = 3) -> Dict[str, Any]:
        """Retry failed email communications
        
        Args:
            email_client: EmailClient instance for sending
            max_attempts: Maximum number of attempts before giving up
            
        Returns:
            Dictionary with retry statistics
        """
        stats = {
            'total_retried': 0,
            'successful': 0,
            'still_failed': 0,
            'skipped': 0
        }
        
        # Get failed email communications that haven't exceeded max attempts
        failed_comms = []
        for comm in self.db.get_pending_communications(CommunicationType.EMAIL):
            if comm.has_failed() and comm.attempts < max_attempts:
                failed_comms.append(comm)
        
        for comm in failed_comms:
            stats['total_retried'] += 1
            
            try:
                # Get the original listing
                listing_data = self.db.get_listing_by_id(comm.listing_id)
                if not listing_data:
                    stats['skipped'] += 1
                    continue
                
                listing = self._dict_to_listing(listing_data)
                
                # Create EmailData from communication
                email_data = EmailData(
                    subject=comm.subject,
                    body=comm.body,
                    to_email=comm.to_email,
                    to_name=comm.to_name,
                    from_email=comm.from_email,
                    from_name=comm.from_name,
                    listing_id=comm.listing_id
                )
                
                # Attempt to send
                success = email_client.send_email(email_data, dry_run=False)
                
                if success:
                    self.db.mark_communication_sent(comm.id)
                    stats['successful'] += 1
                else:
                    self.db.mark_communication_failed(comm.id, "Retry attempt failed")
                    stats['still_failed'] += 1
                    
            except Exception as e:
                self.db.mark_communication_failed(comm.id, f"Retry error: {str(e)}")
                stats['still_failed'] += 1
        
        return stats
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics from database
        
        Returns:
            Dictionary with communication statistics
        """
        return self.db.get_communication_stats()
    
    def _dict_to_listing(self, data: Dict[str, Any]) -> Listing:
        """Convert database dictionary back to Listing object
        
        Args:
            data: Dictionary from database
            
        Returns:
            Listing object
        """
        from ..models.listing import ListingType
        from dateutil import parser
        
        return Listing(
            id=data['id'],
            url=data['url'],
            title=data['title'],
            price=data['price'],
            price_period=data['price_period'],
            start_date=parser.parse(data['start_date']) if data['start_date'] else None,
            end_date=parser.parse(data['end_date']) if data['end_date'] else None,
            neighborhood=data['neighborhood'],
            brief_description=data['brief_description'],
            full_description=data['full_description'],
            contact_name=data['contact_name'],
            contact_email=data['contact_email'],
            source_site=data['source_site'],
            listing_type=ListingType(data['listing_type']),
            scraped_at=parser.parse(data['scraped_at']) if data['scraped_at'] else None
        )
    
    
    def build_user_filters(self) -> Dict[str, Any]:
        """Extract filtering criteria from user_profile (price and date only)
        
        Returns:
            Dictionary with filter criteria for database queries
        """
        filters = {}
        
        # Extract user email for communication tracking
        if self.user_profile.get('email'):
            filters['user_email'] = self.user_profile['email']
        
        # Price filters (assume user specifies monthly preferences)
        if self.user_profile.get('min_price'):
            filters['min_price'] = self.user_profile['min_price']
        
        if self.user_profile.get('max_price'):
            filters['max_price'] = self.user_profile['max_price']
        
        # Date filters
        if self.user_profile.get('start_date_after'):
            filters['start_date_after'] = self.user_profile['start_date_after']
            
        if self.user_profile.get('start_date_before'):
            filters['start_date_before'] = self.user_profile['start_date_before']
            
        if self.user_profile.get('end_date_after'):
            filters['end_date_after'] = self.user_profile['end_date_after']
        
        return filters
    
    def get_candidate_listings(self) -> Generator[Listing, None, None]:
        """Get listings that match user filters and haven't been contacted
        
        Yields:
            Listing objects that are candidates for this user
        """
        import sqlite3
        
        filters = self.build_user_filters()

        # Base query: listings not contacted by this user
        query = """
            SELECT l.* FROM listings l
            LEFT JOIN communications c ON l.id = c.listing_id 
                AND c.from_email = ? AND c.communication_type = 'email'
            WHERE c.id IS NULL
        """
        params = [filters.get('user_email', '')]
        
        # Add price filters (for monthly listings only - other periods handled in Python)
        if filters.get('min_price'):
            query += " AND (l.price_period != 'month' OR l.price >= ?)"
            params.append(filters['min_price'])
            
        if filters.get('max_price'):
            query += " AND (l.price_period != 'month' OR l.price <= ?)"
            params.append(filters['max_price'])
        

        # Add date filters
        if filters.get('start_date_after'):
            query += " AND l.start_date >= ?"
            params.append(filters['start_date_after'])

        if filters.get('start_date_before'):
            query += " AND l.start_date <= ?"
            params.append(filters['start_date_before'])
            
        if filters.get('end_date_after'):
            query += " AND l.end_date >= ?"
            params.append(filters['end_date_after'])
        
        #Order by most recent first
        query += " ORDER BY l.scraped_at DESC"
        
        print(query)
        # Execute query and yield listings
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            for row in cursor.fetchall():
                listing = self._dict_to_listing(dict(row))
                
                # Apply price period filtering for non-monthly listings
                if listing.price and listing.price_period and listing.price_period != 'month':
                    monthly_price = listing.monthly_price()
                    
                    # Check if converted price passes user filters
                    if monthly_price and filters.get('min_price') and monthly_price < filters['min_price']:
                        continue
                    if monthly_price and filters.get('max_price') and monthly_price > filters['max_price']:
                        continue
                
                yield listing
    

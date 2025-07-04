import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime
import os

from ..models.email import EmailData


#TODO: use oauth client instead
class EmailClient:
    
    def __init__(self, smtp_server: str = "smtp.gmail.com", smtp_port: int = 587, 
                 username: Optional[str] = None, password: Optional[str] = None):
        """Initialize email client
        
        Args:
            smtp_server: SMTP server address (default: Gmail)
            smtp_port: SMTP server port (default: 587 for TLS)
            username: Email username (defaults to EMAIL_USERNAME env var)
            password: Email password (defaults to EMAIL_PASSWORD env var)
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username or os.getenv('EMAIL_USERNAME')
        self.password = password or os.getenv('EMAIL_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("Email credentials must be provided via parameters or EMAIL_USERNAME/EMAIL_PASSWORD environment variables")
    
    def send_email(self, email_data: EmailData, dry_run: bool = False) -> bool:
        """Send an email
        
        Args:
            email_data: EmailData object containing email details
            dry_run: If True, only print the email without sending
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if dry_run:
            print("🔍 DRY RUN - Email would be sent:")
            print(f"To: {email_data.to_email} ({email_data.to_name})")
            print(f"From: {email_data.from_email} ({email_data.from_name})")
            print(f"Subject: {email_data.subject}")
            print(f"Body:\n{email_data.body}")
            print("-" * 50)
            return True
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = email_data.subject
            message["From"] = f"{email_data.from_name} <{email_data.from_email}>" if email_data.from_name else email_data.from_email
            message["To"] = f"{email_data.to_name} <{email_data.to_email}>" if email_data.to_name else email_data.to_email
            
            # Create plain text part
            text_part = MIMEText(email_data.body, "plain")
            message.attach(text_part)
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Connect and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                
                # Send email
                server.send_message(message)
                
                # Update sent timestamp
                email_data.sent_at = datetime.now()
                
                print(f"✅ Email sent successfully to {email_data.to_email}")
                return True
                
        except Exception as e:
            print(f"❌ Failed to send email to {email_data.to_email}: {e}")
            return False
    
    def send_batch_emails(self, email_list: list[EmailData], dry_run: bool = False, 
                         delay_seconds: float = 1.0) -> Dict[str, Any]:
        """Send multiple emails with optional delay
        
        Args:
            email_list: List of EmailData objects
            dry_run: If True, only print emails without sending
            delay_seconds: Delay between emails to avoid rate limiting
            
        Returns:
            Dictionary with sending statistics
        """
        import time
        
        results = {
            'total': len(email_list),
            'sent': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, email_data in enumerate(email_list):
            print(f"📧 Processing email {i+1}/{len(email_list)}")
            
            success = self.send_email(email_data, dry_run)
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(f"Failed to send to {email_data.to_email}")
            
            # Add delay between emails (except for the last one)
            if i < len(email_list) - 1 and delay_seconds > 0:
                time.sleep(delay_seconds)
        
        print(f"\n📊 Batch email results:")
        print(f"Total: {results['total']}")
        print(f"Sent: {results['sent']}")
        print(f"Failed: {results['failed']}")
        
        return results
    
    def test_connection(self) -> bool:
        """Test SMTP connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                print("✅ SMTP connection test successful")
                return True
        except Exception as e:
            print(f"❌ SMTP connection test failed: {e}")
            return False

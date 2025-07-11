#!/usr/bin/env python3
"""Interactive CLI for approving and sending rental inquiry emails"""

from dotenv import load_dotenv

from src.agent.listing_agent import ListingAgent
from src.email.email_client import EmailClient
from src.models.email import EmailData
from src.models.listing import Listing

load_dotenv()


class DwellApp:
    """Interactive CLI application for rental listing management"""

    def __init__(self):
        self.stats = {
            "total": 0,
            "approved": 0,
            "rejected": 0,
            "sent": 0,
            "failed": 0,
            "errors": [],
        }

        # Initialize components
        self.user_profile = {
            "name": "Beakal Teshome",
            "email": "beakal42@gmail.com",
            "phone": "415-995-5782",
            "occupation": "Software Engineer",
            "bio": "Young professional, clean and quiet tenant, non-smoker. Looking for a temporary place while apartment hunting.",
            "user_note": "Trying to find place for the whole month of august 2025 and possibly september",
            # Filtering preferences
            "min_price": 1500,
            "max_price": 4000,
            "start_date_after": "2025-07-29",
            "start_date_before": "2025-08-10",
            "end_date_after": "2025-08-29",
        }

        self.agent = None
        self.email_client = None

    def setup_components(self):
        """Initialize the listing agent and email client"""
        try:
            # Initialize listing agent
            self.agent = ListingAgent(
                db_path="./listingdb", user_profile=self.user_profile
            )

            # Initialize email client
            self.email_client = EmailClient()

            # Test email connection
            print("🔗 Testing email connection...")
            if not self.email_client.test_connection():
                print("⚠️  Email connection failed. Emails will be shown but not sent.")
                self.email_client = None

            return True

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False

    def display_listing_summary(self, listing: Listing, index: int, total: int):
        """Display a summary of the listing"""
        print(f"\n{'=' * 60}")
        print(f"📋 LISTING {index}/{total}")
        print(f"{'=' * 60}")
        print(f"🏠 Title: {listing.title}")
        print(f"💰 Price: ${listing.price}/{listing.price_period}")
        print(
            f"📅 Dates: {listing.start_date.strftime('%Y-%m-%d') if listing.start_date else 'N/A'} to {listing.end_date.strftime('%Y-%m-%d') if listing.end_date else 'N/A'}"
        )
        print(f"📍 Location: {listing.neighborhood}")
        print(f"👤 Contact: {listing.contact_name} ({listing.contact_email})")
        print(f"🔗 URL: {listing.url}")
        print(
            f"\n📝 Description: {(listing.full_description or listing.brief_description or 'No description')[:200]}..."
        )

        # Show communication history
        self.display_communication_history(listing.id)

    def display_communication_history(self, listing_id: str):
        """Display communication history for a listing"""
        history = self.agent.get_communication_history(listing_id)
        if history:
            print("\n📞 Communication History:")
            for comm in history[:3]:  # Show last 3 communications
                status_emoji = (
                    "✅" if comm.is_sent() else "❌" if comm.has_failed() else "⏳"
                )
                print(
                    f"   {status_emoji} {comm.communication_type.value.upper()}: {comm.status.value} ({comm.generated_at.strftime('%Y-%m-%d %H:%M') if comm.generated_at else 'N/A'})"
                )
        else:
            print("\n📞 No previous communications")

    def display_email_template(self, email_data: EmailData):
        """Display the generated email template"""
        print(f"\n{'=' * 60}")
        print("📧 GENERATED EMAIL")
        print(f"{'=' * 60}")
        print(f"📤 To: {email_data.to_email} ({email_data.to_name})")
        print(f"📥 From: {email_data.from_email} ({email_data.from_name})")
        print(f"📋 Subject: {email_data.subject}")
        print("\n📝 Body:")
        print("-" * 40)
        print(email_data.body)
        print("-" * 40)

    def get_user_decision(self) -> str:
        """Get user decision on the email"""
        while True:
            print("\n🤔 What would you like to do?")
            print("   [S]end - Send this email")
            print("   [R]eject - Skip this listing")
            print("   [E]dit - Edit email (coming soon)")
            print("   [Q]uit - Exit application")

            choice = input("\nYour choice: ").strip().upper()

            if choice in ["S", "R", "E", "Q"]:
                return choice
            else:
                print("❌ Invalid choice. Please enter S, R, E, or Q.")

    def send_email_with_confirmation(self, listing: Listing) -> bool:
        """Send email using centralized agent logic"""
        if not self.email_client:
            print("⚠️  Email client not available. Simulating send...")
            self.stats["sent"] += 1
            return True

        print(f"\n📤 Sending email for listing {listing.id}...")

        # Use the agent's centralized email sending logic
        result = self.agent.send_email_for_listing(listing, self.email_client)

        if result["success"]:
            print(f"✅ {result['message']}")
            self.stats["sent"] += 1
        elif result["already_sent"]:
            print(f"ℹ️  {result['message']}")
            self.stats["sent"] += 1  # Count as success since it was already sent
        else:
            print(f"❌ {result['message']}")
            self.stats["failed"] += 1
            self.stats["errors"].append(result["message"])

        return result["success"] or result["already_sent"]

    def process_listings(self, max_listings: int = 30):
        """Process unsent listings and handle email approval"""
        print("🚀 Starting email approval process...")
        print(f"📊 Processing up to {max_listings} listings that haven't been emailed")

        # Get communication statistics
        stats = self.agent.get_communication_stats()
        print(
            f"📈 Communication Stats: {stats.get('total_communications', 0)} total, {stats.get('status_counts', {}).get('sent', 0)} sent"
        )

        # Process candidate listings using generator (memory efficient)
        print(f"📋 Processing up to {max_listings} candidate listings...")

        processed = 0

        # Process each candidate listing using generator
        for listing in self.agent.get_candidate_listings():
            if processed >= max_listings:
                print(f"📊 Reached maximum limit of {max_listings} listings")
                break

            processed += 1
            self.stats["total"] += 1

            # Display listing summary
            self.display_listing_summary(listing, processed, max_listings)

            # Generate email preview
            try:
                print("\n🤖 Generating email preview...")
                email_data = self.agent.generate_email(listing)

                # Display email template
                self.display_email_template(email_data)

                # Get user decision
                decision = self.get_user_decision()

                if decision == "S":
                    # Send email using centralized agent logic
                    self.stats["approved"] += 1
                    self.send_email_with_confirmation(listing)

                elif decision == "R":
                    # Reject email - skip this listing
                    self.stats["rejected"] += 1
                    print("❌ Email rejected. Moving to next listing...")

                elif decision == "E":
                    # Edit email (placeholder for future implementation)
                    print("✏️  Edit feature coming soon! For now, rejecting...")
                    self.stats["rejected"] += 1

                elif decision == "Q":
                    # Quit application
                    print("👋 Exiting application...")
                    break

                # Add delay between emails
                if decision == "S":
                    import time

                    print("⏱️  Waiting 2 seconds before next listing...")
                    time.sleep(2)

            except Exception as e:
                print(f"❌ Error processing listing {listing.id}: {e}")
                self.stats["errors"].append(f"Error processing {listing.id}: {str(e)}")

                # Ask user if they want to continue
                continue_choice = (
                    input("\n❓ Continue processing? [Y/n]: ").strip().upper()
                )
                if continue_choice == "N":
                    break

        # Show final count
        if processed == 0:
            print(
                "✨ No candidate listings found! All matching listings have been contacted."
            )
        else:
            print(f"📊 Processed {processed} candidate listings")

    def display_final_stats(self):
        """Display final statistics"""
        print(f"\n{'=' * 60}")
        print("📊 FINAL STATISTICS")
        print(f"{'=' * 60}")
        print(f"Total listings processed: {self.stats['total']}")
        print(f"Emails approved: {self.stats['approved']}")
        print(f"Emails rejected: {self.stats['rejected']}")
        print(f"Emails sent successfully: {self.stats['sent']}")
        print(f"Emails failed to send: {self.stats['failed']}")

        # Show overall communication statistics
        comm_stats = self.agent.get_communication_stats()
        print("\n📈 Overall Communication Statistics:")
        print(f"Total communications: {comm_stats.get('total_communications', 0)}")

        status_counts = comm_stats.get("status_counts", {})
        for status, count in status_counts.items():
            emoji = "✅" if status == "sent" else "❌" if status == "failed" else "⏳"
            print(f"   {emoji} {status.capitalize()}: {count}")

        print(f"Recent activity (7 days): {comm_stats.get('recent_count', 0)}")

        if self.stats["errors"]:
            print("\n❌ Errors encountered:")
            for error in self.stats["errors"]:
                print(f"   • {error}")

        print("\n✅ Email approval session complete!")

    def run(self):
        """Run the interactive rental listing application"""
        print("🏠 Welcome to Dwell")
        print(f"{'=' * 60}")

        # Setup components
        if not self.setup_components():
            return

        # Display user profile
        print("\n👤 User Profile:")
        print(f"   Name: {self.user_profile['name']}")
        print(f"   Email: {self.user_profile['email']}")
        print(f"   Phone: {self.user_profile['phone']}")
        print(f"   Occupation: {self.user_profile['occupation']}")

        # Confirm start
        start_choice = (
            input("\n🚀 Ready to start processing listings? [Y/n]: ").strip().upper()
        )
        if start_choice == "N":
            print("👋 Goodbye!")
            return

        # Process listings
        try:
            self.process_listings(max_listings=20)
        except KeyboardInterrupt:
            print("\n⚠️  Process interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            self.display_final_stats()


def main():
    """Main function"""
    app = DwellApp()
    app.run()


if __name__ == "__main__":
    main()

import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models.listing import Listing
from ..models.communication import Communication, CommunicationStatus, CommunicationType


class DatabaseManager:
    """Manages SQLite database operations for listings"""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager
        
        Args:
            db_path: Path to SQLite database file. If None, uses default path
        """
        if db_path is None:
            # Default to data/listings.db in project root
            project_root = Path(__file__).parent.parent.parent
            data_dir = project_root / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "listings.db")
        
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database and create tables"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r') as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()
    
    def listing_exists(self, listing_id: str) -> bool:
        """Check if a listing already exists in the database
        
        Args:
            listing_id: The unique listing ID
            
        Returns:
            True if listing exists, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM listings WHERE id = ? LIMIT 1", (listing_id,))
            return cursor.fetchone() is not None
    
    def insert_listing(self, listing: Listing, llm_score: Optional[float] = None, 
                      llm_analysis: Optional[str] = None, is_recommended: bool = False) -> bool:
        """Insert a new listing into the database
        
        Args:
            listing: The Listing object to insert
            llm_score: Optional LLM score (0-100)
            llm_analysis: Optional LLM analysis text
            is_recommended: Whether LLM recommends this listing
            
        Returns:
            True if insertion successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                analyzed_at = datetime.now().isoformat() if llm_score is not None else None
                
                cursor.execute("""
                    INSERT INTO listings (
                        id, url, title, price, price_period, start_date, end_date,
                        neighborhood, brief_description, full_description,
                        contact_name, contact_email, source_site, listing_type,
                        scraped_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    listing.id,
                    listing.url,
                    listing.title,
                    listing.price,
                    listing.price_period,
                    listing.start_date.isoformat() if listing.start_date else None,
                    listing.end_date.isoformat() if listing.end_date else None,
                    listing.neighborhood,
                    listing.brief_description,
                    listing.full_description,
                    getattr(listing, 'contact_name', None),
                    getattr(listing, 'contact_email', None),
                    listing.source_site,
                    listing.listing_type.value,
                    listing.scraped_at.isoformat() if listing.scraped_at else datetime.now().isoformat(),
                ))
                conn.commit()
                return True
                
        except sqlite3.IntegrityError as e:
            print(f"Listing {listing.id} already exists in database: {e}")
            return False
        except Exception as e:
            print(f"Error inserting listing {listing.id}: {e}")
            return False
    
    def get_listings(self, limit: Optional[int] = None, 
                    min_score: Optional[float] = None,
                    recommended_only: bool = False,
                    max_price: Optional[float] = None) -> List[Dict[str, Any]]:
        """Retrieve listings from database with optional filtering
        
        Args:
            limit: Maximum number of listings to return
            min_score: Minimum LLM score (0-100)
            recommended_only: Only return recommended listings
            max_price: Maximum price filter
            
        Returns:
            List of listing dictionaries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            query = "SELECT * FROM listings WHERE 1=1"
            params = []
            
            if min_score is not None:
                query += " AND llm_score >= ?"
                params.append(min_score)
            
            if recommended_only:
                query += " AND is_recommended = 1"
            
            if max_price is not None:
                query += " AND price <= ?"
                params.append(max_price)
            
            query += " ORDER BY scraped_at DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_listing_by_id(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific listing by ID
        
        Args:
            listing_id: The unique listing ID
            
        Returns:
            Listing dictionary if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_listing_analysis(self, listing_id: str, llm_score: float, 
                               llm_analysis: str, is_recommended: bool) -> bool:
        """Update LLM analysis for an existing listing
        
        Args:
            listing_id: The unique listing ID
            llm_score: LLM score (0-100)
            llm_analysis: LLM analysis text
            is_recommended: Whether LLM recommends this listing
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE listings 
                    SET llm_score = ?, llm_analysis = ?, is_recommended = ?, analyzed_at = ?
                    WHERE id = ?
                """, (llm_score, llm_analysis, is_recommended, datetime.now().isoformat(), listing_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating listing analysis {listing_id}: {e}")
            return False
    
    # Communications Methods
    
    def insert_communication(self, communication: Communication) -> bool:
        """Insert a new communication into the database
        
        Args:
            communication: The Communication object to insert
            
        Returns:
            True if insertion successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                data = communication.to_dict()
                
                cursor.execute("""
                    INSERT INTO communications (
                        id, listing_id, communication_type, status, subject, body,
                        to_email, to_phone, to_name, from_email, from_phone, from_name,
                        generated_at, sent_at, delivered_at, response_received_at,
                        attempts, last_attempt_at, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['id'],
                    data['listing_id'],
                    data['communication_type'],
                    data['status'],
                    data['subject'],
                    data['body'],
                    data['to_email'],
                    data['to_phone'],
                    data['to_name'],
                    data['from_email'],
                    data['from_phone'],
                    data['from_name'],
                    data['generated_at'],
                    data['sent_at'],
                    data['delivered_at'],
                    data['response_received_at'],
                    data['attempts'],
                    data['last_attempt_at'],
                    data['error_message']
                ))
                conn.commit()
                return True
                
        except sqlite3.IntegrityError as e:
            print(f"Communication {communication.id} already exists in database: {e}")
            return False
        except Exception as e:
            print(f"Error inserting communication {communication.id}: {e}")
            return False
    
    def get_communications_for_listing(self, listing_id: str) -> List[Communication]:
        """Get all communications for a specific listing
        
        Args:
            listing_id: The unique listing ID
            
        Returns:
            List of Communication objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM communications 
                WHERE listing_id = ? 
                ORDER BY generated_at DESC
            """, (listing_id,))
            
            return [Communication.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_pending_communications(self, communication_type: Optional[CommunicationType] = None) -> List[Communication]:
        """Get all pending communications
        
        Args:
            communication_type: Optional filter by communication type
            
        Returns:
            List of pending Communication objects
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM communications WHERE status = ?"
            params = [CommunicationStatus.PENDING.value]
            
            if communication_type:
                query += " AND communication_type = ?"
                params.append(communication_type.value)
            
            query += " ORDER BY generated_at ASC"
            
            cursor.execute(query, params)
            return [Communication.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def update_communication_status(self, communication_id: str, status: CommunicationStatus,
                                   sent_at: Optional[datetime] = None,
                                   delivered_at: Optional[datetime] = None,
                                   response_received_at: Optional[datetime] = None,
                                   error_message: Optional[str] = None) -> bool:
        """Update communication status and timestamps
        
        Args:
            communication_id: The unique communication ID
            status: New status
            sent_at: Optional sent timestamp
            delivered_at: Optional delivered timestamp
            response_received_at: Optional response timestamp
            error_message: Optional error message
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically based on provided fields
                updates = ["status = ?", "last_attempt_at = ?"]
                params = [status.value, datetime.now().isoformat()]
                
                if sent_at:
                    updates.append("sent_at = ?")
                    params.append(sent_at.isoformat())
                
                if delivered_at:
                    updates.append("delivered_at = ?")
                    params.append(delivered_at.isoformat())
                
                if response_received_at:
                    updates.append("response_received_at = ?")
                    params.append(response_received_at.isoformat())
                
                if error_message:
                    updates.append("error_message = ?")
                    params.append(error_message)
                
                # Increment attempts
                updates.append("attempts = attempts + 1")
                
                params.append(communication_id)
                
                query = f"UPDATE communications SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            print(f"Error updating communication {communication_id}: {e}")
            return False
    
    def mark_communication_sent(self, communication_id: str, sent_at: Optional[datetime] = None) -> bool:
        """Mark a communication as sent
        
        Args:
            communication_id: The unique communication ID
            sent_at: Optional sent timestamp (defaults to now)
            
        Returns:
            True if update successful, False otherwise
        """
        return self.update_communication_status(
            communication_id, 
            CommunicationStatus.SENT, 
            sent_at=sent_at or datetime.now()
        )
    
    def mark_communication_failed(self, communication_id: str, error_message: str) -> bool:
        """Mark a communication as failed
        
        Args:
            communication_id: The unique communication ID
            error_message: Error message describing the failure
            
        Returns:
            True if update successful, False otherwise
        """
        return self.update_communication_status(
            communication_id, 
            CommunicationStatus.FAILED, 
            error_message=error_message
        )
    
    def get_unsent_listings(self, communication_type: CommunicationType = CommunicationType.EMAIL) -> List[Dict[str, Any]]:
        """Get listings that don't have any sent communications of the specified type
        
        Args:
            communication_type: Type of communication to check for
            
        Returns:
            List of listing dictionaries that haven't been contacted
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT l.* FROM listings l
                LEFT JOIN communications c ON l.id = c.listing_id 
                    AND c.communication_type = ? 
                    AND c.status IN (?, ?, ?)
                WHERE c.id IS NULL
                ORDER BY l.scraped_at DESC
            """, (
                communication_type.value,
                CommunicationStatus.SENT.value,
                CommunicationStatus.DELIVERED.value,
                CommunicationStatus.REPLIED.value
            ))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def has_successful_communication(self, listing_id: str, communication_type: CommunicationType) -> bool:
        """Check if a listing has any successful communications of the specified type
        
        Args:
            listing_id: The unique listing ID
            communication_type: Type of communication to check for
            
        Returns:
            True if there are successful communications, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM communications 
                WHERE listing_id = ? AND communication_type = ? 
                AND status IN (?, ?, ?) 
                LIMIT 1
            """, (
                listing_id,
                communication_type.value,
                CommunicationStatus.SENT.value,
                CommunicationStatus.DELIVERED.value,
                CommunicationStatus.REPLIED.value
            ))
            return cursor.fetchone() is not None
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get statistics about communications
        
        Returns:
            Dictionary with communication statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get total counts by status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM communications 
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Get total counts by type
            cursor.execute("""
                SELECT communication_type, COUNT(*) as count 
                FROM communications 
                GROUP BY communication_type
            """)
            type_counts = dict(cursor.fetchall())
            
            # Get recent activity (last 7 days)
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM communications 
                WHERE generated_at >= datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]
            
            return {
                'status_counts': status_counts,
                'type_counts': type_counts,
                'recent_count': recent_count,
                'total_communications': sum(status_counts.values())
            }
            
            

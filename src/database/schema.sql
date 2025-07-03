-- Listings table schema
-- Single table approach for both storage and deduplication

CREATE TABLE IF NOT EXISTS listings (
    -- Primary listing data
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    
    -- Pricing information
    price REAL,
    price_period TEXT,
    
    -- Date information
    start_date TEXT,  -- ISO format datetime
    end_date TEXT,    -- ISO format datetime
    
    -- Location
    neighborhood TEXT,
    
    -- Content
    brief_description TEXT,
    full_description TEXT,
    
    -- Contact information (if available after authentication)
    contact_name TEXT,
    contact_email TEXT,
    
    
    -- Metadata
    source_site TEXT NOT NULL,
    listing_type TEXT NOT NULL,
    scraped_at TEXT NOT NULL,  -- ISO format datetime
    
    -- Indexes for common queries
    UNIQUE(id)
);

-- Communications table for tracking all outreach activities
CREATE TABLE IF NOT EXISTS communications (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Foreign key to listings
    listing_id TEXT NOT NULL,
    
    -- Communication type and status
    communication_type TEXT NOT NULL, -- 'email', 'sms', 'call', 'whatsapp'
    status TEXT NOT NULL, -- 'pending', 'sent', 'failed', 'delivered', 'replied'
    
    -- Content
    subject TEXT,
    body TEXT,
    
    -- Recipient information
    to_email TEXT,
    to_phone TEXT,
    to_name TEXT,
    
    -- Sender information
    from_email TEXT,
    from_phone TEXT,
    from_name TEXT,
    
    -- Tracking timestamps
    generated_at TEXT NOT NULL,  -- ISO format datetime when content was generated
    sent_at TEXT,                -- ISO format datetime when actually sent
    delivered_at TEXT,           -- ISO format datetime when delivered (if supported)
    response_received_at TEXT,   -- ISO format datetime when response received
    
    -- Attempt tracking
    attempts INTEGER DEFAULT 0,
    last_attempt_at TEXT,
    
    -- Error handling
    error_message TEXT,
    
    -- Foreign key constraint
    FOREIGN KEY (listing_id) REFERENCES listings (id),
    
    -- Indexes for common queries
    UNIQUE(id)
);

-- Index for common filter queries
CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price);
CREATE INDEX IF NOT EXISTS idx_listings_dates ON listings(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_listings_neighborhood ON listings(neighborhood);
CREATE INDEX IF NOT EXISTS idx_listings_scraped_at ON listings(scraped_at);

-- Index for common communications queries
CREATE INDEX IF NOT EXISTS idx_communications_listing_id ON communications(listing_id);
CREATE INDEX IF NOT EXISTS idx_communications_status ON communications(status);
CREATE INDEX IF NOT EXISTS idx_communications_type ON communications(communication_type);
CREATE INDEX IF NOT EXISTS idx_communications_generated_at ON communications(generated_at);
CREATE INDEX IF NOT EXISTS idx_communications_sent_at ON communications(sent_at);

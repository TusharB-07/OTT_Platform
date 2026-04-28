-- OTT Streaming Platform MySQL Schema
-- Based on PRD v2.0

CREATE DATABASE IF NOT EXISTS ott_platform;
USE ott_platform;

-- 1. Users Table
CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    Email VARCHAR(255) UNIQUE NOT NULL,
    PasswordHash VARCHAR(255) NOT NULL, -- Added for Auth
    FirstName VARCHAR(100) NOT NULL,
    LastName VARCHAR(100) NOT NULL,
    DOB DATE NOT NULL,
    IsActive BOOLEAN DEFAULT TRUE -- For F7.13
);

-- 1.1 Multivalued Attribute: User_Phone
CREATE TABLE User_Phone (
    UserID INT NOT NULL,
    Phone VARCHAR(20) NOT NULL,
    PRIMARY KEY (UserID, Phone),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- 1.2 Derived Attribute: Age (VIEW)
CREATE VIEW v_user_age AS
SELECT 
    UserID, 
    Email, 
    FirstName, 
    LastName, 
    DOB, 
    TIMESTAMPDIFF(YEAR, DOB, CURDATE()) AS Age 
FROM Users;

-- 2. Content Table (Supertype for ISA Inheritance)
CREATE TABLE Content (
    ContentID INT AUTO_INCREMENT PRIMARY KEY,
    Title VARCHAR(255) NOT NULL,
    Duration INT COMMENT 'Total Duration in Minutes',
    Release_Year YEAR NOT NULL,
    Rating DECIMAL(3,1) DEFAULT 0.0 CHECK (Rating >= 0 AND Rating <= 10),
    Content_Type ENUM('Movie', 'Series') NOT NULL
);

-- 2.1 ISA: Movie Subtype
CREATE TABLE Movie (
    ContentID INT PRIMARY KEY,
    Movie_Name VARCHAR(255) NOT NULL,
    Director VARCHAR(150),
    Box_Office BIGINT,
    Movie_Cast TEXT,
    FOREIGN KEY (ContentID) REFERENCES Content(ContentID) ON DELETE CASCADE
);

-- 2.2 ISA: Series Subtype
CREATE TABLE Series (
    ContentID INT PRIMARY KEY,
    Seasons INT NOT NULL,
    FOREIGN KEY (ContentID) REFERENCES Content(ContentID) ON DELETE CASCADE
);

-- 2.3 Multivalued Attribute: Episodes (for Series)
CREATE TABLE Episodes (
    EpisodeID INT AUTO_INCREMENT PRIMARY KEY,
    ContentID INT NOT NULL,
    Episode_Title VARCHAR(255) NOT NULL,
    Season_No INT NOT NULL,
    Episode_No INT NOT NULL,
    Duration INT COMMENT 'Episode Duration in Minutes',
    FOREIGN KEY (ContentID) REFERENCES Series(ContentID) ON DELETE CASCADE
);

-- 2.4 Multivalued Attribute: Content_Language
CREATE TABLE Content_Language (
    ContentID INT NOT NULL,
    Language VARCHAR(50) NOT NULL,
    PRIMARY KEY (ContentID, Language),
    FOREIGN KEY (ContentID) REFERENCES Content(ContentID) ON DELETE CASCADE
);

-- 3. Genre Management
CREATE TABLE Genre (
    GenreID INT AUTO_INCREMENT PRIMARY KEY,
    Genre_Name VARCHAR(100) UNIQUE NOT NULL
);

-- 3.1 M:N Relationship: Content BELONGS_TO Genre
CREATE TABLE Content_Genre (
    ContentID INT NOT NULL,
    GenreID INT NOT NULL,
    PRIMARY KEY (ContentID, GenreID),
    FOREIGN KEY (ContentID) REFERENCES Content(ContentID) ON DELETE CASCADE,
    FOREIGN KEY (GenreID) REFERENCES Genre(GenreID) ON DELETE CASCADE
);

-- 4. Device Management
CREATE TABLE Device (
    DeviceID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    Device_Type VARCHAR(100) COMMENT 'e.g., Mobile, TV, Laptop',
    OS VARCHAR(100) COMMENT 'e.g., Android, iOS, Windows',
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- 5. Plans & Subscriptions
CREATE TABLE Plan (
    PlanID INT AUTO_INCREMENT PRIMARY KEY,
    Plan_Name VARCHAR(100) NOT NULL,
    Price DECIMAL(8,2) NOT NULL,
    Max_Screens INT NOT NULL,
    Duration_Days INT NOT NULL DEFAULT 30 -- Added for End_Date computation
);

-- 5.1 Weak Entity: Subscription
CREATE TABLE Subscription (
    Sub_ID INT NOT NULL,
    UserID INT NOT NULL,
    PlanID INT NOT NULL,
    Start_Date DATE NOT NULL,
    Status ENUM('Active', 'Expired', 'Cancelled') NOT NULL DEFAULT 'Active',
    PRIMARY KEY (UserID, Sub_ID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (PlanID) REFERENCES Plan(PlanID) ON DELETE CASCADE
);

-- 5.2 Derived Attribute: End_Date (VIEW)
CREATE VIEW v_subscription_details AS
SELECT 
    s.UserID, 
    s.Sub_ID, 
    s.PlanID, 
    p.Plan_Name, 
    s.Start_Date, 
    DATE_ADD(s.Start_Date, INTERVAL p.Duration_Days DAY) AS End_Date,
    s.Status
FROM Subscription s
JOIN Plan p ON s.PlanID = p.PlanID;

-- 6. Weak Entity: Payment
CREATE TABLE Payment (
    Trans_ID INT NOT NULL,
    UserID INT NOT NULL,
    Amount DECIMAL(10,2) NOT NULL,
    Pay_Date DATE NOT NULL,
    Method ENUM('Card', 'UPI', 'NetBanking', 'Wallet') NOT NULL,
    PRIMARY KEY (UserID, Trans_ID),
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE
);

-- 7. M:N Relationship: Watches
CREATE TABLE Watches (
    WatchID INT AUTO_INCREMENT PRIMARY KEY,
    UserID INT NOT NULL,
    ContentID INT NOT NULL,
    Watched_At TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    Watch_Duration INT COMMENT 'Minutes watched',
    FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    FOREIGN KEY (ContentID) REFERENCES Content(ContentID) ON DELETE CASCADE
);

-- 8. Aggregation: Review (Applied on Watches)
CREATE TABLE Review (
    ReviewID INT AUTO_INCREMENT PRIMARY KEY,
    WatchID INT UNIQUE NOT NULL, -- One review per watch session (Aggregation)
    Rev_Score DECIMAL(3,1) NOT NULL CHECK (Rev_Score >= 1 AND Rev_Score <= 10),
    Comment TEXT,
    Rev_Date DATE NOT NULL,
    FOREIGN KEY (WatchID) REFERENCES Watches(WatchID) ON DELETE CASCADE
);

-- 8.1 Derived Attribute: Average Content Rating (VIEW)
CREATE VIEW v_content_rating AS
SELECT 
    c.ContentID, 
    c.Title, 
    AVG(r.Rev_Score) AS Average_Rating 
FROM Content c
LEFT JOIN Watches w ON c.ContentID = w.ContentID
LEFT JOIN Review r ON w.WatchID = r.WatchID
GROUP BY c.ContentID;

-- 9. Trigger for Subscription Weak Entity (Auto-increment Sub_ID per User)
-- Note: MySQL doesn't natively support multiple auto-increment columns.
-- We'll handle this in the application logic or with a trigger if needed.

-- Sample Data for Demonstration
INSERT INTO Plan (Plan_Name, Price, Max_Screens, Duration_Days) VALUES
('Basic', 199.00, 1, 30),
('Standard', 499.00, 2, 30),
('Premium', 799.00, 4, 30);

INSERT INTO Genre (Genre_Name) VALUES
('Action'), ('Comedy'), ('Drama'), ('Sci-Fi'), ('Thriller');

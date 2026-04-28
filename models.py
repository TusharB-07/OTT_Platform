from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 1. Users Table
class User(db.Model):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Email = db.Column(db.String(255), unique=True, nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    FirstName = db.Column(db.String(100), nullable=False)
    LastName = db.Column(db.String(100), nullable=False)
    DOB = db.Column(db.Date, nullable=False)
    IsActive = db.Column(db.Boolean, default=True)

    phones = db.relationship('UserPhone', backref='user', cascade='all, delete-orphan')
    devices = db.relationship('Device', backref='user', cascade='all, delete-orphan')
    subscriptions = db.relationship('Subscription', backref='user', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', cascade='all, delete-orphan')
    watches = db.relationship('Watch', backref='user', cascade='all, delete-orphan')

# 1.1 Multivalued Attribute: User_Phone
class UserPhone(db.Model):
    __tablename__ = 'User_Phone'
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)
    Phone = db.Column(db.String(20), primary_key=True)

# 2. Content Table (Supertype for ISA Inheritance)
class Content(db.Model):
    __tablename__ = 'Content'
    ContentID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Title = db.Column(db.String(255), nullable=False)
    Duration = db.Column(db.Integer)
    Release_Year = db.Column(db.Integer, nullable=False)
    Rating = db.Column(db.Numeric(3, 1), default=0.0)
    Content_Type = db.Column(db.Enum('Movie', 'Series'), nullable=False)
    IMDb_Link = db.Column(db.String(500))
    Play_Link = db.Column(db.String(500))

    languages = db.relationship('ContentLanguage', backref='content', cascade='all, delete-orphan')
    genres = db.relationship('Genre', secondary='Content_Genre', backref='contents')

    __mapper_args__ = {
        'polymorphic_identity': 'content',
        'polymorphic_on': Content_Type
    }

# 2.1 ISA: Movie Subtype
class Movie(Content):
    __tablename__ = 'Movie'
    ContentID = db.Column(db.Integer, db.ForeignKey('Content.ContentID'), primary_key=True)
    Movie_Name = db.Column(db.String(255), nullable=False)
    Director = db.Column(db.String(150))
    Box_Office = db.Column(db.BigInteger)
    Movie_Cast = db.Column(db.Text)

    __mapper_args__ = {
        'polymorphic_identity': 'Movie',
    }

# 2.2 ISA: Series Subtype
class Series(Content):
    __tablename__ = 'Series'
    ContentID = db.Column(db.Integer, db.ForeignKey('Content.ContentID'), primary_key=True)
    Seasons = db.Column(db.Integer, nullable=False)

    episodes = db.relationship('Episode', backref='series', cascade='all, delete-orphan')

    __mapper_args__ = {
        'polymorphic_identity': 'Series',
    }

# 2.3 Multivalued Attribute: Episodes (for Series)
class Episode(db.Model):
    __tablename__ = 'Episodes'
    EpisodeID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ContentID = db.Column(db.Integer, db.ForeignKey('Series.ContentID'), nullable=False)
    Episode_Title = db.Column(db.String(255), nullable=False)
    Season_No = db.Column(db.Integer, nullable=False)
    Episode_No = db.Column(db.Integer, nullable=False)
    Duration = db.Column(db.Integer)

# 2.4 Multivalued Attribute: Content_Language
class ContentLanguage(db.Model):
    __tablename__ = 'Content_Language'
    ContentID = db.Column(db.Integer, db.ForeignKey('Content.ContentID'), primary_key=True)
    Language = db.Column(db.String(50), primary_key=True)

# 3. Genre Table
class Genre(db.Model):
    __tablename__ = 'Genre'
    GenreID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Genre_Name = db.Column(db.String(100), unique=True, nullable=False)

# 3.1 M:N Relationship Junction Table: Content_Genre
Content_Genre = db.Table('Content_Genre',
    db.Column('ContentID', db.Integer, db.ForeignKey('Content.ContentID'), primary_key=True),
    db.Column('GenreID', db.Integer, db.ForeignKey('Genre.GenreID'), primary_key=True)
)

# 4. Device Management
class Device(db.Model):
    __tablename__ = 'Device'
    DeviceID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    Device_Type = db.Column(db.String(100))
    OS = db.Column(db.String(100))

# 5. Plans
class Plan(db.Model):
    __tablename__ = 'Plan'
    PlanID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    Plan_Name = db.Column(db.String(100), nullable=False)
    Price = db.Column(db.Numeric(8, 2), nullable=False)
    Max_Screens = db.Column(db.Integer, nullable=False)
    Duration_Days = db.Column(db.Integer, default=30)

# 5.1 Weak Entity: Subscription
class Subscription(db.Model):
    __tablename__ = 'Subscription'
    Sub_ID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)
    PlanID = db.Column(db.Integer, db.ForeignKey('Plan.PlanID'), nullable=False)
    Start_Date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    Status = db.Column(db.Enum('Active', 'Expired', 'Cancelled'), default='Active')

# 6. Weak Entity: Payment
class Payment(db.Model):
    __tablename__ = 'Payment'
    Trans_ID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), primary_key=True)
    Amount = db.Column(db.Numeric(10, 2), nullable=False)
    Pay_Date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    Method = db.Column(db.Enum('Card', 'UPI', 'NetBanking', 'Wallet'), nullable=False)

# 7. M:N Relationship: Watches
class Watch(db.Model):
    __tablename__ = 'Watches'
    WatchID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    ContentID = db.Column(db.Integer, db.ForeignKey('Content.ContentID'), nullable=False)
    Watched_At = db.Column(db.DateTime, default=datetime.utcnow)
    Watch_Duration = db.Column(db.Integer)

    content = db.relationship('Content', backref='watches')
    review = db.relationship('Review', backref='watch', uselist=False, cascade='all, delete-orphan')

# 8. Aggregation: Review (Applied on Watches)
class Review(db.Model):
    __tablename__ = 'Review'
    ReviewID = db.Column(db.Integer, primary_key=True, autoincrement=True)
    WatchID = db.Column(db.Integer, db.ForeignKey('Watches.WatchID'), unique=True, nullable=False)
    Rev_Score = db.Column(db.Numeric(3, 1), nullable=False)
    Comment = db.Column(db.Text)
    Rev_Date = db.Column(db.Date, nullable=False, default=datetime.utcnow)

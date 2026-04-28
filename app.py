from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import db, User, Content, Movie, Series, Genre, Plan, Subscription, Payment, Watch, Review, Episode, Device, ContentLanguage
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps

import os

app = Flask(__name__)
# Using pymysql as a pure-python driver for Python 3.14 compatibility
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:tusharroot@localhost/ott_platform'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'

CORS(app)
db.init_app(app)

# Helper for thumbnails
def get_thumbnail(title):
    safe_title = title.replace(':', '-')
    extensions = ['.jpeg', '.jpg', '.png', '.webp']
    for ext in extensions:
        if os.path.exists(os.path.join('static', 'thumbnails', f'{safe_title}{ext}')):
            return f'/static/thumbnails/{safe_title}{ext}'
    return None

# Helper for JWT Auth
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# --- AUTH ROUTES ---

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('Email', 'Password', 'FirstName', 'LastName', 'DOB')):
        return jsonify({'message': 'Missing required fields!'}), 400
    
    if User.query.filter_by(Email=data['Email']).first():
        return jsonify({'message': 'Email already exists!'}), 400

    try:
        hashed_password = generate_password_hash(data['Password'])
        new_user = User(
            Email=data['Email'],
            PasswordHash=hashed_password,
            FirstName=data['FirstName'],
            LastName=data['LastName'],
            DOB=datetime.datetime.strptime(data['DOB'], '%Y-%m-%d').date()
        )
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Registration failed!', 'error': str(e)}), 500
        
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'Email' not in data or 'Password' not in data:
        return jsonify({'message': 'Email and Password are required!'}), 400
        
    user = User.query.filter_by(Email=data['Email']).first()
    if user and check_password_hash(user.PasswordHash, data['Password']):
        token = jwt.encode({
            'user_id': user.UserID,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        return jsonify({
            'token': token, 
            'user_id': user.UserID,
            'first_name': user.FirstName
        })
    return jsonify({'message': 'Invalid credentials!'}), 401

# --- CONTENT ROUTES ---

@app.route('/api/content', methods=['GET'])
def get_content():
    content_list = Content.query.all()
    output = []
    for c in content_list:
        content_data = {
            'ContentID': c.ContentID,
            'Title': c.Title,
            'Rating': float(c.Rating),
            'Content_Type': c.Content_Type,
            'Release_Year': c.Release_Year,
            'Thumbnail': get_thumbnail(c.Title)
        }
        output.append(content_data)
    return jsonify({'content': output})

@app.route('/api/content/<int:id>', methods=['GET'])
def get_content_detail(id):
    c = Content.query.get_or_404(id)
    
    # Fetch reviews via Watches aggregation
    reviews = db.session.query(Review).join(Watch).filter(Watch.ContentID == id).all()
    
    content_data = {
        'ContentID': c.ContentID,
        'Title': c.Title,
        'Duration': c.Duration,
        'Release_Year': c.Release_Year,
        'Rating': float(c.Rating),
        'Content_Type': c.Content_Type,
        'Thumbnail': get_thumbnail(c.Title),
        'IMDb_Link': c.IMDb_Link,
        'Play_Link': c.Play_Link,
        'Genres': [g.Genre_Name for g in c.genres],
        'Languages': [l.Language for l in c.languages],
        'Reviews': [{
            'User': f"{r.watch.user.FirstName} {r.watch.user.LastName}",
            'Score': float(r.Rev_Score),
            'Comment': r.Comment,
            'Date': r.Rev_Date.strftime('%Y-%m-%d')
        } for r in reviews]
    }
    
    if c.Content_Type == 'Movie':
        movie = Movie.query.get(id)
        content_data.update({
            'Director': movie.Director,
            'Box_Office': movie.Box_Office,
            'Cast': movie.Movie_Cast
        })
    elif c.Content_Type == 'Series':
        series = Series.query.get(id)
        content_data.update({
            'Seasons': series.Seasons,
            'Episodes': [{
                'EpisodeID': e.EpisodeID,
                'Title': e.Episode_Title,
                'Season': e.Season_No,
                'Number': e.Episode_No,
                'Duration': e.Duration
            } for e in series.episodes]
        })
    
    return jsonify(content_data)

# --- USER & DEVICE ROUTES ---

@app.route('/api/user/profile', methods=['GET'])
@token_required
def get_user_profile(current_user):
    # Fetch watch history with content titles
    watches = Watch.query.filter_by(UserID=current_user.UserID).order_by(Watch.Watched_At.desc()).all()
    
    # Fetch reviews
    reviews = db.session.query(Review).join(Watch).filter(Watch.UserID == current_user.UserID).all()

    # Fetch active subscription
    active_sub = Subscription.query.filter_by(UserID=current_user.UserID, Status='Active').first()
    sub_data = None
    if active_sub:
        plan = Plan.query.get(active_sub.PlanID)
        sub_data = {
            'PlanName': plan.Plan_Name,
            'Status': active_sub.Status,
            'StartDate': active_sub.Start_Date.strftime('%Y-%m-%d'),
            'MaxScreens': plan.Max_Screens
        }

    # Continue Watching (Most recent unique items where duration < content duration)
    # Using a dictionary to keep only the latest session per content
    continue_watching = {}
    for w in watches:
        if w.ContentID not in continue_watching:
            if w.Watch_Duration < w.content.Duration:
                continue_watching[w.ContentID] = {
                    'ContentID': w.ContentID,
                    'Title': w.content.Title,
                    'Progress': w.Watch_Duration,
                    'Total': w.content.Duration,
                    'Percent': round((w.Watch_Duration / w.content.Duration) * 100) if w.content.Duration > 0 else 0,
                    'Thumbnail': get_thumbnail(w.content.Title)
                }
    
    return jsonify({
        'FirstName': current_user.FirstName,
        'LastName': current_user.LastName,
        'Email': current_user.Email,
        'DOB': current_user.DOB.strftime('%Y-%m-%d'),
        'Subscription': sub_data,
        'ContinueWatching': list(continue_watching.values())[:4], # Limit to top 4
        'WatchHistory': [{
            'Title': w.content.Title,
            'Date': w.Watched_At.strftime('%Y-%m-%d %H:%M'),
            'Duration': w.Watch_Duration
        } for w in watches],
        'ReviewHistory': [{
            'Title': r.watch.content.Title,
            'Score': float(r.Rev_Score),
            'Comment': r.Comment,
            'Date': r.Rev_Date.strftime('%Y-%m-%d')
        } for r in reviews]
    })

@app.route('/api/users/<int:id>/devices', methods=['GET', 'POST'])
@token_required
def manage_devices(current_user, id):
    if current_user.UserID != id:
        return jsonify({'message': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        devices = Device.query.filter_by(UserID=id).all()
        return jsonify([{'DeviceID': d.DeviceID, 'Type': d.Device_Type, 'OS': d.OS} for d in devices])
    
    data = request.get_json()
    # Check screen limit
    active_sub = Subscription.query.filter_by(UserID=id, Status='Active').first()
    if not active_sub:
        return jsonify({'message': 'No active subscription found!'}), 403
    
    plan = Plan.query.get(active_sub.PlanID)
    current_devices_count = Device.query.filter_by(UserID=id).count()
    
    if current_devices_count >= plan.Max_Screens:
        return jsonify({'message': f'Device limit reached for your {plan.Plan_Name} plan!'}), 403
        
    new_device = Device(UserID=id, Device_Type=data['Type'], OS=data['OS'])
    db.session.add(new_device)
    db.session.commit()
    return jsonify({'message': 'Device registered successfully!'}), 201

# --- SUBSCRIPTION & PAYMENT ROUTES ---

@app.route('/api/plans', methods=['GET'])
def list_plans():
    plans = Plan.query.all()
    return jsonify([{'PlanID': p.PlanID, 'Name': p.Plan_Name, 'Price': float(p.Price), 'Screens': p.Max_Screens} for p in plans])

@app.route('/api/subscriptions', methods=['POST'])
@token_required
def create_subscription(current_user):
    data = request.get_json()
    # In a real app, integrate payment gateway here
    # For this project, we assume payment success
    
    # 1. Create Payment record
    trans_id = Payment.query.filter_by(UserID=current_user.UserID).count() + 1
    new_payment = Payment(
        Trans_ID=trans_id,
        UserID=current_user.UserID,
        Amount=data['Amount'],
        Method=data['Method'],
        Pay_Date=datetime.date.today()
    )
    
    # 2. Create Subscription record
    sub_id = Subscription.query.filter_by(UserID=current_user.UserID).count() + 1
    new_sub = Subscription(
        Sub_ID=sub_id,
        UserID=current_user.UserID,
        PlanID=data['PlanID'],
        Start_Date=datetime.date.today(),
        Status='Active'
    )
    
    db.session.add(new_payment)
    db.session.add(new_sub)
    db.session.commit()
    return jsonify({'message': 'Subscribed successfully!'}), 201

# --- WATCH & REVIEW ROUTES ---

@app.route('/api/watches', methods=['POST'])
@token_required
def start_watch(current_user):
    data = request.get_json()
    new_watch = Watch(
        UserID=current_user.UserID,
        ContentID=data['ContentID'],
        Watch_Duration=0
    )
    db.session.add(new_watch)
    db.session.commit()
    return jsonify({'message': 'Watch session started', 'WatchID': new_watch.WatchID})

@app.route('/api/reviews', methods=['POST'])
@token_required
def submit_review(current_user):
    data = request.get_json()
    
    # 1. Check if watch session exists and belongs to user
    watch = Watch.query.filter_by(WatchID=data['WatchID'], UserID=current_user.UserID).first()
    if not watch:
        return jsonify({'message': 'Invalid watch session!'}), 403
    
    # 2. Check if already reviewed (Aggregation 1:1 constraint)
    existing_review = Review.query.filter_by(WatchID=data['WatchID']).first()
    if existing_review:
        return jsonify({'message': 'This watch session has already been reviewed!'}), 400
    
    try:
        new_review = Review(
            WatchID=data['WatchID'],
            Rev_Score=data['Score'],
            Comment=data['Comment'],
            Rev_Date=datetime.date.today()
        )
        db.session.add(new_review)
        db.session.commit()
        
        # 3. Recalculate Content Average Rating (Trigger-like behavior)
        avg_rating = db.session.query(db.func.avg(Review.Rev_Score))\
            .join(Watch)\
            .filter(Watch.ContentID == watch.ContentID)\
            .scalar()
        
        content = Content.query.get(watch.ContentID)
        content.Rating = round(float(avg_rating), 1)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to submit review', 'error': str(e)}), 500
        
    return jsonify({'message': 'Review submitted and rating updated!'}), 201

# --- ADMIN ANALYTICS ---

@app.route('/api/admin/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    # Skip admin check for demo purposes
    total_users = User.query.count()
    total_revenue = db.session.query(db.func.sum(Payment.Amount)).scalar() or 0
    active_subs = Subscription.query.filter_by(Status='Active').count()
    
    # Top 5 most watched (M:N join)
    top_watched = db.session.query(Content.Title, db.func.count(Watch.WatchID).label('count'))\
        .join(Watch)\
        .group_by(Content.ContentID)\
        .order_by(db.text('count DESC'))\
        .limit(5).all()
        
    return jsonify({
        'total_users': total_users,
        'total_revenue': float(total_revenue),
        'active_subscriptions': active_subs,
        'top_content': [{'Title': t[0], 'Watches': t[1]} for t in top_watched]
    })

# --- WEB ROUTES ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/subscription')
def subscription_page():
    return render_template('subscription.html')

@app.route('/content/<int:id>')
def content_detail_page(id):
    return render_template('content_detail.html')

if __name__ == '__main__':
    with app.app_context():
        # db.create_all() # We'll use schema.sql for initial setup
        pass
    app.run(debug=True)

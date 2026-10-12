import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'jonotar_khata_secret_key_123'

# Supabase PostgreSQL Pooler Configuration (Port 5432)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres.bdxyvdbstcxzxh:JunayedDb2026@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    thana = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved
    true_votes = db.Column(db.Integer, default=0)
    false_votes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

# Create Tables & Initial Notice
with app.app_context():
    db.create_all()
    if not Notice.query.first():
        default_notice = Notice(content="জনতার খাতা - কিশোরগঞ্জ প্ল্যাটফর্মে আপনাকে স্বাগতম। দুর্নীতি ও অনিয়মের বিরুদ্ধে সরব হোন।")
        db.session.add(default_notice)
        db.session.commit()

# Helper Functions
def convert_to_bengali_digits(text):
    if text is None:
        return ""
    english_to_bengali = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    return str(text).translate(english_to_bengali)

def format_bengali_datetime(dt):
    if not dt:
        return ""
    bd_time = dt + timedelta(hours=6)
    
    months = {
        1: 'জানুয়ারি', 2: 'ফেব্রুয়ারি', 3: 'মার্চ', 4: 'এপ্রিল',
        5: 'মে', 6: 'জুন', 7: 'জুলাই', 8: 'আগস্ট',
        9: 'সেপ্টেম্বর', 10: 'অক্টোবর', 11: 'নভেম্বর', 12: 'ডিসেম্বর'
    }
    
    day = convert_to_bengali_digits(bd_time.day)
    month = months.get(bd_time.month, '')
    year = convert_to_bengali_digits(bd_time.year)
    
    hour_24 = bd_time.hour
    minute = bd_time.minute
    
    ampm = "রাত" if (hour_24 >= 20 or hour_24 < 4) else ("সকাল" if (hour_24 >= 4 and hour_24 < 12) else ("দুপুর" if (hour_24 >= 12 and hour_24 < 16) else ("বিকাল" if (hour_24 >= 16 and hour_24 < 18) else "সন্ধ্যা")))
    
    hour_12 = hour_24 % 12
    if hour_12 == 0:
        hour_12 = 12
        
    hour_bn = convert_to_bengali_digits(hour_12)
    minute_bn = convert_to_bengali_digits(f"{minute:02d}")
    
    return f"{day}ই {month}, {year} • {ampm} {hour_bn}:{minute_bn}"

# Routes
@app.route('/')
def index():
    selected_thana = request.args.get('thana')
    notice = Notice.query.first()
    
    total_count = Post.query.filter((Post.status == 'approved') | (Post.status == None)).count()
    
    thanas = [
        "কিশোরগঞ্জ সদর", "হোসেনপুর", "পাকুন্দিয়া", "কটিয়াদী", 
        "করিমগঞ্জ", "তাড়াইল", "বাজিতপুর", "কুলিয়ারচর", 
        "ভৈরব", "নিকলী", "অষ্টগ্রাম", "ইটনা", "মিঠামইন"
    ]
    
    thana_counts = {t: Post.query.filter((Post.status == 'approved') | (Post.status == None), Post.thana == t).count() for t in thanas}

    if selected_thana and selected_thana != 'all':
        posts_query = Post.query.filter((Post.status == 'approved') | (Post.status == None), Post.thana == selected_thana).order_by(Post.id.desc()).all()
    else:
        posts_query = Post.query.filter((Post.status == 'approved') | (Post.status == None)).order_by(Post.id.desc()).all()

    posts = []
    total_posts_len = len(posts_query)
    for idx, p in enumerate(posts_query):
        posts.append({
            'raw_id': p.id,
            'index': convert_to_bengali_digits(total_posts_len - idx),
            'id': convert_to_bengali_digits(p.id),
            'category': p.category,
            'thana': p.thana,
            'content': p.content,
            'true_votes': convert_to_bengali_digits(p.true_votes),
            'false_votes': convert_to_bengali_digits(p.false_votes),
            'created_at_bn': format_bengali_datetime(p.created_at)
        })

    all_approved = Post.query.filter((Post.status == 'approved') | (Post.status == None)).all()
    all_true_votes = sum(p.true_votes for p in all_approved)
    all_false_votes = sum(p.false_votes for p in all_approved)
    total_all_votes = all_true_votes + all_false_votes

    if total_all_votes > 0:
        rating_all_val = round((all_true_votes / total_all_votes) * 100

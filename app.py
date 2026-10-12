import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'jonotar_khata_secret_key_123'

# Supabase Direct Connection Database Configuration (Exact URI)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://postgres:JunayedDb2026@db.bdxyvdbsyelpdstczaxh.supabase.co:5432/postgres'
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
        rating_all_val = round((all_true_votes / total_all_votes) * 100)
        rating_all = f"{convert_to_bengali_digits(rating_all_val)}% সত্য"
    else:
        rating_all = "১০০% সত্য"

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_posts = Post.query.filter((Post.status == 'approved') | (Post.status == None), Post.created_at >= thirty_days_ago).all()
    monthly_count = len(monthly_posts)

    m_true_votes = sum(p.true_votes for p in monthly_posts)
    m_false_votes = sum(p.false_votes for p in monthly_posts)
    total_m_votes = m_true_votes + m_false_votes

    if total_m_votes > 0:
        rating_monthly_val = round((m_true_votes / total_m_votes) * 100)
        rating_monthly = f"{convert_to_bengali_digits(rating_monthly_val)}% সত্য"
    else:
        rating_monthly = "১০০% সত্য"

    cat_counts = {}
    for p in monthly_posts:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1

    top_sector_monthly = max(cat_counts, key=cat_counts.get) if cat_counts else "তথ্য নেই"

    all_cat_counts = {}
    for p in all_approved:
        all_cat_counts[p.category] = all_cat_counts.get(p.category, 0) + 1
    top_sector_all = max(all_cat_counts, key=all_cat_counts.get) if all_cat_counts else "তথ্য নেই"

    dept_analytics = []
    if monthly_count > 0:
        for cat, cnt in cat_counts.items():
            pct = round((cnt / monthly_count) * 100)
            dept_analytics.append({
                'name': cat,
                'count': convert_to_bengali_digits(cnt),
                'percentage': convert_to_bengali_digits(pct),
                'raw_percentage': pct
            })

    return render_template('index.html', 
                           posts=posts, 
                           total_count=convert_to_bengali_digits(total_count),
                           thanas=thanas,
                           thana_counts={t: convert_to_bengali_digits(c) for t, c in thana_counts.items()},
                           selected_thana=selected_thana,
                           monthly_count=convert_to_bengali_digits(monthly_count),
                           top_sector_monthly=top_sector_monthly,
                           top_sector_all=top_sector_all,
                           dept_analytics=dept_analytics,
                           notice=notice,
                           rating_all=rating_all,
                           rating_monthly=rating_monthly)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        category = request.form.get('category')
        thana = request.form.get('thana')
        content = request.form.get('content')
        
        if category and thana and content:
            new_post = Post(category=category, thana=thana, content=content, status='pending')
            db.session.add(new_post)
            db.session.commit()
            
            flash('আপনার রিপোর্টটি সফলভাবে জমা হয়েছে! অনুমোদনের জন্য অ্যাডমিনের কাছে পাঠানো হয়েছে।')
            return redirect(url_for('submit'))
            
    return render_template('submit.html')

@app.route('/vote/<int:post_id>/<vote_type>')
def vote(post_id, vote_type):
    post = Post.query.get_or_404(post_id)
    if vote_type == 'true':
        post.true_votes += 1
    elif vote_type == 'false':
        post.false_votes += 1
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    notice = Notice.query.first()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin.html', error="ভুল ইউজারনেম বা পাসওয়ার্ড!", notice=notice)

    if not session.get('admin_logged_in'):
        return render_template('admin.html', show_login=True, notice=notice)
        
    all_posts = Post.query.order_by(Post.id.desc()).all()
    
    pending_posts = [p for p in all_posts if p.status == 'pending']
    approved_posts = [p for p in all_posts if p.status == 'approved' or p.status == None or p.status == '']

    return render_template('admin.html', 
                           approved_posts=approved_posts, 
                           pending_posts=pending_posts, 
                           notice=notice, 
                           to_bn=convert_to_bengali_digits)

@app.route('/admin/update-notice', methods=['POST'])
def update_notice():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    new_text = request.form.get('notice_text')
    notice = Notice.query.first()
    if not notice:
        notice = Notice(content=new_text)
        db.session.add(notice)
    else:
        notice.content = new_text
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/action/<int:post_id>/<action>')
def admin_action(post_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
        
    post = Post.query.get_or_404(post_id)
    if action == 'approve':
        post.status = 'approved'
    elif action == 'delete':
        db.session.delete(post)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

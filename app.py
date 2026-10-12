import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# SQLite Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

# Post Model
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    thana = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved
    true_votes = db.Column(db.Integer, default=0)
    false_votes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Notice Model (চলমান নোটিশের জন্য)
class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()
    # ডিফল্ট নোটিশ না থাকলে একটি তৈরি করে নেওয়া
    if not Notice.query.first():
        default_notice = Notice(content="জনতার খাতা - কিশোরগঞ্জ প্ল্যাটফর্মে আপনাকে স্বাগতম। দুর্নীতি ও অনিয়মের বিরুদ্ধে সরوب হোন।")
        db.session.add(default_notice)
        db.session.commit()

# বাংলা সংখ্যা ও সময় কনভার্টার হেল্পার
def convert_to_bengali_digits(text):
    if not text:
        return ""
    english_to_bengali = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    return str(text).translate(english_to_bengali)

def format_bengali_datetime(dt):
    if not dt:
        return ""
    # বাংলাদেশ সময় (UTC + 6 hours)
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

@app.route('/')
def index():
    selected_thana = request.args.get('thana')
    
    # নোটিশ ফেচ করা
    notice = Notice.query.first()
    
    # টোটাল কাউন্ট
    total_count = Post.query.filter_by(status='approved').count()
    
    # থানা লেজার লিস্ট
    thanas = [
        "কিশোরগঞ্জ সদর", "হোসেনপুর", "پاکুন্দিয়া", "কটিয়াদী", 
        "করিমগঞ্জ", "তাড়াইল", "বাজিতপুর", "কুলিয়ারচর", 
        "ভৈরব", "নিকላይ (নিকলী)", "অষ্টগ্রাম", "ইটনা", "মিঠামইন"
    ]
    
    thana_counts = {}
    for t in thanas:
        c = Post.query.filter_by(status='approved', thana=t).count()
        thana_counts[t] = c

    if selected_thana and selected_thana != 'all':
        posts_query = Post.query.filter_by(status='approved', thana=selected_thana).order_by(Post.id.desc()).all()
    else:
        posts_query = Post.query.filter_by(status='approved').order_by(Post.id.desc()).all()

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

    # মাসিক হিসাব (গত ৩০ দিন)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    monthly_posts = Post.query.filter(Post.status == 'approved', Post.created_at >= thirty_days_ago).all()
    monthly_count = len(monthly_posts)

    # শীর্ষ দপ্তর ও থানা হিসাব বের করা
    cat_counts = {}
    thana_monthly_counts = {}
    for p in monthly_posts:
        cat_counts[p.category] = cat_counts.get(p.category, 0) + 1
        thana_monthly_counts[p.thana] = thana_monthly_counts.get(p.thana, 0) + 1

    top_sector_monthly = max(cat_counts, key=cat_counts.get) if cat_counts else "তথ্য নেই"
    top_thana_monthly = max(thana_monthly_counts, key=thana_monthly_counts.get) if thana_monthly_counts else "কিশোরগঞ্জ সদর"

    all_posts = Post.query.filter_by(status='approved').all()
    all_cat_counts = {}
    for p in all_posts:
        all_cat_counts[p.category] = all_cat_counts.get(p.category, 0) + 1
    top_sector_all = max(all_cat_counts, key=all_cat_counts.get) if all_cat_counts else "তথ্য নেই"

    # প্রোগ্রেস বার ডেটা তৈরি
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
                           selected_thana_monthly=top_thana_monthly,
                           dept_analytics=dept_analytics,
                           notice=notice)

@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == 'POST':
        category = request.form.get('category')
        thana = request.form.get('thana')
        content = request.form.get('content')
        
        new_post = Post(category=category, thana=thana, content=content, status='pending')
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))
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
        if username == 'admin' and password == 'admin123': # আপনার ইউজারনেম ও পাসওয়ার্ড
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('admin.html', error="ভুল ইউজারনেম বা পাসওয়ার্ড!", notice=notice)
            
    posts = Post.query.order_by(Post.id.desc()).all()
    return render_template('admin.html', posts=posts, notice=notice)

# অ্যাডমিন প্যানেল থেকে নোটিশ আপডেট করার রুট
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

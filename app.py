from flask import Flask, render_template, request, redirect, url_for, session, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'jonotar_khata_kishorganj_super_secret_key'
db = SQLAlchemy(app)

KISHORGANJ_THANAS = [
    "কিশোরগঞ্জ সদর", "ভৈরব", "কুলিয়ারচর", "বাজিতপুর", 
    "হোসেনপুর", "পাকুন্দিয়া", "কটিয়াদী", "করিমগঞ্জ", 
    "তাড়াইল", "ইটনা", "মিঠামইন", "অষ্টগ্রাম", "নিকলী"
]

DEPARTMENTS = [
    "ভূমি অফিস / এসিল্যান্ড অফিস",
    "থানা / পুলিশ সার্ভিস",
    "হাসপাতাল / স্বাস্থ্য কেন্দ্র",
    "সাব-রেজিস্ট্রি অফিস",
    "পাসপোর্ট অফিস",
    "বিআরটিএ (BRTA)",
    "পল্লী বিদ্যুৎ / বিদ্যুৎ অফিস",
    "ইউনিয়ন পরিষদ / পৌরসভা",
    "শিক্ষা অফিস / স্কুল-কলেজ",
    "অন্যান্য"
]

def get_bd_now():
    # UTC এর সাথে ৬ ঘণ্টা যোগ করে সরাসরি বাংলাদেশের সময় (UTC+6) বের করা
    return datetime.utcnow() + timedelta(hours=6)

def to_bn(num):
    num_str = str(num)
    eng_to_bn = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
    return num_str.translate(eng_to_bn)

def to_eng(num_str):
    bn_to_eng = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
    return str(num_str).translate(bn_to_eng)

def format_bn_datetime(dt):
    if not dt:
        return ""
    months = ["জানুয়ারি", "ফেব্রুয়ারি", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টেম্বর", "অক্টোবর", "নভেম্বর", "ডিসেম্বর"]
    day = to_bn(dt.day)
    month = months[dt.month - 1]
    year = to_bn(dt.year)
    hour = dt.strftime("%I")
    minute = dt.strftime("%M")
    am_pm = "পূর্বাহ্ন" if dt.strftime("%p") == "AM" else "অপরাহ্ন"
    time_str = f"{to_bn(int(hour))}:{to_bn(minute)} {am_pm}"
    return f"{day} {month} {year}, {time_str}"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    thana = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=get_bd_now)
    true_votes = db.Column(db.Integer, default=0)
    false_votes = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    selected_thana = request.args.get('thana')
    one_month_ago = get_bd_now() - timedelta(days=30)
    
    all_approved = Post.query.filter_by(status='approved').all()
    monthly_approved = Post.query.filter(Post.status == 'approved', Post.created_at >= one_month_ago).all()
    
    query = Post.query.filter(Post.status == 'approved')
    if selected_thana and selected_thana != 'all':
        recent_posts = query.filter_by(thana=selected_thana).order_by(Post.created_at.desc()).all()
    else:
        recent_posts = query.order_by(Post.created_at.desc()).all()
        
    total_count = len(all_approved)
    monthly_count = len(monthly_approved)

    thana_counts = {}
    for t in KISHORGANJ_THANAS:
        count = Post.query.filter_by(status='approved', thana=t).count()
        thana_counts[t] = to_bn(count)

    all_dept_stats = {}
    for post in all_approved:
        all_dept_stats[post.category] = all_dept_stats.get(post.category, 0) + 1
    
    top_sector_all = "তথ্য নেই"
    if all_dept_stats:
        top_sector_all = max(all_dept_stats, key=all_dept_stats.get)

    monthly_dept_stats = {}
    for post in monthly_approved:
        monthly_dept_stats[post.category] = monthly_dept_stats.get(post.category, 0) + 1
    
    dept_analytics = []
    top_sector_monthly = "তথ্য নেই"
    if monthly_count > 0:
        for dept, count in monthly_dept_stats.items():
            percentage = round((count / monthly_count) * 100, 1)
            dept_analytics.append({
                'name': dept,
                'count': to_bn(count),
                'percentage': to_bn(percentage),
                'raw_percentage': percentage
            })
        dept_analytics = sorted(dept_analytics, key=lambda x: x['raw_percentage'], reverse=True)
        top_sector_monthly = dept_analytics[0]['name']

    posts_data = []
    for idx, p in enumerate(recent_posts, start=1):
        posts_data.append({
            'id': to_bn(p.id),
            'raw_id': p.id,
            'index': to_bn(idx),
            'category': p.category,
            'thana': p.thana,
            'content': p.content,
            'created_at_bn': format_bn_datetime(p.created_at),
            'true_votes': to_bn(p.true_votes),
            'false_votes': to_bn(p.false_votes)
        })

    return render_template(
        'index.html', 
        posts=posts_data, 
        thanas=KISHORGANJ_THANAS, 
        thana_counts=thana_counts,
        total_count=to_bn(total_count), 
        monthly_count=to_bn(monthly_count),
        selected_thana=selected_thana,
        dept_analytics=dept_analytics,
        top_sector_all=top_sector_all,
        top_sector_monthly=top_sector_monthly
    )

@app.route('/submit', methods=['GET', 'POST'])
def submit_post():
    if request.method == 'POST':
        category = request.form.get('category')
        thana = request.form.get('thana')
        content = request.form.get('content', '').strip()
        
        if not category or not thana or not content:
            flash("সবগুলো প্রয়োজনীয় তথ্য সঠিকভাবে লিখুন।", "danger")
            return redirect(url_for('submit_post'))

        new_post = Post(
            category=category, 
            thana=thana, 
            content=content, 
            status='pending',
            created_at=get_bd_now()
        )
        db.session.add(new_post)
        db.session.commit()
        
        flash("আপনার রিপোর্টটি সফলভাবে জমা হয়েছে! একজন এডমিন রিভিউ করে প্রকাশ করবেন।", "success")
        return redirect(url_for('submit_post'))
        
    return render_template('submit.html', thanas=KISHORGANJ_THANAS, departments=DEPARTMENTS)

@app.route('/vote/<int:post_id>/<vote_type>')
def vote(post_id, vote_type):
    voted_posts = request.cookies.get('voted_posts', '')
    voted_list = voted_posts.split(',') if voted_posts else []

    target_url = url_for('index') + '#recent-reports'

    if str(post_id) in voted_list:
        return redirect(target_url)

    post = Post.query.get_or_404(post_id)
    if vote_type == 'true':
        post.true_votes += 1
    elif vote_type == 'false':
        post.false_votes += 1
    db.session.commit()

    voted_list.append(str(post_id))
    resp = make_response(redirect(target_url))
    resp.set_cookie('voted_posts', ','.join(voted_list), max_age=60*60*24*365)
    return resp

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'kishorgonj123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return "ভুল পাসওয়ার্ড! <a href='/admin'>আবার চেষ্টা করুন</a>"
            
    if session.get('admin_logged_in'):
        tab = request.args.get('tab', 'approve')
        search_id = request.args.get('search_id', '').strip()
        
        pending_posts = Post.query.filter_by(status='pending').order_by(Post.created_at.desc()).all()
        
        approved_query = Post.query.filter_by(status='approved')
        
        if search_id:
            clean_id = search_id.replace('#', '').strip()
            clean_id_eng = to_eng(clean_id)
            if clean_id_eng.isdigit():
                approved_query = approved_query.filter_by(id=int(clean_id_eng))

        approved_posts = approved_query.order_by(Post.created_at.desc()).all()
        
        return render_template(
            'admin.html', 
            pending_posts=pending_posts, 
            approved_posts=approved_posts,
            tab=tab,
            search_id=search_id,
            to_bn=to_bn
        )
    
    return '''
        <body style="font-family: Arial; margin: 80px; background: #f5f4f0;">
        <div style="max-width: 400px; margin: 0 auto; background: #fff; padding: 30px; border: 1px solid #000;">
            <h2>অ্যাডমিন প্যানেল লগইন</h2>
            <form method="post">
                <label>ইউজারনেম:</label><br>
                <input type="text" name="username" style="width: 100%; padding: 8px; margin: 8px 0;"><br>
                <label>পাসওয়ার্ড:</label><br>
                <input type="password" name="password" style="width: 100%; padding: 8px; margin: 8px 0;"><br><br>
                <button type="submit" style="width: 100%; background: #000; color: #fff; padding: 10px; font-weight: bold;">লগইন করুন</button>
            </form>
        </div>
        </body>
    '''

@app.route('/admin/action/<int:post_id>/<action>')
def admin_action(post_id, action):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))
    
    post = Post.query.get_or_404(post_id)
    tab = 'approve'
    if action == 'approve':
        post.status = 'approved'
        tab = 'approve'
    elif action == 'delete':
        db.session.delete(post)
        tab = 'delete'
    db.session.commit()
    return redirect(url_for('admin', tab=tab))

if __name__ == '__main__':
    app.run(debug=True)
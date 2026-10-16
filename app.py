from datetime import datetime, timedelta
import os
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'jonotar_khata_admin_settings_2026'

database_url = (
    os.environ.get('DATABASE_URL')
    or 'postgresql://postgres.bdxyvdbsyelpdstczaxh:JunayedDb2026@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres?sslmode=require'
)

if database_url and database_url.startswith('postgres://'):
  database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)


@app.teardown_appcontext
def shutdown_session(exception=None):
  db.session.remove()


class Post(db.Model):
  __tablename__ = 'post'
  id = db.Column(db.Integer, primary_key=True)
  category = db.Column(db.String(100), nullable=False)
  thana = db.Column(db.String(100), nullable=False)
  content = db.Column(db.Text, nullable=False)
  status = db.Column(db.String(20), default='pending')
  true_votes = db.Column(db.Integer, default=0)
  false_votes = db.Column(db.Integer, default=0)
  created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notice(db.Model):
  __tablename__ = 'notice'
  id = db.Column(db.Integer, primary_key=True)
  content = db.Column(db.Text, nullable=False)


class AdminSetting(db.Model):
  __tablename__ = 'admin_setting'
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(100), nullable=False)
  password = db.Column(db.String(100), nullable=False)


class HeroText(db.Model):
  __tablename__ = 'hero_text'
  id = db.Column(db.Integer, primary_key=True)
  left_text = db.Column(db.Text, nullable=False)
  right_text = db.Column(db.Text, nullable=False)


with app.app_context():
  db.create_all()
  try:
    if not Notice.query.first():
      default_notice = Notice(
          content=(
              'জনতার খাতা - কিশোরগঞ্জ প্ল্যাটফর্মে আপনাকে স্বাগতম। দুর্নীতি ও'
              ' অনিয়মের বিরুদ্ধে সরব হোন।'
          )
      )
      db.session.add(default_notice)
      db.session.commit()

    if not AdminSetting.query.first():
      default_admin = AdminSetting(username='admin', password='admin123')
      db.session.add(default_admin)
      db.session.commit()

    if not HeroText.query.first():
      default_hero = HeroText(
          left_text='📍 কিশোরগঞ্জ জেলা\n১৩ টি উপজেলা',
          right_text='📢 আপনার পরিচয়\nসম্পূর্ণ গোপন থাকে',
      )
      db.session.add(default_hero)
      db.session.commit()
  except Exception as e:
    db.session.rollback()


def convert_to_bengali_digits(text):
  if text is None:
    return ''
  english_to_bengali = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
  return str(text).translate(english_to_bengali)


def format_bengali_datetime(dt):
  if not dt:
    return ''
  bd_time = dt + timedelta(hours=6)
  months = {
      1: 'জানুয়ারি',
      2: 'ফেব্রুয়ারি',
      3: 'মার্চ',
      4: 'এপ্রিল',
      5: 'মে',
      6: 'জুন',
      7: 'জুলাই',
      8: 'আগস্ট',
      9: 'সেপ্টেম্বর',
      10: 'অক্টোবর',
      11: 'নভেম্বর',
      12: 'ডিসেম্বর',
  }
  day = convert_to_bengali_digits(bd_time.day)
  month = months.get(bd_time.month, '')
  year = convert_to_bengali_digits(bd_time.year)
  hour_24 = bd_time.hour
  minute = bd_time.minute
  ampm = (
      'রাত'
      if (hour_24 >= 20 or hour_24 < 4)
      else (
          'সকাল'
          if (hour_24 >= 4 and hour_24 < 12)
          else (
              'দুপুর'
              if (hour_24 >= 12 and hour_24 < 16)
              else ('বিকাল' if (hour_24 >= 16 and hour_24 < 18) else 'সন্ধ্যা')
          )
      )
  )
  hour_12 = hour_24 % 12 or 12
  return f"{day}ই {month}, {year} • {ampm} {convert_to_bengali_digits(hour_12)}:{convert_to_bengali_digits(f'{minute:02d}')}"


@app.route('/')
def index():
  selected_thana = request.args.get('thana')
  notice = Notice.query.first()
  hero_text = HeroText.query.first()

  all_approved = Post.query.filter(Post.status == 'approved').all()
  total_approved_count = len(all_approved)

  thanas = [
      'কিশোরগঞ্জ সদর',
      'হোসেনপুর',
      'পাকুন্দিয়া',
      'কটিয়াদী',
      'করিমগঞ্জ',
      'তাড়াইল',
      'বাজিতপুর',
      'কুলিয়ারচর',
      'ভৈরব',
      'নিকলী',
      'অষ্টগ্রাম',
      'ইটনা',
      'মিঠামইন',
  ]
  thana_counts = {t: 0 for t in thanas}

  dept_list = [
      'ভূমি অফিস',
      'হিসাবরক্ষণ অফিস',
      'কর অফিস',
      'কাস্টমস অফিস',
      'ট্রাফিক পুলিশ',
      'বিআরটিএ',
      'পাসপোর্ট অফিস',
      'পৌরসভা',
      'সাব-রেজিস্ট্রি অফিস',
      'শিক্ষা অফিস',
      'ইউনিয়ন পরিষদ',
      'সরকারি হাসপাতাল',
      'অন্যান্য সরকারি সেবা',
  ]
  dept_counts = {cat: 0 for cat in dept_list}

  for p in all_approved:
    if p.thana in thana_counts:
      thana_counts[p.thana] += 1
    if p.category in dept_counts:
      dept_counts[p.category] += 1

  if selected_thana and selected_thana != 'all':
    posts_query = [p for p in all_approved if p.thana == selected_thana]
  else:
    posts_query = all_approved

  posts_query.sort(key=lambda x: x.id, reverse=True)

  user_votes = session.get('user_votes', {})

  posts = [{
      'raw_id': p.id,
      'index': convert_to_bengali_digits(len(posts_query) - idx),
      'id': convert_to_bengali_digits(p.id),
      'category': p.category,
      'thana': p.thana,
      'content': p.content,
      'true_votes': convert_to_bengali_digits(p.true_votes),
      'false_votes': convert_to_bengali_digits(p.false_votes),
      'created_at_bn': format_bengali_datetime(p.created_at),
      'voted_type': user_votes.get(str(p.id)),
  } for idx, p in enumerate(posts_query)]

  def calculate_metrics(subset):
    count = len(subset)
    t_votes = sum(p.true_votes for p in subset)
    f_votes = sum(p.false_votes for p in subset)
    total_v = t_votes + f_votes

    if total_v > 0:
      rating_val = round((t_votes / total_v) * 100)
      rating = f'{convert_to_bengali_digits(rating_val)}% নিশ্চিত'
    else:
      rating = '১০০% নিশ্চিত'

    cat_c = {}
    thana_c = {}
    for p in subset:
      cat_c[p.category] = cat_c.get(p.category, 0) + 1
      thana_c[p.thana] = thana_c.get(p.thana, 0) + 1

    top_dept = max(cat_c, key=cat_c.get) if cat_c else 'তথ্য নেই'
    top_thana = max(thana_c, key=thana_c.get) if thana_c else 'তথ্য নেই'

    return {
        'count': convert_to_bengali_digits(count),
        'rating': rating,
        'top_dept': top_dept,
        'top_thana': top_thana,
    }

  all_metrics = calculate_metrics(all_approved)

  now_utc = datetime.utcnow()
  thirty_days_ago = now_utc - timedelta(days=30)
  monthly_posts = [
      p for p in all_approved if p.created_at and p.created_at >= thirty_days_ago
  ]
  monthly_metrics = calculate_metrics(monthly_posts)

  today_start = datetime(now_utc.year, now_utc.month, now_utc.day)
  today_posts = [
      p for p in all_approved if p.created_at and p.created_at >= today_start
  ]
  today_metrics = calculate_metrics(today_posts)

  return render_template(
      'index.html',
      posts=posts,
      thanas=thanas,
      thana_counts={
          t: convert_to_bengali_digits(c) for t, c in thana_counts.items()
      },
      dept_list=dept_list,
      dept_counts={
          k: convert_to_bengali_digits(v) for k, v in dept_counts.items()
      },
      total_approved_count=convert_to_bengali_digits(total_approved_count),
      selected_thana=selected_thana,
      notice=notice,
      hero_text=hero_text,
      all_metrics=all_metrics,
      monthly_metrics=monthly_metrics,
      today_metrics=today_metrics,
  )


@app.route('/submit', methods=['GET', 'POST'])
def submit():
  if request.method == 'POST':
    category, thana, content = (
        request.form.get('category'),
        request.form.get('thana'),
        request.form.get('content'),
    )
    if category and thana and content:
      db.session.add(
          Post(category=category, thana=thana, content=content, status='pending')
      )
      db.session.commit()
      flash('আপনার রিপোর্টটি সফলভাবে জমা হয়েছে! অনুমোদনের পর হোম পেজে দেখানো হবে।')
      return redirect(url_for('index'))
  return render_template('submit.html')


@app.route('/api/vote/<int:post_id>/<vote_type>', methods=['POST'])
def api_vote(post_id, vote_type):
  if 'user_votes' not in session:
    session['user_votes'] = {}

  user_votes = session['user_votes']
  post_key = str(post_id)
  post = Post.query.get_or_404(post_id)

  if post_key in user_votes:
    return jsonify({
        'success': False,
        'message': 'আপনি ইতিমধ্যে এই পোস্টে রিঅ্যাক্ট করেছেন!',
    })

  if vote_type == 'true':
    post.true_votes += 1
  elif vote_type == 'false':
    post.false_votes += 1

  db.session.commit()

  user_votes[post_key] = vote_type
  session['user_votes'] = user_votes
  session.modified = True

  return jsonify({
      'success': True,
      'true_votes': convert_to_bengali_digits(post.true_votes),
      'false_votes': convert_to_bengali_digits(post.false_votes),
      'voted_type': vote_type,
  })


@app.route('/admin', methods=['GET', 'POST'])
def admin():
  notice = Notice.query.first()
  admin_setting = AdminSetting.query.first()
  hero_text = HeroText.query.first()

  if request.method == 'POST':
    u_input = request.form.get('username')
    p_input = request.form.get('password')

    if (
        admin_setting
        and u_input == admin_setting.username
        and p_input == admin_setting.password
    ):
      session['admin_logged_in'] = True
      return redirect(url_for('admin'))
    return render_template(
        'admin.html',
        error='ভুল ইউজারনেম বা পাসওয়ার্ড!',
        notice=notice,
        hero_text=hero_text,
        show_login=True,
    )

  if not session.get('admin_logged_in'):
    return render_template(
        'admin.html', show_login=True, notice=notice, hero_text=hero_text
    )

  pending_posts = (
      Post.query.filter((Post.status == 'pending') | (Post.status == None))
      .order_by(Post.id.desc())
      .all()
  )
  approved_posts = (
      Post.query.filter(Post.status == 'approved')
      .order_by(Post.id.desc())
      .all()
  )
  return render_template(
      'admin.html',
      approved_posts=approved_posts,
      pending_posts=pending_posts,
      notice=notice,
      hero_text=hero_text,
      admin_setting=admin_setting,
      to_bn=convert_to_bengali_digits,
  )


@app.route('/admin/update-notice', methods=['POST'])
def update_notice():
  if not session.get('admin_logged_in'):
    return redirect(url_for('admin'))
  new_text = request.form.get('notice_text')
  if new_text:
    notice = Notice.query.first()
    if not notice:
      db.session.add(Notice(content=new_text))
    else:
      notice.content = new_text
    db.session.commit()
  return redirect(url_for('admin'))


@app.route('/admin/update-hero', methods=['POST'])
def update_hero():
  if not session.get('admin_logged_in'):
    return redirect(url_for('admin'))
  left_val = request.form.get('left_text')
  right_val = request.form.get('right_text')

  hero = HeroText.query.first()
  if hero:
    hero.left_text = left_val
    hero.right_text = right_val
    db.session.commit()
    flash('হিরো ব্যানার সাইডের টেক্সট সফলভাবে আপডেট করা হয়েছে!')
  return redirect(url_for('admin'))


@app.route('/admin/update-credentials', methods=['POST'])
def update_credentials():
  if not session.get('admin_logged_in'):
    return redirect(url_for('admin'))
  new_user = request.form.get('new_username')
  new_pass = request.form.get('new_password')

  if new_user and new_pass:
    admin_setting = AdminSetting.query.first()
    if admin_setting:
      admin_setting.username = new_user
      admin_setting.password = new_pass
      db.session.commit()
      flash('অ্যাডমিন ইউজারনেম ও পাসওয়ার্ড সফলভাবে আপডেট করা হয়েছে!')
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
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port, debug=True)

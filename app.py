from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_wtf.csrf import CSRFProtect
import mysql.connector
import bcrypt
import os
from datetime import timedelta
from werkzeug.utils import secure_filename
from resume_processor import process_resume

UPLOAD_FOLDER      = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'talentscan-secret-key-change-in-production'
app.permanent_session_lifetime = timedelta(hours=8)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

csrf = CSRFProtect(app)

DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': '3104',   # <-- YOUR PASSWORD HERE
    'database': 'talentscan_db'
}

ORG_CODE = 'HRCODE2025'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_user_context():
    name     = session.get('user_name', '')
    initials = ''.join([p[0].upper() for p in name.split() if p])[:2]
    return {
        'user_name':     name,
        'user_email':    session.get('user_email', ''),
        'user_initials': initials,
    }


# ─────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────

@app.route('/')
def index():
    session.clear()
    return redirect(url_for('login'))


# ── LOGIN ──
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        try:
            db     = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM hr_users WHERE email = %s", (email,))
            user = cursor.fetchone()
            db.close()

            if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                session.permanent     = True
                session['user_id']    = user['id']
                session['user_name']  = user['first_name'] + ' ' + user['last_name']
                session['user_email'] = user['email']
                flash('Welcome back, ' + user['first_name'] + '!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid email or password.', 'error')
        except Exception as e:
            flash('Database error: ' + str(e), 'error')

    return render_template('login.html')


# ── SIGNUP ──
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        first_name       = request.form.get('first_name', '').strip()
        last_name        = request.form.get('last_name',  '').strip()
        email            = request.form.get('email',      '').strip().lower()
        password         = request.form.get('password',   '')
        confirm_password = request.form.get('confirm_password', '')
        org_code         = request.form.get('org_code',   '').strip()

        if not all([first_name, last_name, email, password, org_code]):
            flash('All fields are required.', 'error')
            return render_template('signup.html')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('signup.html')
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('signup.html')
        if org_code != ORG_CODE:
            flash('Invalid organization code. Contact your HR administrator.', 'error')
            return render_template('signup.html')

        try:
            db     = get_db()
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id FROM hr_users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('An account with this email already exists.', 'error')
                db.close()
                return render_template('signup.html')

            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            cursor.execute("""
                INSERT INTO hr_users (first_name, last_name, email, password_hash)
                VALUES (%s, %s, %s, %s)
            """, (first_name, last_name, email, hashed))
            db.commit()
            db.close()
            flash('Account created! Please sign in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Database error: ' + str(e), 'error')

    return render_template('signup.html')


# ── DASHBOARD ──
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx = get_user_context()

    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates")
        total_resumes = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates WHERE status='shortlisted'")
        shortlisted = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM job_roles WHERE is_active=TRUE")
        active_roles = cursor.fetchone()['cnt']

        cursor.execute("SELECT AVG(match_score) AS avg FROM candidates")
        avg_row   = cursor.fetchone()
        avg_score = round(avg_row['avg'] or 0)

        cursor.execute("""
            SELECT c.id, c.full_name, c.email, c.match_score, c.status,
                   j.title AS job_role,
                   DATE_FORMAT(c.uploaded_at, '%b %d') AS date
            FROM candidates c
            LEFT JOIN job_roles j ON c.job_role_id = j.id
            ORDER BY c.uploaded_at DESC LIMIT 8
        """)
        rows = cursor.fetchall()
        candidates = []
        status_map = {'shortlisted':'shortlisted','reviewing':'reviewing','rejected':'rejected','new':'new','processed':'new'}
        for r in rows:
            parts = (r['full_name'] or '').split()
            ic    = ''.join([p[0].upper() for p in parts if p])[:2]
            candidates.append({
                'id':           r['id'],
                'name':         r['full_name'],
                'email':        r['email'],
                'job_role':     r['job_role'] or 'General',
                'score':        r['match_score'] or 0,
                'status':       (r['status'] or 'new').title(),
                'status_class': status_map.get(r['status'], 'new'),
                'date':         r['date'],
                'initials':     ic or '?',
            })

        cursor.execute("""
            SELECT j.title, COUNT(c.id) AS applicants,
                   COALESCE(MAX(c.match_score),0) AS top_score
            FROM job_roles j
            LEFT JOIN candidates c ON c.job_role_id = j.id
            WHERE j.is_active = TRUE
            GROUP BY j.id, j.title
            ORDER BY applicants DESC LIMIT 5
        """)
        job_roles = cursor.fetchall()

        cursor.execute("""
            SELECT action_text, color,
                   DATE_FORMAT(created_at, '%b %d, %H:%i') AS time
            FROM activity_log WHERE user_id = %s
            ORDER BY created_at DESC LIMIT 6
        """, (session['user_id'],))
        activities = cursor.fetchall()
        db.close()

    except Exception:
        total_resumes = 0; shortlisted = 0; active_roles = 0
        avg_score = 0; candidates = []; job_roles = []; activities = []

    return render_template('dashboard.html',
        **ctx,
        total_resumes=total_resumes, shortlisted=shortlisted,
        active_roles=active_roles, avg_score=avg_score,
        candidates=candidates, job_roles=job_roles,
        activities=activities, total_candidates=total_resumes,
    )


# ── UPLOAD RESUMES ──
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx = get_user_context()

    if request.method == 'POST':
        files          = request.files.getlist('resumes')
        job_role_id    = request.form.get('job_role_id', '')
        candidate_name = request.form.get('candidate_name', '').strip()

        if not files or all(f.filename == '' for f in files):
            flash('Please select at least one resume file.', 'error')
            return redirect(url_for('upload'))

        if not job_role_id:
            flash('Please select a job role.', 'error')
            return redirect(url_for('upload'))

        # Get job title for scoring
        job_title = ''
        if job_role_id != 'general':
            try:
                db     = get_db()
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT title FROM job_roles WHERE id=%s", (job_role_id,))
                row = cursor.fetchone()
                db.close()
                job_title = row['title'] if row else ''
            except Exception:
                pass

        uploaded = 0
        errors   = 0

        for file in files:
            if file.filename == '':
                continue
            if not allowed_file(file.filename):
                flash(f'{file.filename} — only PDF and DOCX allowed.', 'error')
                errors += 1
                continue

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # ── AI Processing ──
            result = process_resume(filepath, job_title)

            # Use provided name or AI-extracted name
            cand_name  = candidate_name or result.get('name') or filename.rsplit('.', 1)[0].replace('_', ' ').title()
            cand_email = result.get('email', '')
            skills     = ', '.join(result.get('skills', []))
            score      = result.get('score', 0)
            role_id    = None if job_role_id == 'general' else job_role_id

            try:
                db     = get_db()
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO candidates
                      (full_name, email, resume_filename, job_role_id,
                       match_score, extracted_skills, status, uploaded_by)
                    VALUES (%s, %s, %s, %s, %s, %s, 'processed', %s)
                """, (cand_name, cand_email, filename, role_id,
                      score, skills, session['user_id']))

                # Log activity
                cursor.execute("""
                    INSERT INTO activity_log (user_id, action_text, color)
                    VALUES (%s, %s, %s)
                """, (session['user_id'],
                      f'Resume uploaded: {cand_name} — {score}% match',
                      'on' if score >= 70 else ('yellow' if score >= 40 else 'red')))

                db.commit()
                db.close()
                uploaded += 1
            except Exception as e:
                flash('DB error: ' + str(e), 'error')
                errors += 1

        if uploaded > 0:
            flash(f'{uploaded} resume(s) uploaded and analysed successfully!', 'success')
        if errors > 0:
            flash(f'{errors} file(s) could not be processed.', 'error')

        return redirect(url_for('upload'))

    # GET
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, title FROM job_roles WHERE is_active=TRUE ORDER BY title")
        job_roles = cursor.fetchall()

        cursor.execute("""
            SELECT c.resume_filename AS filename,
                   COALESCE(j.title,'General') AS job_role,
                   c.status, c.match_score,
                   DATE_FORMAT(c.uploaded_at,'%b %d, %H:%i') AS date
            FROM candidates c
            LEFT JOIN job_roles j ON c.job_role_id = j.id
            ORDER BY c.uploaded_at DESC LIMIT 10
        """)
        rows = cursor.fetchall()
        db.close()

        uploads = []
        for r in rows:
            uploads.append({
                'filename':     r['filename'],
                'job_role':     r['job_role'],
                'score':        r['match_score'] or 0,
                'status':       'Processed' if r['status'] == 'processed' else r['status'].title(),
                'status_class': 'processed' if r['status'] in ('processed','shortlisted') else 'pending',
                'date':         r['date'],
            })
    except Exception:
        job_roles = []
        uploads   = []

    return render_template('upload.html', **ctx, job_roles=job_roles, uploads=uploads)


# ── LOGOUT ──
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'success')
    return redirect(url_for('login'))


# ── CANDIDATES LIST ──
@app.route('/candidates')
def candidates():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx = get_user_context()

    selected_role   = request.args.get('role',   '')
    selected_status = request.args.get('status', '')
    selected_sort   = request.args.get('sort',   'score_desc')
    search_query    = request.args.get('search', '')

    sort_map = {
        'score_desc': 'c.match_score DESC',
        'score_asc':  'c.match_score ASC',
        'date_desc':  'c.uploaded_at DESC',
        'date_asc':   'c.uploaded_at ASC',
        'name_asc':   'c.full_name ASC',
    }
    order_by = sort_map.get(selected_sort, 'c.match_score DESC')

    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates")
        total_count = cursor.fetchone()['cnt']

        cursor.execute("SELECT id, title FROM job_roles WHERE is_active=TRUE ORDER BY title")
        job_roles = cursor.fetchall()

        query  = """
            SELECT c.id, c.full_name, c.email, c.match_score,
                   c.status, c.extracted_skills,
                   j.title AS job_role,
                   DATE_FORMAT(c.uploaded_at, '%b %d, %Y') AS date
            FROM candidates c
            LEFT JOIN job_roles j ON c.job_role_id = j.id
            WHERE 1=1
        """
        params = []

        if selected_role:
            query += " AND c.job_role_id = %s"
            params.append(selected_role)
        if selected_status:
            query += " AND c.status = %s"
            params.append(selected_status)
        if search_query:
            query += " AND (c.full_name LIKE %s OR c.email LIKE %s)"
            params.extend([f'%{search_query}%', f'%{search_query}%'])

        query += f" ORDER BY {order_by}"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        db.close()

        status_map = {'shortlisted':'shortlisted','reviewing':'reviewing','rejected':'rejected','new':'new','processed':'processed'}
        candidates_list = []
        for r in rows:
            parts  = (r['full_name'] or '').split()
            ic     = ''.join([p[0].upper() for p in parts if p])[:2]
            skills = [s.strip() for s in (r['extracted_skills'] or '').split(',') if s.strip()]
            candidates_list.append({
                'id':           r['id'],
                'name':         r['full_name'],
                'email':        r['email'] or '',
                'job_role':     r['job_role'] or 'General',
                'score':        r['match_score'] or 0,
                'status':       (r['status'] or 'new').title(),
                'status_class': status_map.get(r['status'], 'new'),
                'date':         r['date'],
                'initials':     ic or '?',
                'top_skills':   skills[:4],
                'extra_skills': max(0, len(skills) - 4),
            })

    except Exception as e:
        candidates_list = []; job_roles = []; total_count = 0

    return render_template('candidates.html',
        **ctx,
        candidates=candidates_list, job_roles=job_roles,
        total_count=total_count, selected_role=selected_role,
        selected_status=selected_status, selected_sort=selected_sort,
        search_query=search_query,
    )


# ── UPDATE CANDIDATE STATUS ──
@app.route('/candidate/<int:cid>/status', methods=['POST'])
def update_status(cid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    new_status = request.form.get('status', '')
    if new_status not in ('shortlisted', 'reviewing', 'rejected', 'new', 'processed'):
        flash('Invalid status.', 'error')
        redirect_to = request.form.get('redirect', '')
    if redirect_to == 'profile':
        return redirect(url_for('candidate_profile', cid=cid))
    return redirect(url_for('candidates'))

    try:
        db     = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE candidates SET status=%s WHERE id=%s", (new_status, cid))
        cursor.execute("""
            INSERT INTO activity_log (user_id, action_text, color)
            VALUES (%s, %s, %s)
        """, (session['user_id'],
              f'Candidate #{cid} marked as {new_status}',
              'on' if new_status == 'shortlisted' else ('red' if new_status == 'rejected' else 'yellow')))
        db.commit()
        db.close()
        flash(f'Candidate status updated to {new_status}.', 'success')
    except Exception as e:
        flash('Error: ' + str(e), 'error')

    return redirect(url_for('candidates'))


# ── ANALYTICS ──
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx = get_user_context()

    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates")
        row = cursor.fetchone()
        print("DEBUG total row:", row)
        total = row['cnt']

        cursor.execute("SELECT COALESCE(AVG(match_score),0) AS avg FROM candidates")
        avg_score = round(cursor.fetchone()['avg'])

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates WHERE status='shortlisted'")
        shortlisted = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates WHERE uploaded_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        this_week = cursor.fetchone()['cnt']

        cursor.execute("SELECT match_score AS mx, full_name FROM candidates ORDER BY match_score DESC LIMIT 1")
        top_row = cursor.fetchone()
        top_score     = top_row['mx'] or 0
        top_candidate = top_row['full_name'] or 'N/A'
        shortlist_rate = round((shortlisted / total * 100)) if total > 0 else 0

        # Pipeline (status breakdown)
        cursor.execute("SELECT status, COUNT(*) AS cnt FROM candidates GROUP BY status")
        pipeline_rows = cursor.fetchall()
        label_map = {'new':'New','processed':'Processed','shortlisted':'Shortlisted','reviewing':'Reviewing','rejected':'Rejected'}
        pipeline_data = {'labels': [], 'values': []}
        for r in pipeline_rows:
            pipeline_data['labels'].append(label_map.get(r['status'], r['status'].title()))
            pipeline_data['values'].append(r['cnt'])

        # Score distribution bands
        bands_def = [
            ('0-20',  0,  20,  'low'),
            ('21-40', 21, 40,  'low'),
            ('41-60', 41, 60,  'mid'),
            ('61-80', 61, 80,  'high'),
            ('81-100',81, 100, 'high'),
        ]
        score_bands = []
        max_cnt = 1
        band_counts = []
        for label, lo, hi, color in bands_def:
            cursor.execute("SELECT COUNT(*) AS cnt FROM candidates WHERE match_score BETWEEN %s AND %s", (lo, hi))
            cnt = cursor.fetchone()['cnt']
            band_counts.append((label, cnt, color))
            if cnt > max_cnt:
                max_cnt = cnt

        for label, cnt, color in band_counts:
            height = max(4, round((cnt / max_cnt) * 72)) if max_cnt > 0 else 4
            score_bands.append({'label': label, 'count': cnt, 'color': color, 'height': height})

        # Top skills
        cursor.execute("SELECT extracted_skills FROM candidates WHERE extracted_skills IS NOT NULL AND extracted_skills != ''")
        skill_rows = cursor.fetchall()
        skill_freq = {}
        for row in skill_rows:
            for s in row['extracted_skills'].split(','):
                s = s.strip()
                if s:
                    skill_freq[s] = skill_freq.get(s, 0) + 1

        sorted_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        max_skill = sorted_skills[0][1] if sorted_skills else 1
        top_skills = [{'name': s, 'count': c, 'pct': round(c / max_skill * 100)} for s, c in sorted_skills]

        # Role breakdown
        cursor.execute("""
            SELECT j.title, COUNT(c.id) AS cnt
            FROM job_roles j
            LEFT JOIN candidates c ON c.job_role_id = j.id
            WHERE j.is_active = TRUE
            GROUP BY j.id, j.title
            ORDER BY cnt DESC
        """)
        role_rows  = cursor.fetchall()
        role_colors = ['#6BBF59','#FFC107','#2196F3','#F44336','#9C27B0','#FF5722','#00BCD4']
        role_total  = sum(r['cnt'] for r in role_rows) or 1
        role_breakdown = []
        for i, r in enumerate(role_rows):
            role_breakdown.append({
                'title': r['title'],
                'count': r['cnt'],
                'pct':   round(r['cnt'] / role_total * 100),
                'color': role_colors[i % len(role_colors)],
            })

        db.close()

    except Exception as e:
        print("ANALYTICS ERROR:", str(e))
        import traceback; traceback.print_exc()
        total = avg_score = shortlisted = this_week = top_score = shortlist_rate = 0
        top_candidate = 'N/A'
        pipeline_data  = {'labels': [], 'values': []}
        score_bands    = [{'label': l, 'count': 0, 'color': c, 'height': 4} for l, c in [('0-20','low'),('21-40','low'),('41-60','mid'),('61-80','high'),('81-100','high')]]
        top_skills     = []
        role_breakdown = []

    return render_template('analytics.html',
        **ctx,
        stats={
            'total': total, 'avg_score': avg_score,
            'shortlisted': shortlisted, 'this_week': this_week,
            'top_score': top_score, 'top_candidate': top_candidate,
            'shortlist_rate': shortlist_rate,
        },
        pipeline_data=pipeline_data,
        score_bands=score_bands,
        top_skills=top_skills,
        role_breakdown=role_breakdown,
    )


# ── CANDIDATE PROFILE ──
@app.route('/candidate/<int:cid>')
def candidate_profile(cid):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx = get_user_context()

    from resume_processor import JOB_REQUIRED_SKILLS

    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, j.title AS job_role
            FROM candidates c
            LEFT JOIN job_roles j ON c.job_role_id = j.id
            WHERE c.id = %s
        """, (cid,))
        row = cursor.fetchone()
        db.close()

        if not row:
            flash('Candidate not found.', 'error')
            return redirect(url_for('candidates'))

        parts    = (row['full_name'] or '').split()
        initials = ''.join([p[0].upper() for p in parts if p])[:2]
        skills   = [s.strip() for s in (row['extracted_skills'] or '').split(',') if s.strip()]

        job_title = (row['job_role'] or '').lower().strip()
        required_skills = set()
        for key, val in JOB_REQUIRED_SKILLS.items():
            if key in job_title or job_title in key:
                required_skills = val
                break

        matched_skills = set(skills).intersection(required_skills)

        status_map = {'shortlisted':'shortlisted','reviewing':'reviewing','rejected':'rejected','new':'new','processed':'processed'}

        candidate = {
            'id':             row['id'],
            'name':           row['full_name'],
            'email':          row['email'] or '',
            'job_role':       row['job_role'] or 'General',
            'score':          row['match_score'] or 0,
            'status':         (row['status'] or 'new').title(),
            'status_class':   status_map.get(row['status'], 'new'),
            'filename':       row['resume_filename'] or 'N/A',
            'date':           row['uploaded_at'].strftime('%b %d, %Y') if row['uploaded_at'] else 'N/A',
            'initials':       initials or '?',
            'skills':         skills,
            'matched_skills': matched_skills,
            'required_skills': sorted(list(required_skills)),
        }

    except Exception as e:
        flash('Error loading profile: ' + str(e), 'error')
        return redirect(url_for('candidates'))

    return render_template('candidate_profile.html', **ctx, candidate=candidate)


# ── DOWNLOAD RESUME ──
@app.route('/download/<int:cid>')
def download_resume(cid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT resume_filename FROM candidates WHERE id=%s", (cid,))
        row = cursor.fetchone()
        db.close()
        if row and row['resume_filename']:
            from flask import send_from_directory
            return send_from_directory(UPLOAD_FOLDER, row['resume_filename'], as_attachment=True)
    except Exception as e:
        flash('Error downloading file: ' + str(e), 'error')
    return redirect(url_for('candidates'))


# ── JOB ROLES ──
@app.route('/job-roles')
def job_roles():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    ctx = get_user_context()
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT j.id, j.title, j.description, j.is_active,
                   COUNT(c.id) AS applicants,
                   COALESCE(ROUND(AVG(c.match_score)),0) AS avg_score
            FROM job_roles j
            LEFT JOIN candidates c ON c.job_role_id = j.id
            GROUP BY j.id, j.title, j.description, j.is_active
            ORDER BY j.is_active DESC, j.title ASC
        """)
        roles = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) AS cnt FROM job_roles")
        total = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM job_roles WHERE is_active=TRUE")
        active = cursor.fetchone()['cnt']
        cursor.execute("SELECT COUNT(*) AS cnt FROM candidates")
        total_applicants = cursor.fetchone()['cnt']
        db.close()
    except Exception as e:
        roles = []; total = active = total_applicants = 0
    return render_template('job_roles.html', **ctx, roles=roles,
        stats={'total': total, 'active': active, 'total_applicants': total_applicants})


@app.route('/job-roles/add', methods=['POST'])
def add_job_role():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not title:
        flash('Job title is required.', 'error')
        return redirect(url_for('job_roles'))
    try:
        db     = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO job_roles (title, description) VALUES (%s, %s)", (title, description))
        db.commit(); db.close()
        flash(f'Job role "{title}" added successfully!', 'success')
    except Exception as e:
        flash('Error adding role: ' + str(e), 'error')
    return redirect(url_for('job_roles'))


@app.route('/job-roles/<int:rid>/edit', methods=['POST'])
def edit_job_role(rid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title       = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    if not title:
        flash('Job title is required.', 'error')
        return redirect(url_for('job_roles'))
    try:
        db     = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE job_roles SET title=%s, description=%s WHERE id=%s", (title, description, rid))
        db.commit(); db.close()
        flash(f'Job role updated successfully!', 'success')
    except Exception as e:
        flash('Error updating role: ' + str(e), 'error')
    return redirect(url_for('job_roles'))


@app.route('/job-roles/<int:rid>/toggle', methods=['POST'])
def toggle_job_role(rid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT is_active FROM job_roles WHERE id=%s", (rid,))
        row = cursor.fetchone()
        new_val = not row['is_active']
        cursor.execute("UPDATE job_roles SET is_active=%s WHERE id=%s", (new_val, rid))
        db.commit(); db.close()
        flash('Job role ' + ('activated' if new_val else 'deactivated') + '.', 'success')
    except Exception as e:
        flash('Error: ' + str(e), 'error')
    return redirect(url_for('job_roles'))


@app.route('/job-roles/<int:rid>/delete', methods=['POST'])
def delete_job_role(rid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        db     = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE candidates SET job_role_id=NULL WHERE job_role_id=%s", (rid,))
        cursor.execute("DELETE FROM job_roles WHERE id=%s", (rid,))
        db.commit(); db.close()
        flash('Job role deleted.', 'success')
    except Exception as e:
        flash('Error deleting role: ' + str(e), 'error')
    return redirect(url_for('job_roles'))


# ── RANKINGS ──
@app.route('/rankings')
def rankings():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ctx           = get_user_context()
    selected_role = request.args.get('role', '')
    min_score     = request.args.get('min_score', '0')

    try:
        db     = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT id, title FROM job_roles WHERE is_active=TRUE ORDER BY title")
        job_roles = cursor.fetchall()

        query  = """
            SELECT c.id, c.full_name, c.email, c.match_score,
                   c.status, c.extracted_skills,
                   j.title AS job_role
            FROM candidates c
            LEFT JOIN job_roles j ON c.job_role_id = j.id
            WHERE c.match_score >= %s
        """
        params = [int(min_score) if min_score.isdigit() else 0]

        if selected_role:
            query += " AND c.job_role_id = %s"
            params.append(selected_role)

        query += " ORDER BY c.match_score DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        db.close()

        status_map = {'shortlisted':'shortlisted','reviewing':'reviewing','rejected':'rejected','new':'new','processed':'processed'}
        candidates = []
        for r in rows:
            parts  = (r['full_name'] or '').split()
            ic     = ''.join([p[0].upper() for p in parts if p])[:2]
            skills = [s.strip() for s in (r['extracted_skills'] or '').split(',') if s.strip()]
            candidates.append({
                'id':           r['id'],
                'name':         r['full_name'],
                'email':        r['email'] or '',
                'job_role':     r['job_role'] or 'General',
                'score':        r['match_score'] or 0,
                'status':       (r['status'] or 'new').title(),
                'status_class': status_map.get(r['status'], 'new'),
                'initials':     ic or '?',
                'top_skills':   skills[:3],
                'extra_skills': max(0, len(skills) - 3),
            })

    except Exception as e:
        candidates = []; job_roles = []

    return render_template('rankings.html',
        **ctx,
        candidates=candidates,
        job_roles=job_roles,
        selected_role=selected_role,
        min_score=min_score,
    )

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)

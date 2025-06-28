import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors
from dotenv import load_dotenv, find_dotenv
import calendar
from datetime import datetime, timedelta

# .env 파일의 절대 경로를 명시하여 환경 변수를 로드합니다.
# Apache/mod_wsgi 환경에서 .env 로딩 문제가 발생할 경우를 대비합니다.
dotenv_path = find_dotenv('/var/www/html/your_flask_app/.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
    print("DEBUG: .env variables loaded from explicit path.") # 디버깅용 로그
else:
    print(f"WARNING: .env file not found at {dotenv_path}. Environment variables might not be loaded.") # 디버깅용 로그

# Flask 애플리케이션 인스턴스 생성
app = Flask(__name__)

# FLASK_SECRET_KEY 로딩 및 처리 로직
# 환경 변수에서 SECRET_KEY를 가져옵니다. 없을 경우 임시 키를 생성합니다.
# 프로덕션 환경에서는 반드시 .env에 유효하고 고유한 키가 존재해야 합니다.
flask_secret_key = os.getenv('FLASK_SECRET_KEY')
if not flask_secret_key:
    flask_secret_key = os.urandom(24).hex() # 임시 키 생성
    print(f"WARNING: FLASK_SECRET_KEY not found in .env. Using newly generated key for this run: {flask_secret_key}") # 디버깅용 로그
    print("Please add 'FLASK_SECRET_KEY={}' to your .env file for persistent security.".format(flask_secret_key)) # 디버깅용 로그

app.secret_key = flask_secret_key
print(f"DEBUG: Flask secret key loaded: {'exists' if app.secret_key else 'NOT FOUND'}") # 디버깅용 로그


# 데이터베이스 연결 설정
# 환경 변수가 설정되지 않았을 경우 사용할 기본값(폴백)을 지정합니다.
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '10.10.8.4'),
    'user': os.getenv('DB_USER', 'flask_user'),
    'password': os.getenv('DB_PASSWORD', 'P@ssw0rd'),
    'db': os.getenv('DB_NAME', 'flask_auth_db'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db_connection():
    """데이터베이스 연결을 설정하고 반환합니다."""
    print("DEBUG: Attempting to get DB connection...") # 디버깅용 로그
    try:
        conn = pymysql.connect(**DB_CONFIG)
        print("DEBUG: DB connection successful!") # 디버깅용 로그
        return conn
    except pymysql.Error as e:
        print(f"DEBUG: DB connection failed in get_db_connection: {e}") # 디버깅용 로그
        flash('데이터베이스 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요.', 'error')
        raise

# --- 사용자 인증 관련 라우트 ---

@app.route('/')
def index():
    """
    메인 페이지를 렌더링합니다.
    로그인 상태에 따라 다른 UI (인증 폼 또는 링크 메뉴)를 보여줍니다.
    """
    if 'loggedin' in session:
        # 로그인 상태이면, 일기쓰기, 게시판, To-Do List 링크가 있는 메인 페이지를 보여줌
        return render_template('main_logged_in.html', username=session['username'])
    # 로그아웃 상태이면, 로그인/회원가입 폼이 있는 기본 페이지를 보여줌
    return render_template('default.html')


@app.route('/register', methods=['POST'])
def register():
    """사용자 등록을 처리합니다."""
    username = request.form['username'].strip()
    password = request.form['password'].strip()

    if not username or not password:
        flash('사용자 이름과 비밀번호를 비워둘 수 없습니다.', 'error')
        return redirect(url_for('index'))

    hashed_password = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 사용자 이름 중복 확인
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('이미 존재하는 사용자 이름입니다. 다른 이름을 선택해주세요.', 'error')
                return redirect(url_for('index'))

            # 새 사용자 삽입
            sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, hashed_password))
        conn.commit() # 트랜잭션 커밋
        flash('회원가입에 성공했습니다! 이제 로그인할 수 있습니다.', 'success')
    except Exception as e:
        print(f"데이터베이스 오류 (회원가입): {e}") # 디버깅용 로그
        flash('회원가입에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """사용자 로그인을 처리합니다."""
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    print(f"DEBUG: 로그인 시도 사용자: {username}") # 디버깅용 로그

    if not username or not password:
        print("DEBUG: 로그인 시도: 사용자 이름 또는 비밀번호가 비어 있습니다.") # 디버깅용 로그
        flash('사용자 이름과 비밀번호를 모두 입력해주세요.', 'error')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, username, password FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                session['loggedin'] = True
                session['id'] = user['id']
                session['username'] = user['username']
                print(f"DEBUG: 사용자 {username} 로그인 성공. 대시보드로 리디렉션.") # 디버깅용 로그
                flash(f'환영합니다, {user["username"]}님!', 'success')
                return redirect(url_for('dashboard')) # 로그인 성공 시 대시보드로 리디렉션
            else:
                print(f"DEBUG: 사용자 {username} 로그인 실패: 잘못된 자격 증명.") # 디버깅용 로그
                flash('잘못된 사용자 이름 또는 비밀번호입니다. 다시 시도해주세요.', 'error')
    except Exception as e:
        print(f"DEBUG: 로그인 처리 중 일반 오류: {e}") # 디버깅용 로그
        flash('로그인에 실패했습니다. 서버 오류입니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
            print("DEBUG: 로그인 라우트에서 DB 연결 닫음.") # 디버깅용 로그
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """현재 사용자를 로그아웃합니다."""
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    flash('성공적으로 로그아웃되었습니다.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """
    로그인한 사용자에게는 메인 페이지로 리디렉션하고,
    로그아웃 상태이면 로그인 페이지로 리디렉션합니다.
    """
    if 'loggedin' in session:
        return redirect(url_for('index')) # 로그인 상태이면 새로운 메인 페이지 (index)로 리디렉션
    flash('이 페이지에 접근하려면 로그인해야 합니다.', 'error')
    return redirect(url_for('index')) # 로그아웃 상태이면 로그인 페이지 (index)로 리디렉션


# --- 게시판 관련 라우트 ---

@app.route('/board')
def board_list():
    """검색 기능을 포함한 게시글 목록을 표시합니다."""
    if 'loggedin' not in session:
        flash('게시판을 보려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    search_query = request.args.get('query', '').strip()

    conn = None
    posts = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT b.id, b.title, b.content, b.created_at, b.updated_at, u.username " \
                  "FROM board b JOIN users u ON b.user_id = u.id"
            params = []

            if search_query:
                sql += " WHERE b.title LIKE %s OR b.content LIKE %s"
                params.append(f"%{search_query}%")
                params.append(f"%{search_query}%")

            sql += " ORDER BY b.created_at DESC" # 정렬 기준은 최신순 유지

            cursor.execute(sql, params) # 파라미터화된 쿼리 실행
            posts = cursor.fetchall()
    except Exception as e:
        print(f"데이터베이스 오류 (게시글 불러오기 및 검색): {e}")
        flash('게시판 글을 불러오는 데 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return render_template('board_list.html', posts=posts, username=session['username'], search_query=search_query)

@app.route('/board/write', methods=['GET', 'POST'])
def write_post():
    """새 게시글 작성을 처리합니다."""
    if 'loggedin' not in session:
        flash('게시글을 작성하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        user_id = session['id']

        if not title or not content:
            flash('제목과 내용은 비워둘 수 없습니다.', 'error')
            return redirect(url_for('write_post'))

        conn = None
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                sql = "INSERT INTO board (user_id, title, content) VALUES (%s, %s, %s)"
                cursor.execute(sql, (user_id, title, content))
            conn.commit()
            flash('게시글이 성공적으로 작성되었습니다!', 'success')
        except Exception as e:
            print(f"데이터베이스 오류 (게시글 작성): {e}")
            flash('게시글 작성에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
        finally:
            if conn:
                conn.close()
        return redirect(url_for('board_list'))
    return render_template('write_post.html', username=session['username'])

@app.route('/board/view/<int:post_id>')
def view_post(post_id):
    """단일 게시글과 해당 댓글을 표시합니다."""
    if 'loggedin' not in session:
        flash('게시글을 보려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    conn = None
    post = None
    comments = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql_post = "SELECT b.id, b.title, b.content, b.created_at, b.updated_at, b.user_id, u.username " \
                       "FROM board b JOIN users u ON b.user_id = u.id WHERE b.id = %s"
            cursor.execute(sql_post, (post_id,))
            post = cursor.fetchone()

            if not post:
                flash('게시글을 찾을 수 없습니다.', 'error')
                return redirect(url_for('board_list'))

            sql_comments = "SELECT c.id, c.content, c.created_at, u.username, c.user_id " \
                           "FROM comments c JOIN users u ON c.user_id = u.id WHERE c.board_id = %s ORDER BY c.created_at ASC"
            cursor.execute(sql_comments, (post_id,))
            comments = cursor.fetchall()

    except Exception as e:
        print(f"데이터베이스 오류 (게시글 조회): {e}")
        flash('게시글을 불러오는 데 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return render_template('view_post.html', post=post, comments=comments, username=session['username'])

@app.route('/board/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    """기존 게시글 편집을 처리합니다."""
    if 'loggedin' not in session:
        flash('게시글을 수정하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    conn = None
    post = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, title, content, user_id FROM board WHERE id = %s"
            cursor.execute(sql, (post_id,))
            post = cursor.fetchone()

            if not post:
                flash('게시글을 찾을 수 없습니다.', 'error')
                return redirect(url_for('board_list'))

            if post['user_id'] != session['id']:
                flash('이 게시글을 수정할 권한이 없습니다.', 'error')
                return redirect(url_for('view_post', post_id=post_id))

        if request.method == 'POST':
            title = request.form['title'].strip()
            content = request.form['content'].strip()

            if not title or not content:
                flash('제목과 내용은 비워둘 수 없습니다.', 'error')
                return redirect(url_for('edit_post', post_id=post_id))

            with conn.cursor() as cursor:
                sql = "UPDATE board SET title = %s, content = %s WHERE id = %s"
                cursor.execute(sql, (title, content, post_id))
            conn.commit()
            flash('게시글이 성공적으로 수정되었습니다!', 'success')
            return redirect(url_for('view_post', post_id=post_id))
    except Exception as e:
        print(f"데이터베이스 오류 (게시글 수정): {e}")
        flash('게시글 수정에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return render_template('edit_post.html', post=post, username=session['username'])

@app.route('/board/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    """게시글 삭제를 처리합니다."""
    if 'loggedin' not in session:
        flash('게시글을 삭제하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql_check = "SELECT user_id FROM board WHERE id = %s"
            cursor.execute(sql_check, (post_id,))
            post_owner = cursor.fetchone()

            if not post_owner:
                flash('게시글을 찾을 수 없습니다.', 'error')
                return redirect(url_for('board_list'))

            if post_owner['user_id'] != session['id']:
                flash('이 게시글을 삭제할 권한이 없습니다.', 'error')
                return redirect(url_for('view_post', post_id=post_id))

            sql_delete = "DELETE FROM board WHERE id = %s"
            cursor.execute(sql_delete, (post_id,))
        conn.commit()
        flash('게시글이 성공적으로 삭제되었습니다!', 'success')
    except Exception as e:
        print(f"데이터베이스 오류 (게시글 삭제): {e}")
        flash('게시글 삭제에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('board_list'))


@app.route('/comment/add/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    """게시글에 댓글 추가를 처리합니다."""
    if 'loggedin' not in session:
        flash('댓글을 작성하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    content = request.form['content'].strip()
    user_id = session['id']

    if not content:
        flash('댓글 내용은 비워둘 수 없습니다.', 'error')
        return redirect(url_for('view_post', post_id=post_id))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM board WHERE id = %s", (post_id,))
            if not cursor.fetchone():
                flash('댓글을 달 게시글을 찾을 수 없습니다.', 'error')
                return redirect(url_for('board_list'))

            sql = "INSERT INTO comments (board_id, user_id, content) VALUES (%s, %s, %s)"
            cursor.execute(sql, (post_id, user_id, content))
        conn.commit()
        flash('댓글이 성공적으로 작성되었습니다!', 'success')
    except Exception as e:
        print(f"데이터베이스 오류 (댓글 작성): {e}")
        flash('댓글 작성에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('view_post', post_id=post_id))


# --- 일기장 관련 라우트 ---

@app.route('/diary')
@app.route('/diary/<int:year>/<int:month>')
def diary_calendar(year=None, month=None):
    """사용자별 월 달력을 표시하고 일기 기록 여부를 나타냅니다."""
    if 'loggedin' not in session:
        flash('일기장을 보려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    today = datetime.now()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    if not (1 <= month <= 12 and 1900 <= year <= 2100):
        flash('유효하지 않은 연도 또는 월입니다.', 'error')
        return redirect(url_for('diary_calendar'))

    prev_month_date = (datetime(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month_date = (datetime(year, month, 1) + timedelta(days=31)).replace(day=1)

    prev_year, prev_month = prev_month_date.year, prev_month_date.month
    next_year, next_month = next_month_date.year, next_month_date.month

    cal = calendar.Calendar(firstweekday=6) # 일요일부터 시작
    month_days = cal.monthdayscalendar(year, month)

    user_id = session['id']
    diary_dates = set()

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT DATE_FORMAT(entry_date, '%%Y-%%m-%%d') AS entry_date_str FROM diaries WHERE user_id = %s AND YEAR(entry_date) = %s AND MONTH(entry_date) = %s"
            cursor.execute(sql, (user_id, year, month))
            for row in cursor.fetchall():
                diary_dates.add(row['entry_date_str'])
    except Exception as e:
        print(f"DEBUG: 일기 데이터를 불러오는 데 오류 발생: {e}")
        flash('일기 데이터를 불러오는 데 실패했습니다.', 'error')
    finally:
        if conn:
            conn.close()

    return render_template('diary_calendar.html',
                           year=year,
                           month=month,
                           month_name=datetime(year, month, 1).strftime('%B'),
                           month_days=month_days,
                           diary_dates=diary_dates,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           current_day=today.day if today.year == year and today.month == month else None,
                           today=today,
                           username=session['username'])

@app.route('/diary/entry/<string:date_str>', methods=['GET', 'POST'])
def diary_entry(date_str):
    """특정 날짜의 일기를 작성/조회/수정합니다."""
    if 'loggedin' not in session:
        flash('일기를 작성/조회하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    entry_date = None
    try:
        entry_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('유효하지 않은 날짜 형식입니다.', 'error')
        return redirect(url_for('diary_calendar'))

    diary = None
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, title, content, DATE_FORMAT(entry_date, '%%Y-%%m-%%d') AS entry_date_str FROM diaries WHERE user_id = %s AND entry_date = %s"
            cursor.execute(sql, (user_id, entry_date))
            diary = cursor.fetchone()

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            content = request.form['content'].strip()

            if not content:
                flash('일기 내용은 비워둘 수 없습니다.', 'error')
                return redirect(url_for('diary_entry', date_str=date_str))

            with conn.cursor() as cursor:
                if diary: # 기존 일기 수정
                    sql = "UPDATE diaries SET title = %s, content = %s WHERE id = %s AND user_id = %s"
                    cursor.execute(sql, (title, content, diary['id'], user_id))
                    flash('일기가 성공적으로 수정되었습니다!', 'success')
                else: # 새 일기 작성
                    sql = "INSERT INTO diaries (user_id, entry_date, title, content) VALUES (%s, %s, %s, %s)"
                    cursor.execute(sql, (user_id, entry_date, title, content))
                    flash('일기가 성공적으로 작성되었습니다!', 'success')
            conn.commit()
            return redirect(url_for('diary_calendar', year=entry_date.year, month=entry_date.month))

    except Exception as e:
        print(f"DEBUG: diary_entry에서 데이터베이스 오류: {e}")
        flash('일기 처리 중 오류가 발생했습니다.', 'error')
    finally:
        if conn:
            conn.close()

    return render_template('diary_entry.html', diary=diary, date_str=date_str, username=session['username'])


# --- To-Do List 관련 라우트 ---

@app.route('/todos')
def todos_list():
    """To-Do 목록을 표시하고 필터링 옵션을 제공합니다."""
    if 'loggedin' not in session:
        flash('To-Do List를 보려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    status_filter = request.args.get('status', 'all').strip() # 'all' 또는 특정 상태 (예: '미완료')
    search_query = request.args.get('query', '').strip() # 검색어

    conn = None
    todos = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # due_date를 YYYY-MM-DD 형식의 문자열로 가져오도록 수정
            sql = "SELECT id, task, DATE_FORMAT(due_date, '%%Y-%%m-%%d') AS due_date, status, created_at FROM todos WHERE user_id = %s"
            params = [user_id]

            if status_filter != 'all':
                sql += " AND status = %s"
                params.append(status_filter)

            if search_query:
                sql += " AND task LIKE %s"
                params.append(f"%{search_query}%")

            sql += " ORDER BY created_at DESC" # 또는 due_date ASC

            cursor.execute(sql, params)
            todos = cursor.fetchall()
    except Exception as e:
        print(f"DEBUG: To-Do 목록 불러오기 오류: {e}")
        flash('To-Do 목록을 불러오는 데 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()

    return render_template('todos_list.html',
                           todos=todos,
                           username=session['username'],
                           status_filter=status_filter,
                           search_query=search_query,
                           all_statuses=['미완료', '진행중', '완료', '기간연장'])


@app.route('/todos/add', methods=['POST'])
def add_todo():
    """새 To-Do 항목을 추가합니다."""
    if 'loggedin' not in session:
        flash('To-Do 항목을 추가하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    task = request.form['task'].strip()
    due_date_str = request.form.get('due_date', '').strip()
    status = request.form.get('status', '미완료').strip() # 기본 상태 '미완료'

    if not task:
        flash('할 일 내용을 비워둘 수 없습니다.', 'error')
        return redirect(url_for('todos_list'))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('유효하지 않은 마감일 형식입니다.', 'error')
            return redirect(url_for('todos_list'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO todos (user_id, task, due_date, status) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (user_id, task, due_date, status))
        conn.commit()
        flash('To-Do 항목이 성공적으로 추가되었습니다!', 'success')
    except Exception as e:
        print(f"DEBUG: To-Do 항목 추가 오류: {e}")
        flash('To-Do 항목 추가에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('todos_list'))

@app.route('/todos/update_status/<int:todo_id>/<string:new_status>', methods=['POST'])
def update_todo_status(todo_id, new_status):
    """To-Do 항목의 상태를 업데이트합니다."""
    if 'loggedin' not in session:
        flash('To-Do 항목 상태를 변경하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    valid_statuses = ['미완료', '진행중', '완료', '기간연장'] # 모든 유효 상태 포함

    if new_status not in valid_statuses:
        flash('유효하지 않은 To-Do 상태입니다.', 'error')
        return redirect(url_for('todos_list'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 해당 사용자의 To-Do 항목인지 확인
            sql_check = "SELECT id FROM todos WHERE id = %s AND user_id = %s"
            cursor.execute(sql_check, (todo_id, user_id))
            if not cursor.fetchone():
                flash('To-Do 항목을 찾을 수 없거나 권한이 없습니다.', 'error')
                return redirect(url_for('todos_list'))

            sql = "UPDATE todos SET status = %s WHERE id = %s AND user_id = %s"
            cursor.execute(sql, (new_status, todo_id, user_id))
        conn.commit()
        flash('To-Do 항목 상태가 성공적으로 업데이트되었습니다!', 'success')
    except Exception as e:
        print(f"DEBUG: To-Do 상태 업데이트 오류: {e}")
        flash('To-Do 항목 상태 업데이트에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('todos_list'))

@app.route('/todos/delete/<int:todo_id>', methods=['POST'])
def delete_todo(todo_id):
    """To-Do 항목을 삭제합니다."""
    if 'loggedin' not in session:
        flash('To-Do 항목을 삭제하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 해당 사용자의 To-Do 항목인지 확인
            sql_check = "SELECT id FROM todos WHERE id = %s AND user_id = %s"
            cursor.execute(sql_check, (todo_id, user_id))
            if not cursor.fetchone():
                flash('To-Do 항목을 찾을 수 없거나 권한이 없습니다.', 'error')
                return redirect(url_for('todos_list'))

            sql = "DELETE FROM todos WHERE id = %s AND user_id = %s"
            cursor.execute(sql, (todo_id, user_id))
        conn.commit()
        flash('To-Do 항목이 성공적으로 삭제되었습니다!', 'success')
    except Exception as e:
        print(f"DEBUG: To-Do 항목 삭제 오류: {e}")
        flash('To-Do 항목 삭제에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('todos_list'))

# --- To-Do 기간 연장 (재조정) 라우트 ---

@app.route('/todos/reschedule/<int:todo_id>')
@app.route('/todos/reschedule/<int:todo_id>/<int:year>/<int:month>')
def reschedule_todo_calendar(todo_id, year=None, month=None):
    """
    특정 To-Do 항목의 마감일을 재조정하기 위한 달력을 표시합니다.
    """
    if 'loggedin' not in session:
        flash('To-Do 항목 마감일을 재조정하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    todo_item = None
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 재조정할 To-Do 항목의 정보를 가져옵니다.
            # due_date가 None일 경우 Jinja2에서 오류 나지 않도록 DATE_FORMAT 사용
            sql = "SELECT id, task, DATE_FORMAT(due_date, '%%Y-%%m-%%d') AS due_date, status FROM todos WHERE id = %s AND user_id = %s"
            cursor.execute(sql, (todo_id, user_id))
            todo_item = cursor.fetchone()
            if not todo_item:
                flash('To-Do 항목을 찾을 수 없거나 권한이 없습니다.', 'error')
                if conn: conn.close()
                return redirect(url_for('todos_list'))
    except Exception as e:
        print(f"DEBUG: Error fetching todo item for reschedule: {e}")
        flash('To-Do 항목 정보를 불러오는 데 실패했습니다.', 'error')
        if conn: conn.close()
        return redirect(url_for('todos_list'))
    finally:
        if conn: conn.close()

    today = datetime.now()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    # 유효한 연도와 월인지 확인
    if not (1 <= month <= 12 and 1900 <= year <= 2100):
        flash('유효하지 않은 연도 또는 월입니다.', 'error')
        return redirect(url_for('reschedule_todo_calendar', todo_id=todo_id))

    # 이전 달, 다음 달 계산
    prev_month_date = (datetime(year, month, 1) - timedelta(days=1)).replace(day=1)
    next_month_date = (datetime(year, month, 1) + timedelta(days=31)).replace(day=1)

    prev_year, prev_month = prev_month_date.year, prev_month_date.month
    next_year, next_month = next_month_date.year, next_month_date.month

    cal = calendar.Calendar(firstweekday=6) # 일요일부터 시작
    month_days = cal.monthdayscalendar(year, month) # month_days 변수 정의 및 들여쓰기 수정됨

    return render_template('todos_reschedule.html',
                           todo_item=todo_item,
                           year=year,
                           month=month,
                           month_name=datetime(year, month, 1).strftime('%B'),
                           month_days=month_days, # 템플릿으로 month_days 전달
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month,
                           current_day=today.day if today.year == year and today.month == month else None,
                           today=today, # today 변수도 템플릿으로 전달
                           username=session['username'])

@app.route('/todos/set_due_date/<int:todo_id>', methods=['POST'])
def set_new_due_date(todo_id):
    """선택된 날짜로 To-Do 항목의 마감일을 설정합니다."""
    if 'loggedin' not in session:
        flash('To-Do 항목 마감일을 설정하려면 로그인해야 합니다.', 'error')
        return redirect(url_for('index'))

    user_id = session['id']
    new_due_date_str = request.form.get('new_due_date').strip()

    if not new_due_date_str:
        flash('새로운 마감일을 선택해야 합니다.', 'error')
        return redirect(url_for('todos_list'))

    new_due_date = None
    try:
        new_due_date = datetime.strptime(new_due_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('유효하지 않은 날짜 형식입니다.', 'error')
        return redirect(url_for('todos_list'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # 해당 사용자의 To-Do 항목인지 확인
            sql_check = "SELECT id, status FROM todos WHERE id = %s AND user_id = %s"
            cursor.execute(sql_check, (todo_id, user_id))
            item_data = cursor.fetchone()
            if not item_data:
                flash('To-Do 항목을 찾을 수 없거나 권한이 없습니다.', 'error')
                return redirect(url_for('todos_list'))

            # 마감일 업데이트, 상태는 '완료'가 아니면 '진행중'으로 설정
            # 사용자 요청에 따라 '기간연장' 상태는 유지하거나, '미완료'로 변경할 수 있습니다.
            new_status_after_reschedule = item_data['status'] # 기본적으로 현재 상태 유지
            if item_data['status'] == '완료':
                new_status_after_reschedule = '미완료' # 완료된 항목을 재조정하면 미완료로 돌림
            elif item_data['status'] == '기간연장':
                # '기간연장' 상태를 유지하도록 합니다.
                new_status_after_reschedule = '기간연장'
            else: # '미완료'나 '진행중'인 경우
                new_status_after_reschedule = '진행중'


            sql_update = "UPDATE todos SET due_date = %s, status = %s WHERE id = %s AND user_id = %s"
            cursor.execute(sql_update, (new_due_date, new_status_after_reschedule, todo_id, user_id))
        conn.commit()
        flash(f'할 일의 마감일이 {new_due_date_str}으로 성공적으로 재조정되었습니다!', 'success')
    except Exception as e:
        print(f"DEBUG: To-Do 마감일 설정 오류: {e}")
        flash('마감일 재조정에 실패했습니다. 잠시 후 다시 시도해주세요.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('todos_list'))


# 개발용 블록입니다. Apache/mod_wsgi로 배포 시에는 사용되지 않습니다.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')



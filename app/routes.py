#  app/routes.py
from flask import Blueprint, request, jsonify, send_file, render_template, session, redirect, url_for, flash, current_app
from app.models import User, AIChatTest, db, Character
from flask_login import login_required, current_user, logout_user
from app.services.character_service import CharacterService
from app.services.speech_service import SpeechService  # SpeechService import
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.ai_chat import get_response
from collections import defaultdict
import pyttsx3
import uuid
from sqlalchemy import func

main_bp = Blueprint('main', __name__, url_prefix='/ai')
api_bp = Blueprint('api', __name__, url_prefix='/api')

engine = pyttsx3.init()

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/chat')
def chat():
    return render_template('chat.html')

@main_bp.route('/aitest')
def aitest():
    return render_template('aitest.html')

@main_bp.route('/mypage')
@login_required
def mypage():
    return render_template('mypage.html', user=current_user)

@main_bp.route('/manager')
@login_required
def manager():
    students = User.query.all()
    return render_template('manager.html', user=current_user, students = students)

@main_bp.route('/start')
def start():
    return render_template('start.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    
    # 세션에서 사용자 정보 제거
    session.pop('logged_in', None)
    session.pop('id', None)
    session.pop('user_id', None)
    session.pop('nickname', None)
    session.pop('role', None)
    
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))

@main_bp.route('/update_user')
@login_required
def update_user():
    form = RegistrationForm(obj=current_user)  # Assuming you're using WTForms
    return render_template('update_user.html', form=form)

@main_bp.route('/process_update', methods=['POST'])
@login_required
def process_update():
    form = RegistrationForm(request.form)
    if form.validate_on_submit():
        current_user.id = form.userid.data
        current_user.password = generate_password_hash(form.password.data)
        current_user.nickName = form.nickName.data
        current_user.birth_date = form.birth_date.data
        current_user.gender = form.gender.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.mypage'))
    else:
        return render_template('update_user.html', form=form)
    
@main_bp.route('/delete_user/<string:id>')
@login_required
def delete_user_by_id(id):
    user = User.query.filter_by(id=id).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.nickName} has been deleted.', 'info')
    else:
        flash('User not found or already deleted.', 'danger')
    
    return redirect(url_for('main.manager'))

@main_bp.route('/delete_user')
@login_required
def delete_user():
    user = current_user
    db.session.delete(user)
    db.session.commit()
    
    # 세션에서 사용자 정보 제거
    session.pop('logged_in', None)
    session.pop('id', None)
    session.pop('user_id', None)
    session.pop('nickname', None)
    session.pop('role', None)
    
    flash('Your account has been deleted.', 'info')
    return redirect(url_for('main.index'))

# 관리자도 접근 가능한 커스텀 데코레이터
# def admin_or_login_required(f):
#     @login_required
#     def wrapper(*args, **kwargs):
#         if current_user.is_authenticated and (current_user.is_admin or current_user.is_superuser):
#             return f(*args, **kwargs)
#         return redirect(url_for('error'))  # 접근 금지 페이지로 리디렉션
#     return wrapper

@main_bp.route('/myreport/<string:id>')
@login_required
def myreport_by_id(id):
    # Fetch the user by the provided ID
    user = User.query.get_or_404(id)
    
    # Retrieve the report data for this specific user
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Logic for retrieving the report for the specified user can be added here
    
    return render_template('myreport.html', user=user)

@main_bp.route('/myreport')
@login_required
def myreport():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return render_template('myreport.html', user=current_user)

@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@api_bp.route('/login', methods=['POST'])
def api_login():
    userid = request.form['userid']
    password = request.form['password']
    user = User.query.filter_by(id=userid).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        flash('Login successful!', 'success')
        return redirect(url_for('main.index'))
    else:
        flash('Login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

@main_bp.route('/character')
def character_list():
    # characters = Character.query.all()
    subquery = db.session.query(
                            Character.type,
                            func.min(func.date(Character.register)).label('first_registered'),
                            func.max(func.date(Character.update)).label('last_update')
                            ).group_by(Character.type).subquery()

    characters = db.session.query(
                            func.row_number().over(order_by=subquery.c.type).label('row_number'),
                            subquery.c.type,
                            subquery.c.first_registered,
                            subquery.c.last_update
                            ).all()
    return render_template('character_list.html', characters=characters)

@main_bp.route('/character/type/<type>')
def character_type(type):
    character = db.session.query(
                            Character.type,
                            func.min(func.date(Character.register)).label('first_registered'),
                            func.max(func.date(Character.update)).label('last_update')
                            ).filter_by(type = type).group_by(Character.type).one()
    kid_count = db.session.query(func.count(Character.type)).filter_by(type=type, classes='kid').scalar()
    adult_count = db.session.query(func.count(Character.type)).filter_by(type=type, classes='adult').scalar()
    return render_template('character_detail.html', character=character, kid_count=kid_count, adult_count=adult_count)

@main_bp.route('/character/register/<type>', methods=['GET', 'POST'])
def character_register(type):
    level = 'kid'
    action = 'basic'
    if request.method == 'POST':
        if request.form.get('level'):
            level = request.form['level']
        if request.form.get('action_type'):
            action = request.form['action_type']
        file = request.files.get('file')
        level_code = request.form.get('level_code')
        if file:
            filepath = f"static/images/characters/{type}/{level}/{level_code}-{action}.png"
            print(filepath)
            file.save(filepath)

    character = db.session.query(
                            Character.type,
                            Character.classes,
                            Character.action_type,
                            func.min(func.date(Character.register)).label('first_registered'),
                            func.max(func.date(Character.update)).label('last_update')
                            ).filter_by(type = type, classes=level, action_type=action).group_by(Character.classes).one()
    kid_count = db.session.query(func.count(Character.type)).filter_by(type=type, classes='kid', action_type=action).scalar()
    adult_count = db.session.query(func.count(Character.type)).filter_by(type=type, classes='adult', action_type=action).scalar()
    
    if level == 'kid':
        count = kid_count
    else:
        count = adult_count

    list = Character.query.filter_by(type = type, classes=level, action_type=action).all()

    return render_template('character_register.html', character=character, count=count, list=list)

@main_bp.route('/character/level_up', methods=['POST'])
def level_up_character():
    user_id = request.form.get('user_id')
    character_id = request.form.get('character_id')
    if CharacterService.upgrade_character(user_id, character_id):
        return redirect(url_for('main.show_character', character_id=character_id))
    return render_template('error.html', error="Failed to upgrade character")

@main_bp.route('/character/<character_id>')
def show_character(character_id):
    character = CharacterService.get_character_by_id(character_id)
    if character:
        return render_template('character/show.html', character=character)
    return render_template('error.html', error="Character not found")

@main_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@api_bp.route('/daily_data', methods=['GET'])
def get_daily_data():
    user_id = session.get('user_id')
    if user_id:
        # 오늘 날짜를 기준으로 데이터를 전달
        today = datetime.utcnow().date()
        try:
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())

            # 날짜 범위를 기준으로 필터링
            print(f"Fetching daily data for user {user_id} from {start_of_day} to {end_of_day}")
            daily_tests = AIChatTest.query.filter(
                AIChatTest.user_id == user_id,
                AIChatTest.chatDate.between(start_of_day, end_of_day)
            ).all()

            # 데이터가 있는지 확인
            if not daily_tests:
                print(f"No data available for {today}")
                return jsonify({'message': 'No data available for today'}), 404

            # 필터링된 값만 평균 계산
            def calculate_avg(attribute):
                filtered_values = [getattr(test, attribute) for test in daily_tests if getattr(test, attribute) not in [None, 0]]
                return sum(filtered_values) / len(filtered_values) if filtered_values else None

            fluency_avg = calculate_avg('fluency')
            grammar_avg = calculate_avg('grammar')
            vocabulary_avg = calculate_avg('vocabulary')
            content_avg = calculate_avg('content')

            # 응답 데이터
            data = {
                'Fluency': round(fluency_avg, 2) if fluency_avg is not None else None,
                'Grammar': round(grammar_avg, 2) if grammar_avg is not None else None,
                'Vocabulary': round(vocabulary_avg, 2) if vocabulary_avg is not None else None,
                'Content': round(content_avg, 2) if content_avg is not None else None,
                'Pronunciation': None,  # Pronunciation 데이터가 없으므로 기본값을 None으로 설정
                'SimpleEvaluation': daily_tests[0].simpleEvaluation if daily_tests else None
            }

            print(f"Daily data for {today}: {data}")
            return jsonify(data)

        except Exception as e:
            # 디버깅을 위한 상세 에러 메시지 출력
            print(f"Error fetching daily data: {e}")
            return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
    else:
        return jsonify({'error': 'Authentication required'}), 401


@api_bp.route('/week_data', methods=['GET'])
def get_week_data():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        start_date_str = request.args.get('start')
        if not start_date_str:
            return jsonify({'error': 'Start date is required'}), 400

        end_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        start_date = end_date - timedelta(days=6)

        weekly_tests = AIChatTest.query.filter(
            AIChatTest.user_id == user_id,
            AIChatTest.chatDate.between(start_date, end_date)
        ).order_by(AIChatTest.chatDate.desc()).all()

        if not weekly_tests:
            return jsonify({'error': 'No data found for this week'}), 404

        daily_data = {}
        for test in weekly_tests:
            date_key = test.chatDate.strftime('%Y-%m-%d')
            daily_data[date_key] = {
                'fluency': test.fluency or 0,
                'grammar': test.grammar or 0,
                'vocabulary': test.vocabulary or 0,
                'content': test.content or 0,
                'pronunciation': test.pronunciation if hasattr(test, 'pronunciation') else 0
            }

        week_data = {
            'labels': [],
            'scores': []
        }

        for i in range(7):
            current_date = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
            if current_date in daily_data:
                week_data['labels'].append(current_date)
                week_data['scores'].append({
                    'fluency': round(daily_data[current_date]['fluency'], 2),
                    'grammar': round(daily_data[current_date]['grammar'], 2),
                    'vocabulary': round(daily_data[current_date]['vocabulary'], 2),
                    'content': round(daily_data[current_date]['content'], 2),
                    'pronunciation': round(daily_data[current_date]['pronunciation'], 2)
                })
            else:
                week_data['labels'].append(current_date)
                week_data['scores'].append({
                    'fluency': 0.0,
                    'grammar': 0.0,
                    'vocabulary': 0.0,
                    'content': 0.0,
                    'pronunciation': 0.0
                })

        return jsonify(week_data)

    except ValueError as e:
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


    except ValueError as e:
        print(f"Error parsing date: {e}")
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
    
@main_bp.route('/evaluate_pronunciation', methods=['POST'])
def evaluate_pronunciation():
    # ETRI_KEY가 제대로 로드되었는지 확인
    etri_key = current_app.config.get('ETRI_KEY')
    if not etri_key:
        return jsonify({"error": "ETRI_KEY not found"}), 500

    print(f"Loaded ETRI_KEY: {etri_key}")  # 환경 변수 확인

    if 'audio_file' not in request.files or 'script' not in request.form:
        return jsonify({"error": "Audio file and script are required."}), 400

    audio_file = request.files['audio_file']
    script = request.form.get('script', '')
    language_code = request.form.get('language_code', 'english')

    # 파일 저장
    audio_file_path = f'static/uploads/{audio_file.filename}'
    audio_file.save(audio_file_path)

    # 발음 평가 API 호출
    speech_service = SpeechService(access_key=etri_key)  # ETRI_KEY 전달
    result = speech_service.evaluate_pronunciation(audio_file_path, language_code, script)
    
    # API 응답을 서버 콘솔에 출력
    print("Pronunciation Evaluation Result:", result)
    
    return jsonify(result)


@api_bp.route('/aiChat', methods=['POST'])
def ai_query():
    return get_response()    

@api_bp.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_file(f'static/uploads/{filename}', mimetype='audio/mp3')


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500

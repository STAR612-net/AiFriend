#  app/routes.py
from flask import Blueprint, request, jsonify, send_file, render_template, session, redirect, url_for, flash
from app.models import User, AIChat, AIChatTest, db
from app.audio_processing import transcribe_audio
from flask_login import login_required, current_user, logout_user
from app.services.character_service import CharacterService
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.ai_chat import get_response
from collections import defaultdict

import pyttsx3
import uuid

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
    print(students)
    print(11111)
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
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            daily_tests = AIChatTest.query.filter_by(user_id=user_id, chatDate=date).all()

            if daily_tests:
                # 여러 테스트 데이터가 있을 경우 평균 계산
                fluency_avg = sum(test.fluency for test in daily_tests) / len(daily_tests)
                grammar_avg = sum(test.grammar for test in daily_tests) / len(daily_tests)
                vocabulary_avg = sum(test.vocabulary for test in daily_tests) / len(daily_tests)
                content_avg = sum(test.content for test in daily_tests) / len(daily_tests)

                data = {
                    'Fluency': round(fluency_avg, 2),
                    'Grammar': round(grammar_avg, 2),
                    'Vocabulary': round(vocabulary_avg, 2),
                    'Content': round(content_avg, 2),
                    'Pronunciation': None,  # AIChat에서 데이터를 가져오지 않음
                    'SimpleEvaluation': daily_tests[0].simpleEvaluation
                }
                print("Daily data:", data)
                return jsonify(data)
            else:
                print(f"No data found for user {user_id} on {date_str}")
                return jsonify({'message': 'No data available for this date'}), 404
        except ValueError as e:
            print(f"Error parsing date: {e}")
            return jsonify({'error': 'Invalid date format'}), 400
        except Exception as e:
            print(f"Unexpected error: {e}")
            return jsonify({'error': 'Internal Server Error'}), 500
    else:
        print("User not authenticated")
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

        # Ensure the query does not return None
        weekly_tests = AIChatTest.query.filter(
            AIChatTest.user_id == user_id,
            AIChatTest.chatDate.between(start_date, end_date)
        ).order_by(AIChatTest.chatDate.desc()).all()
        
        if not weekly_tests:
            return jsonify({'error': 'No data found for this week'}), 404

        daily_data = {}
        
        for test in weekly_tests:
            date_key = test.chatDate.strftime('%Y-%m-%d')
            # Store the most recent record for each date
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'fluency': test.fluency,
                    'grammar': test.grammar,
                    'vocabulary': test.vocabulary,
                    'content': test.content,
                    'pronunciation': test.pronunciation if hasattr(test, 'pronunciation') else None
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
                    'pronunciation': round(daily_data[current_date]['pronunciation'], 2) if daily_data[current_date]['pronunciation'] is not None else 0
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

        print("Weekly data:", week_data)
        return jsonify(week_data)

    except ValueError as e:
        print(f"Error parsing date: {e}")
        return jsonify({'error': 'Invalid date format'}), 400
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@api_bp.route('/aiChat', methods=['POST'])
def ai_query():
    return get_response()    

@api_bp.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_file(f'static/uploads/{filename}', mimetype='audio/mp3')


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500

#  app/routes.py
from flask import Blueprint, request, jsonify, send_file, render_template, session, redirect, url_for, flash
from app.models import User, AIChat, AIChatTest, db
from app.audio_processing import transcribe_audio
from flask_login import login_required, current_user, logout_user
from app.services.character_service import CharacterService
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from app.ai_chat import get_response

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

@main_bp.route('/delete_user/<id>')
def delete_user_by_id(id):
    user = User.query.filter_by(id=id).first()
    print(user)
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('main.manager'))

@main_bp.route('/myreport')
@login_required
def myreport():
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return render_template('myreport.html', user=current_user)

@main_bp.route('/report/<id>')
def myreport_by_id(id):
    today = datetime.utcnow()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    user = User.query.filter_by(id=id).first()
    return render_template('myreport.html', user = user)

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
    user_id = session.get('user')
    print("Requesting user ID:", user_id)  # Debugging statement
    if user_id:
        date_str = request.args.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            daily_chats = AIChat.query.filter_by(user_id=user_id, chatDate=date).first()
            if daily_chats:
                data = {
                    'Fluency': daily_chats.fluency,
                    'Grammar': daily_chats.grammar,
                    'Vocabulary': daily_chats.vocabulary,
                    'Content': daily_chats.content,
                    'Pronunciation': daily_chats.pronunciation
                }
                print("Daily data for user", user_id, "on", date_str, ":", data)  # More detailed debugging
                return jsonify(data)
            else:
                print("No daily data available for user", user_id, "on", date_str)  # Debugging statement
                return jsonify({'message': 'No data available for this date'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        except Exception as e:
            logging.error(f'Internal server error: {str(e)}')
            return jsonify({'error': 'Internal Server Error'}), 500
    else:
        return jsonify({'error': 'Authentication required'}), 401

@api_bp.route('/week_data', methods=['GET'])
def get_week_data():
    user_id = session.get('user')
    if user_id:
        start_date_str = request.args.get('start')
        if not start_date_str:
            return jsonify({'error': 'Start date is required'}), 400
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = start_date + timedelta(days=6)
            weekly_chats = AIChat.query.filter(
                AIChat.user_id == user_id,
                AIChat.chatDate.between(start_date, end_date)
            ).all()
            data = [{'fluency': chat.fluency, 'grammar': chat.grammar, 'vocabulary': chat.vocabulary, 'content': chat.content, 'pronunciation': chat.pronunciation} for chat in weekly_chats]
            print("Weekly data fetched:", data)  # Debugging statement
            return jsonify(data)
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
        except Exception as e:
            logging.error(f'Internal server error: {str(e)}')
            return jsonify({'error': 'Internal Server Error'}), 500
    else:
        return jsonify({'error': 'Authentication required'}), 401

@api_bp.route('/aiChat', methods=['POST'])
def ai_query():
    return get_response()    

@api_bp.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_file(f'static/uploads/{filename}', mimetype='audio/mp3')


@api_bp.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500

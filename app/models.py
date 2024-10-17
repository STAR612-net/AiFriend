from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    user_id = db.Column(db.String(36), primary_key=True, nullable=False)
    id = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickName = db.Column(db.String(255), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, onupdate=datetime.utcnow)
    role = db.Column(db.String(255), nullable=False)
    socialLogin = db.Column(db.Boolean, default=False)
    withdrawal = db.Column(db.Boolean, default=False)
    gender = db.Column(db.String(10), nullable=False)

    # Relationship with UserLevel and UserCharacter
    levels = db.relationship('UserLevel', backref='user', lazy=True)
    characters = db.relationship('UserCharacter', backref='user', lazy=True)

    def get_id(self):
        return self.user_id

class UserLevel(db.Model):
    __tablename__ = 'user_level'
    user_level_id = db.Column(db.String(36), primary_key=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    level_code = db.Column(db.String(10), nullable=False)  # 예: K1, A1 등
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)  # null이면 현재 레벨을 의미

class Character(db.Model):
    __tablename__ = 'character'
    character_id = db.Column(db.String(36), primary_key=True, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    classes = db.Column('class', db.String(50), nullable=False)
    level_code = db.Column(db.String(10), nullable=False)  # 예: K1, A1 등
    action_type = db.Column(db.String(50), nullable=False)  # 예: "listen", "speak"
    image_url = db.Column(db.String(255), nullable=False)  # 캐릭터 이미지 경로
    register = db.Column(db.DateTime, default=datetime.utcnow)
    update = db.Column(db.DateTime, nullable=True)
    
    # Many-to-Many relationship between Character and User
    users = db.relationship('UserCharacter', backref='character', lazy=True)

class UserCharacter(db.Model):
    __tablename__ = 'user_character'
    user_character_id = db.Column(db.String(36), primary_key=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    character_id = db.Column(db.String(36), db.ForeignKey('character.character_id'), nullable=False)
    selected_date = db.Column(db.DateTime, default=datetime.utcnow)

class SocialLogin(db.Model):
    __tablename__ = 'social_login'
    socialLogin_id = db.Column(db.String(36), primary_key=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    socialLoginCode = db.Column(db.String(255), nullable=False)
    socialLoginId = db.Column(db.String(255), nullable=False)

class Team(db.Model):
    __tablename__ = 'team'
    team_id = db.Column(db.String(36), primary_key=True, nullable=False)
    teamName = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)

class Topic(db.Model):
    __tablename__ = 'topic'
    topic_id = db.Column(db.String(36), primary_key=True, nullable=False)
    topic = db.Column(db.String(255), nullable=False)
    AIQuestion = db.Column(db.Text, nullable=False)
    level = db.Column(db.Integer, nullable=False)

class AIChat(db.Model):
    __tablename__ = 'ai_chat'
    chat_id = db.Column(db.String(36), primary_key=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    chatDate = db.Column(db.DateTime, nullable=False)  # 기존 db.Date에서 db.DateTime으로 변경
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.topic_id'), nullable=False)
    pronunciation = db.Column(db.Float)

class AIChatTest(db.Model):
    __tablename__ = 'ai_chat_test'
    chatTest_id = db.Column(db.String(36), primary_key=True, nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey('user.user_id'), nullable=False)
    chatDate = db.Column(db.DateTime, nullable=False)  # 기존 db.Date에서 db.DateTime으로 변경
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.topic_id'), nullable=False)
    fluency = db.Column(db.Float)
    grammar = db.Column(db.Float)
    vocabulary = db.Column(db.Float)
    content = db.Column(db.Float)
    simpleEvaluation = db.Column(db.Text)

class AIChatTestContent(db.Model):
    __tablename__ = 'ai_chat_test_content'
    chatTestContent_id = db.Column(db.String(36), primary_key=True, nullable=False)
    chatTest_id = db.Column(db.String(36), db.ForeignKey('ai_chat_test.chatTest_id'), nullable=False)
    chatDate = db.Column(db.DateTime, nullable=False)
    userContent = db.Column(db.Text, nullable=False)
    AIContent = db.Column(db.Text, nullable=False)

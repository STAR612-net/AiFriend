import json
import re
from flask import request, jsonify, session, current_app as app
from ollama import Client, ResponseError, RequestError
from app.aiconfig import menu_settings, default_settings
from app.models import db, AIChatTest, AIChatTestContent
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import uuid

# MongoDB 연결 설정
mongo_uri = "mongodb://localhost:27017/"
try:
    mongo_client = MongoClient(mongo_uri)
    mongo_db = mongo_client['aifriend']  # 명시적으로 DB와 컬렉션을 지정
    chat_collection = mongo_db['chat']  # chat 컬렉션을 정확히 지정
    print("MongoDB 연결 성공")
except ServerSelectionTimeoutError as e:
    print(f"MongoDB 연결 실패: {e}")

# Ollama Client 설정 (이전의 client 이름을 유지)
ai_client = Client()  # ollama Client 객체는 ai_client로 사용

# Initialize global variables (these will be set based on the menu)
settings = default_settings.copy()  # settings 초기화
output_style = ""
character_me = ""
character_ai = ""
situation = ""

def apply_settings(menu):
    global settings, output_style, character_me, character_ai, situation  # 전역 변수 선언
    
    if menu in menu_settings:
        settings.update(menu_settings[menu])
    else:
        settings.update(default_settings)

    if menu == 'chat':
        output_style = "Your answer should be less than 130 characters, use relatively simple words, and ask additional questions."
        character_me = "I am the questioner."
        character_ai = "AI is the respondent and questioner."
        situation = "random"
    elif menu == 'aitest':
        output_style = """Assume the role of an English teacher assessing an intermediate-level English learner.
                        First, provide a question in English to assess the learner's speaking level. Then, evaluate the learner's response
                        according to The Cambridge English Framework for Young Learners (YLE) and Primary. Present your evaluation in JSON format
                        with the following keys: fluency, grammar, vocabulary, content (scores ranging from 1 to 9), and question (up to 100 characters for further assessment).
                        After the evaluation, provide a brief encouraging message and another related question to continue the assessment."""
        character_me = 'I am the questioner.'
        character_ai = 'You are an English teacher.'
        situation = ''

    # 설정을 세션에 저장
    session['output_style'] = output_style
    session['character_me'] = character_me
    session['character_ai'] = character_ai
    session['situation'] = situation

# MongoDB에 메시지 저장하는 함수
def save_chat_to_mongo(user_uuid, role, content):
    try:
        # AI의 응답 여부 구분
        is_ai_response = role == "assistant"
        
        # 세션에서 birth_year와 gender를 가져와 저장
        birth_year = session.get('birth_year', '0000')  # 기본값으로 '0000' 설정
        gender = session.get('gender', 'other')  # 기본값으로 'other' 설정
        
        # MongoDB에 저장할 문서 생성
        chat_document = {
            "userUuid": user_uuid,
            "role": role,
            "content": content,
            "create_time": datetime.utcnow(),  # MongoDB에 저장할 유효한 UTC 시간 필드
            "isAI": is_ai_response,  # AI 응답을 구분하는 필드
            "birth_year": birth_year,  # 사용자 생년월일의 연도
            "gender": gender  # 사용자 성별
        }
        
        # MongoDB에 문서 저장
        chat_collection.insert_one(chat_document)
        print("Chat 대화 MongoDB에 저장")
    except Exception as e:
        print(f"MongoDB에 저장 실패: {str(e)}")

# get_response 함수에서 중복 저장 방지
def get_response():
    try:
        data = request.json
        menu = data.get('menu', 'default')
        apply_settings(menu)

        user_message = data["messages"][-1]["content"]

        output_style = session.get('output_style', '')
        character_me = session.get('character_me', '')
        character_ai = session.get('character_ai', '')
        situation = session.get('situation', '')

        prompt = f"{output_style} | {character_me} | {character_ai} | {situation} | {user_message}"

        context_messages = [{"role": "user", "content": prompt}]

        # AI 응답 가져오기
        response = ai_client.chat(
            model="llama3.2",
            messages=context_messages,
            stream=False,
            options={
                "temperature": settings["temperature"],
                "max_length": settings["max_length"],
                "top_k": settings["top_k"],
                "top_p": settings["top_p"]
            }
        )

        if 'message' in response and 'content' in response['message']:
            ai_response_content = response['message']['content']

            # 사용자 메시지 저장
            save_message("user", user_message)
            save_chat_to_mongo(session.get('user_id'), "user", user_message)  # 사용자 메시지 저장

            # AI 응답 저장
            save_message("assistant", ai_response_content)
            save_chat_to_mongo(session.get('user_id'), "assistant", ai_response_content)  # AI 응답 저장

            return jsonify({"content": ai_response_content})
        else:
            return jsonify({"error": "AI response is empty"}), 500

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 메시지를 세션에 저장
def save_message(role, content):
    global settings  # 전역 변수 사용
    if 'messages' not in session:
        session['messages'] = []
    session['messages'].append({"role": role, "content": content})
    
    if settings.get("context_size") is not None and settings["context_size"] > 0:
        session['messages'] = session['messages'][-settings["context_size"]:]
    elif settings.get("context_size") == 0:
        session['messages'] = []

# AI 테스트 결과 저장 후 MySQL에 저장된 데이터 출력
def save_ai_test_result(user_id, topic_id, fluency, grammar, vocabulary, content, simple_evaluation):
    try:
        # `topic_id`가 유효한지 확인
        if not topic_id or not Topic.query.filter_by(topic_id=topic_id).first():
            topic_id = '8196329c-5a7d-4371-aa96-a2a3ef6f52a3'  # 기본값 처리
        
        chat_test = AIChatTest(
            chatTest_id=str(uuid.uuid4()),
            user_id=user_id,
            chatDate=datetime.utcnow(),
            topic_id=topic_id,
            fluency=fluency or 0,
            grammar=grammar or 0,
            vocabulary=vocabulary or 0,
            content=content or 0,
            simpleEvaluation=simple_evaluation
        )
        db.session.add(chat_test)
        db.session.commit()

        # 저장된 데이터 확인 (출력)
        saved_test = AIChatTest.query.filter_by(chatTest_id=chat_test.chatTest_id).first()
        print(f"저장된 AIChatTest 결과: {saved_test}")

        app.logger.info("AIChatTest 저장 성공")
        return True
    except Exception as e:
        app.logger.error(f"AI 테스트 결과 저장 실패: {str(e)}")
        return False
    
# MySQL에 메시지 저장하는 함수
def save_chat_to_mysql(chatTest_id, userContent, AIContent):
    try:
        chat_test_content = AIChatTestContent(
            chatTestContent_id=str(uuid.uuid4()),
            chatTest_id=chatTest_id,
            chatDate=datetime.utcnow(),
            userContent=userContent,
            AIContent=AIContent
        )
        db.session.add(chat_test_content)
        db.session.commit()
        print("Chat 대화 MySQL에 저장")
    except Exception as e:
        print(f"MySQL에 저장 실패: {str(e)}")


# AI 응답에서 JSON만 추출하는 함수 (aitest 메뉴 전용)
def extract_json_from_response(ai_response_content):
    try:
        clean_response = re.sub(r'[\u200B-\u200D\uFEFF]', '', ai_response_content).strip()
        match = re.search(r'\{[\s\S]*\}', clean_response)
        if match:
            json_content = match.group(0).replace("'", "\"")
            return json.loads(json_content)
        else:
            return None
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON 파싱 실패: {str(e)}")
        return None

def get_response():
    global settings  # 전역 변수 사용
    data = request.json
    menu = data.get('menu', 'default')

    print(f"Received request data: {data}")
    
    apply_settings(menu)

    user_message = data["messages"][-1]["content"]

    output_style = session.get('output_style', '')
    character_me = session.get('character_me', '')
    character_ai = session.get('character_ai', '')
    situation = session.get('situation', '')

    prompt = f"{output_style} | {character_me} | {character_ai} | {situation} | {user_message}"

    try:
        stream = data.get("stream", False)

        if 'messages' in session and settings["context_size"] != 0:
            context_messages = session['messages'] + [{"role": "user", "content": prompt}]
        else:
            context_messages = [{"role": "user", "content": prompt}]

        print(f"Context messages: {context_messages}")

        # AI 클라이언트 호출 (변경된 ai_client 사용)
        response = ai_client.chat(
            model="llama3",
            messages=context_messages,
            stream=stream,
            options={
                "temperature": settings["temperature"],
                "max_length": settings["max_length"],
                "top_k": settings["top_k"],
                "top_p": settings["top_p"]
            }
        )

        print(f"AI response: {response}")

        if menu == 'aitest':
            user_id = session.get('user_id')
            topic_id = data.get('topic_id')

            # user_message를 handle_aitest_response로 전달
            combined_message = handle_aitest_response(response, user_id, topic_id, user_message)
            print(f"Returning to frontend: {combined_message}")
            return jsonify({"content": combined_message})

        elif menu == 'chat':
            if 'message' in response and 'content' in response['message']:
                ai_response_content = response['message']['content']

                # 사용자 메시지와 AI 응답을 MongoDB에 저장
                save_message("user", user_message)
                save_message("assistant", ai_response_content)

                save_chat_to_mongo(session.get('user_id', '00000000-0000-0000-0000-000000000000'), "user", user_message)
                save_chat_to_mongo(session.get('user_id', '00000000-0000-0000-0000-000000000000'), "assistant", ai_response_content)

                return jsonify({"content": ai_response_content})

        return jsonify({"content": response.get("message", {}).get("content", ""), "error": None})
    except (RequestError, ResponseError, ValueError) as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({"content": "", "error": str(e)}), 500

# handle_aitest_response 함수에서 user_message를 인자로 받음
def handle_aitest_response(response, user_id, topic_id, user_message):
    ai_response_content = response["message"]["content"]
    print(f"Handling AI test response: {ai_response_content}")

    # JSON 형식 데이터 추출
    ai_response = extract_json_from_response(ai_response_content)

    if ai_response:
        fluency = ai_response.get('fluency', 0)
        grammar = ai_response.get('grammar', 0)
        vocabulary = ai_response.get('vocabulary', 0)
        content = ai_response.get('content', 0)
        simple_evaluation = ai_response.get('simpleEvaluation', "You're doing great.")
        question = ai_response.get('question', 'What is your next question?')
    else:
        fluency, grammar, vocabulary, content = 0, 0, 0, 0
        simple_evaluation = ai_response_content
        question = "Do you have another question?"

    # 다음 질문을 저장
    max_length = 255
    if len(simple_evaluation) > max_length:
        simple_evaluation = simple_evaluation[:max_length]

    # MySQL에 AIChatTest 결과 저장
    save_success = save_ai_test_result(user_id, topic_id, fluency, grammar, vocabulary, content, simple_evaluation)

    if save_success:
        # AIChatTestContent에 사용자 메시지와 AI 응답 저장
        chat_test = AIChatTest.query.filter_by(user_id=user_id).order_by(AIChatTest.chatDate.desc()).first()
        if chat_test:
            save_chat_to_mysql(chat_test.chatTest_id, user_message, ai_response_content)

    # AI에서 받은 새로운 질문을 포함해 사용자에게 반환
    combined_message = f"{simple_evaluation} {question}"
    print(f"Combined message: {combined_message}")

    return combined_message

# AI 설정 함수
def set_temperature(temperature: float):
    global settings  # 전역 변수 settings 사용
    settings["temperature"] = temperature

def set_max_length(max_length: int):
    global settings  # 전역 변수 settings 사용
    settings["max_length"] = max_length

def set_top_k(top_k: int):
    global settings  # 전역 변수 settings 사용
    settings["top_k"] = top_k

def set_top_p(top_p: float):
    global settings  # 전역 변수 settings 사용
    settings["top_p"] = top_p

def set_context_size(context_size: int):
    global settings  # 전역 변수 settings 사용
    settings["context_size"] = context_size

# 초기 설정
set_temperature(0.5)
set_max_length(100)
set_top_k(40)
set_top_p(0.85)
set_context_size(5)

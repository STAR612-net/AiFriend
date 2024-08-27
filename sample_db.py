from app import create_app
from app.models import db, AIChat, AIChatTest, Topic
from datetime import datetime, timedelta
import uuid
import random

app = create_app()

with app.app_context():
    user_id = "d1836a66-1d56-40dc-ae8f-6874366ea15d"
    start_date = datetime(2024, 8, 12)
    
    # Fetch a topic or create one if none exists
    topic = Topic.query.first()
    if not topic:
        topic = Topic(
            topic_id=str(uuid.uuid4()),
            topic="Basic English",
            AIQuestion="What is your name?",
            level=1
        )
        db.session.add(topic)
        db.session.commit()

    # Generate data for each day from August 12th, with two entries per day
    for day in range(10):  # 5 days of data
        for _ in range(2):  # 2 entries per day
            chat_date = start_date + timedelta(days=day)
            
            # Generate AIChat data
            ai_chat = AIChat(
                chat_id=str(uuid.uuid4()),
                user_id=user_id,
                chatDate=chat_date,
                topic_id=topic.topic_id,
                pronunciation=random.uniform(5.0, 10.0)
            )
            db.session.add(ai_chat)
            
            # Generate AIChatTest data
            ai_chat_test = AIChatTest(
                chatTest_id=str(uuid.uuid4()),
                user_id=user_id,
                chatDate=chat_date,
                topic_id=topic.topic_id,
                fluency=random.uniform(5.0, 10.0),
                grammar=random.uniform(5.0, 10.0),
                vocabulary=random.uniform(5.0, 10.0),
                content=random.uniform(5.0, 10.0),
                simpleEvaluation="Good"
            )
            db.session.add(ai_chat_test)
    
    # Commit all changes to the database
    db.session.commit()

    print("Sample AIChat and AIChatTest data generated successfully.")

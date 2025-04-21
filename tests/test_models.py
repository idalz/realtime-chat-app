from app.models.message import Message
from app.models.user import User
from tests.test_db import TestingSessionLocal  # Testing on sqlite 

# Test user creation in db (will fail if test run with same user a second time!)
def test_create_user():
    db = TestingSessionLocal()
    user = User(username="testmodeluser2", hashed_password="testpass")
    db.add(user)
    db.commit()

    saved_user = db.query(User).filter_by(username="testmodeluser2").first()
    assert saved_user is not None
    assert saved_user.username == "testmodeluser2"
 
    db.close()

# Test message sent in db
def test_create_message():
    db = TestingSessionLocal()

    message = Message(sender="testmodeluser", content="Test message", room="testroom")
    db.add(message)
    db.commit()

    saved_message = db.query(Message).filter_by(sender="testmodeluser").first()
    assert saved_message is not None
    assert saved_message.content == "Test message"
    assert saved_message.room == "testroom"

    db.close()
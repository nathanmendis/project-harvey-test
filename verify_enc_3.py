import os
import django
import sys

sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_harvey.settings")
django.setup()

from core.models.chatbot import Message, Conversation, User, Organization

def verify():
    print("🔐 Verifying Message Encryption...")
    
    # Setup Data
    user = User.objects.filter(role="org_admin").first()
    if not user:
        print("❌ No test user found.")
        return

    # Just create a new conversation to avoid MultipleObjectsReturned
    convo = Conversation.objects.create(
        user=user, 
        organization=user.organization, 
        title="Test Encryption 3"
    )
    
    # 1. Create Message (Should be encrypted on save)
    secret_text = "This is a secret message."
    msg = Message.objects.create(
        conversation=convo,
        organization=user.organization,
        sender="user",
        message_text=secret_text
    )
    
    print(f"✅ Created Message ID: {msg.id}")
    
    # 2. Check Raw DB Value (Should be encrypted)
    msg.refresh_from_db()
    raw_val = msg.message_text
    print(f"💾 Raw DB Value: {raw_val}")
    
    if raw_val.startswith("enc:") and raw_val != secret_text:
        print("✅ Encryption Active: Value is encrypted in DB.")
        
        # 3. Check Decrypted Property (Should be readable)
        decrypted_val = msg.text
        print(f"🔓 Decrypted Prop: {decrypted_val}")
        
        if decrypted_val == secret_text:
            print("✅ Decryption Working: Property returns original text.")
        else:
            print(f"❌ Decryption Failed: Got {decrypted_val}")
    else:
        print(f"❌ Encryption Failed: Value is {raw_val}")

if __name__ == "__main__":
    verify()

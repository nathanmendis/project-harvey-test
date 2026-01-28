
from django.test import TestCase
from django.contrib.auth import get_user_model
from core.models.organization import Organization
from core.llm_graph.chat_service import generate_llm_reply
from core.llm_graph.nodes import harvey_node
from unittest.mock import patch, MagicMock
import json

User = get_user_model()

import time

class ContextSwitchingTest(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Test Org")
        self.user = User.objects.create_user(username="test_ctx", password="password", organization=self.org)
        # Ensure user has chat access
        self.user.has_chat_access = True
        self.user.save()

    def test_recall_after_topic_shift(self):
        """
        Test Phases:
        1. Info Injection: User gives specific details (Name, Secret Code).
        2. Distraction: User switches topic completely (Math/Policy).
        3. Recall: User asks for the specific details from Phase 1.
        
        This tests if the 'summarizer' correctly updated the 'extracted_info' 
        in the system prompt, allowing recall even if messages are truncated.
        """
        print("\n--- Starting Context Switching Test ---")

        # Phase 1: Injection
        secret_code = "BLUE-FALCON-99"
        p1_prompt = f"My name is Agent Smith and my secret code is {secret_code}. Remember this."
        print(f"User: {p1_prompt}")
        
        resp1 = generate_llm_reply(p1_prompt, self.user)
        print(f"Agent: {resp1.response}")
        time.sleep(60)  # Rate Limit Cooldown (Increased for stability)
        
        # Phase 2: Distraction (Context Switch)
        # We explicitly change the topic to something unrelated
        p2_prompt = "Let's change the topic. What is 25 * 4? And tell me a joke about Python."
        print(f"User: {p2_prompt}")
        
        resp2 = generate_llm_reply(p2_prompt, self.user)
        print(f"Agent: {resp2.response}")
        time.sleep(60)  # Rate Limit Cooldown (Increased for stability)

        # Phase 3: Recall
        p3_prompt = "What was my secret code?"
        print(f"User: {p3_prompt}")
        
        resp3 = generate_llm_reply(p3_prompt, self.user)
        print(f"Agent: {resp3.response}")
        
        # Assertions (Precision)
        self.assertIn(secret_code, resp3.response, "Recall Failed: Agent did not return the correct secret code.")
        print("--- Precision Check: PASSED (Code retrieved correctly) ---")

    def test_multi_turn_distraction(self):
        """
        Test recall after multiple distraction turns to force message truncation 
        (if we were sending 20+ messages, but here we just test logic persistence).
        """
        print("\n--- Starting Multi-Turn Distraction Test ---")
        
        # 1. Setup
        project_name = "Project Omega"
        generate_llm_reply(f"I am working on {project_name}.", self.user)
        
        # 2. Distract
        distractions = [
            "What is the capital of France?",
            "How do I cook pasta?",
        ]
        
        for d in distractions:
            print(f"User (Distraction): {d}")
            generate_llm_reply(d, self.user)
            time.sleep(60)  # Rate Limit Cooldown (Increased for stability)
            
        # 3. Recall
        p_final = "What project am I working on?"
        print(f"User: {p_final}")
        resp_final = generate_llm_reply(p_final, self.user)
        print(f"Agent: {resp_final.response}")
        
        self.assertIn("Omega", resp_final.response)
        print("--- Recall Check: PASSED ---")

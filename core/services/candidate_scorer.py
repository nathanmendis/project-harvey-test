import json
from core.models.recruitment import CandidateJobScore
from langchain_core.messages import HumanMessage

class CandidateScorer:
    def __init__(self):
        from core.llm_graph.tools_registry import get_llm
        self.llm = get_llm()

    def score_candidate(self, candidate, job_role):
        """
        Scores a candidate against a job role using LLM.
        Returns the score (0-100) and justification.
        """
        
        # Prepare the prompt
        candidate_info = f"Name: {candidate.name}\nSkills: {candidate.skills}\nResume Text: {candidate.parsed_data}"
        job_info = f"Title: {job_role.title}\nDescription: {job_role.description}\nRequirements: {job_role.requirements}"
        
        prompt = f"""
        You are an expert HR recruiter. Evaluate the following candidate for the given job role.
        
        Job Role:
        {job_info}
        
        Candidate:
        {candidate_info}
        
        Provide a match score from 0 to 100 and a brief justification.
        Return the output as a valid JSON object with keys "score" (integer) and "justification" (string).
        Do not include any other text.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content
            
            # Clean up potential markdown formatting
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            data = json.loads(content)
            score = data.get("score", 0)
            justification = data.get("justification", "No justification provided.")
            
            # Save or update the score in the database
            CandidateJobScore.objects.update_or_create(
                candidate=candidate,
                job_role=job_role,
                defaults={
                    "score": score,
                    "justification": justification
                }
            )
            
            return score, justification
            
        except Exception as e:
            print(f"Error scoring candidate: {e}")
            return 0, f"Error during scoring: {e}"

# I need to check ChatService to implement this correctly.

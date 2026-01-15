"""
Azure OpenAI Service
Provides integration with Azure OpenAI for generating exercises,
validating user explanations, and conducting conversations.
"""
import logging
from typing import Optional
from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """Service for interacting with Azure OpenAI GPT-4"""

    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.max_tokens = settings.AZURE_OPENAI_MAX_TOKENS
        self.temperature = settings.AZURE_OPENAI_TEMPERATURE

    async def chat_completion(
        self,
        messages: list[dict],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Send a chat completion request to Azure OpenAI.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Override default max_tokens
            temperature: Override default temperature

        Returns:
            The assistant's response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Azure OpenAI chat completion error: {e}")
            raise

    async def generate_vocabulary_exercise(
        self,
        word: str,
        word_definition: str,
        level: str,
        context: str = "general"
    ) -> dict:
        """
        Generate a contextualized vocabulary exercise for a word.

        Args:
            word: The vocabulary word
            word_definition: Definition of the word
            level: User's level (beginner/intermediate)
            context: Context for the exercise (general, data_engineering, ai)

        Returns:
            Dict with exercise data (sentence, options, correct_answer, explanation)
        """
        context_info = ""
        if context == "data_engineering":
            context_info = "Use examples related to data engineering, databases, ETL, pipelines."
        elif context == "ai":
            context_info = "Use examples related to artificial intelligence, machine learning, neural networks."
        elif context == "technology":
            context_info = "Use examples related to technology and software development."

        prompt = f"""Generate a vocabulary exercise for the word "{word}" at {level} level.
Definition: {word_definition}
{context_info}

Create a fill-in-the-blank exercise with:
1. A natural sentence with the word replaced by a blank ___
2. 4 multiple choice options (including the correct answer)
3. A brief explanation of why the correct answer fits

Respond in JSON format:
{{
    "sentence": "The sentence with ___ for the blank",
    "options": ["option1", "option2", "option3", "option4"],
    "correct_answer": "the correct word",
    "correct_index": 0,
    "explanation": "Brief explanation",
    "example_usage": "Another example sentence using the word"
}}"""

        messages = [
            {"role": "system", "content": "You are an expert English teacher creating vocabulary exercises. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(messages, temperature=0.7)

        # Parse JSON response
        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError("Failed to parse exercise JSON from response")

    async def evaluate_grammar_explanation(
        self,
        rule_name: str,
        rule_description: str,
        user_explanation: str,
        language: str = "pt-BR"
    ) -> dict:
        """
        Evaluate a user's explanation of a grammar rule.

        Args:
            rule_name: Name of the grammar rule
            rule_description: Correct description of the rule
            user_explanation: User's explanation in their own words
            language: User's native language for feedback

        Returns:
            Dict with score, feedback, and suggestions
        """
        prompt = f"""Evaluate this student's explanation of the grammar rule "{rule_name}".

Correct rule description: {rule_description}

Student's explanation (in {language}): {user_explanation}

Evaluate:
1. Accuracy (0-100): How correct is the explanation?
2. Completeness (0-100): Did they cover the key points?
3. Understanding (0-100): Do they truly understand the concept?

Provide feedback in {language}.

Respond in JSON format:
{{
    "accuracy_score": 85,
    "completeness_score": 70,
    "understanding_score": 80,
    "overall_score": 78,
    "feedback": "Feedback in student's language",
    "missing_points": ["Point 1", "Point 2"],
    "suggestions": "How to improve understanding",
    "correct_explanation": "A clear, simple explanation of the rule"
}}"""

        messages = [
            {"role": "system", "content": f"You are an expert English grammar teacher. Provide feedback in {language}. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(messages, temperature=0.3)

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError("Failed to parse evaluation JSON from response")

    async def generate_grammar_exercises(
        self,
        rule_name: str,
        rule_description: str,
        level: str,
        count: int = 5
    ) -> list[dict]:
        """
        Generate practice exercises for a grammar rule.

        Args:
            rule_name: Name of the grammar rule
            rule_description: Description of the rule
            level: User's level (beginner/intermediate)
            count: Number of exercises to generate

        Returns:
            List of exercise dicts
        """
        prompt = f"""Create {count} grammar exercises for the rule "{rule_name}" at {level} level.

Rule: {rule_description}

Create varied exercises (fill-in-blank, error correction, sentence completion).

Respond in JSON format:
{{
    "exercises": [
        {{
            "type": "fill_in_blank",
            "instruction": "Fill in the blank with the correct form",
            "sentence": "She ___ to the store yesterday.",
            "options": ["go", "went", "goes", "going"],
            "correct_answer": "went",
            "correct_index": 1,
            "explanation": "We use 'went' because it's past tense"
        }}
    ]
}}"""

        messages = [
            {"role": "system", "content": "You are an expert English grammar teacher. Create clear, helpful exercises. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(messages, temperature=0.7)

        import json
        try:
            result = json.loads(response)
            return result.get("exercises", [])
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(response[start:end])
                return result.get("exercises", [])
            raise ValueError("Failed to parse exercises JSON from response")

    async def generate_conversation_response(
        self,
        conversation_history: list[dict],
        user_input: str,
        topic: str,
        level: str
    ) -> str:
        """
        Generate a natural conversation response.

        Args:
            conversation_history: Previous exchanges
            user_input: User's latest message
            topic: Conversation topic
            level: User's level (beginner/intermediate)

        Returns:
            Agent's response text
        """
        level_instructions = ""
        if level == "beginner":
            level_instructions = "Use simple vocabulary and short sentences. Speak slowly and clearly."
        else:
            level_instructions = "Use natural, conversational English. Include some idioms and varied vocabulary."

        system_prompt = f"""You are a friendly English conversation partner helping a student practice speaking.
Topic: {topic}
Student level: {level}
{level_instructions}

Guidelines:
- Keep responses concise (1-3 sentences)
- Ask follow-up questions to keep the conversation going
- Be encouraging but don't correct errors mid-conversation
- Speak naturally as a native American English speaker would"""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for exchange in conversation_history:
            messages.append({
                "role": "assistant" if exchange["speaker"] == "agent" else "user",
                "content": exchange["text"]
            })

        # Add current user input
        messages.append({"role": "user", "content": user_input})

        return await self.chat_completion(messages, temperature=0.8, max_tokens=150)

    async def detect_grammar_errors(
        self,
        text: str,
        level: str
    ) -> list[dict]:
        """
        Detect grammar errors in user's text.

        Args:
            text: User's spoken/written text
            level: User's level for appropriate feedback

        Returns:
            List of detected errors with corrections
        """
        prompt = f"""Analyze this English text for grammar errors:
"{text}"

For each error found, provide:
- The incorrect text
- The correction
- The grammar rule violated
- A brief explanation

Focus on errors appropriate for a {level} level student.

Respond in JSON format:
{{
    "errors": [
        {{
            "type": "grammar",
            "incorrect_text": "waked",
            "correction": "woke",
            "rule": "irregular_past_tense",
            "explanation": "The verb 'wake' has an irregular past tense form 'woke', not 'waked'."
        }}
    ],
    "error_count": 1,
    "overall_assessment": "Brief overall feedback"
}}

If no errors are found, return an empty errors array."""

        messages = [
            {"role": "system", "content": "You are an expert English grammar analyzer. Be thorough but fair. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(messages, temperature=0.2)

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            return {"errors": [], "error_count": 0, "overall_assessment": "Unable to analyze"}

    async def compare_grammar_with_portuguese(
        self,
        rule_name: str,
        rule_description: str
    ) -> dict:
        """
        Compare an English grammar rule with Portuguese equivalent.

        Args:
            rule_name: Name of the English grammar rule
            rule_description: Description of the rule

        Returns:
            Dict with comparison, similarities, and differences
        """
        prompt = f"""Compare this English grammar rule with Portuguese:

Rule: {rule_name}
Description: {rule_description}

Analyze:
1. Does this rule exist in Portuguese?
2. What are the similarities?
3. What are the key differences?
4. Common mistakes Portuguese speakers make
5. Tips for Portuguese speakers to remember this rule

Respond in JSON format:
{{
    "exists_in_portuguese": true,
    "portuguese_equivalent": "Nome da regra em português",
    "similarities": ["Similarity 1", "Similarity 2"],
    "differences": ["Difference 1", "Difference 2"],
    "common_mistakes": ["Mistake 1", "Mistake 2"],
    "memory_tips": ["Tip 1", "Tip 2"],
    "example_english": "English example sentence",
    "example_portuguese": "Exemplo em português"
}}"""

        messages = [
            {"role": "system", "content": "You are a bilingual English-Portuguese language expert. Help Portuguese speakers understand English grammar by comparing with their native language. Always respond with valid JSON."},
            {"role": "user", "content": prompt}
        ]

        response = await self.chat_completion(messages, temperature=0.5)

        import json
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(response[start:end])
            raise ValueError("Failed to parse comparison JSON from response")


# Singleton instance
azure_openai_service = AzureOpenAIService()
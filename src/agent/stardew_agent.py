"""LangChain agent for Stardew Valley assistance with rich content handling."""

import logging
import json
from enum import Enum
from typing import Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from config.settings import settings
from src.rag.knowledge_base import StardewRAGSystem
from src.planner.crop_planner import CropPlanner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentMode(Enum):
    HINTS = "hints"
    WALKTHROUGH = "walkthrough"

class StardewAgent:
    """AI agent for Stardew Valley, supporting structured data responses."""
    
    def __init__(self, mode: AgentMode = AgentMode.HINTS):
        self.mode = mode
        self.rag_system = StardewRAGSystem()
        self.crop_planner = CropPlanner(self.rag_system)

        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            openai_api_key=settings.openai_api_key
        )
        
        self.memory = ConversationBufferWindowMemory(
            k=5, return_messages=True, memory_key="chat_history"
        )
        
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent_executor()
    
    def _create_tools(self) -> List[Tool]:
        """Creates tools based on the agent's mode."""
        if self.mode == AgentMode.HINTS:
            return [
                Tool(
                    name="get_hint",
                    description="Get a subtle hint for a specific question about Stardew Valley.",
                    func=self._get_hint_tool
                )
            ]
        else:  # WALKTHROUGH mode
            return [
                Tool(
                    name="search_stardew_knowledge",
                    description="Search for general information. Returns text, and potentially an image or a data table.",
                    func=self._search_knowledge_tool
                ),
                Tool(
                    name="get_specific_info",
                    description="Get detailed information about a specific topic (e.g., crops, animals, characters).",
                    func=self._get_specific_info_tool
                ),
                Tool(
                    name="plan_crop_farming",
                    description="Plan a crop farming strategy. Input: 'crop_name, target_yield, season'.",
                    func=self._plan_crop_tool
                )
            ]

    def _get_hint_tool(self, query: str) -> str:
        """Helper to get a hint from the RAG system."""
        return self.rag_system.get_hint_for_query(query)

    def _search_knowledge_tool(self, query: str) -> str:
        """Helper to search knowledge base."""
        return self.rag_system.get_context_for_query(query)

    def _get_specific_info_tool(self, query: str) -> str:
        """Helper to get specific info."""
        return self.rag_system.get_context_for_query(query)

    def _plan_crop_tool(self, query: str) -> str:
        """
        Delegates crop planning to the CropPlanner instance.
        Query format: "crop_name, target_yield, season"
        Example: "wheat, 100, summer"
        """
        try:
            parts = [p.strip() for p in query.split(',')]
            if len(parts) != 3:
                return "Invalid query format for crop planning. Please use 'crop_name, target_yield, season'."

            crop_name, target_yield_str, season = parts
            target_yield = int(target_yield_str)
            
            return self.crop_planner.plan_crop_farming(crop_name, target_yield, season)

        except ValueError:
            return "Invalid target yield. Please provide a valid number."
        except Exception as e:
            logger.error(f"Error in _plan_crop_tool: {e}")
            return f"An error occurred while planning your crop: {str(e)}"
            
    def _get_system_prompt(self):
        """Returns the appropriate system prompt based on the agent's mode."""
        walkthrough_prompt = """You are a comprehensive Stardew Valley guide that provides DETAILED WALKTHROUGHS and COMPLETE SOLUTIONS.

Your role:
- Provide step-by-step instructions
- Give complete and detailed explanations
- Include all relevant information and context
- Be thorough and systematic in your responses
- Help players achieve their goals efficiently

Guidelines:
- Provide comprehensive answers with specific steps
- Include relevant numbers, timings, and requirements
- Give complete item lists and resource requirements
- Explain the reasoning behind strategies
- Cover multiple approaches when applicable

When players ask questions, use your tools to gather comprehensive information and provide detailed, actionable guidance."""
        
        hints_prompt = """Your role:
- Give players gentle nudges in the right direction
- Avoid giving away complete solutions unless specifically asked
- Keep responses concise and encouraging
- Let players discover and learn on their own
- Use phrases like "You might want to try...", "Consider...", "Have you thought about..."

Guidelines:
- Keep responses under 200 words
- Focus on one main hint per response
- Ask follow-up questions to guide discovery
- Avoid spoilers about late-game content
- Encourage experimentation and exploration

When players ask questions, use your tools to find relevant information, then present it as a helpful hint rather than a complete answer."""
        
        return walkthrough_prompt if self.mode == AgentMode.WALKTHROUGH else hints_prompt

    def _create_agent_executor(self) -> AgentExecutor:
        """Creates the agent executor with the appropriate prompt."""
        system_message = self._get_system_prompt()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=settings.debug,
            max_iterations=settings.max_response_length // 100,
            early_stopping_method="generate"
        )
            
    def set_mode(self, mode: AgentMode):
        """Changes the agent's mode and recreates the executor."""
        if self.mode != mode:
            self.mode = mode
            logger.info(f"Agent mode changed to: {mode.value}")
            self.agent_executor = self._create_agent_executor()
    
    def _format_structured_output(self, structured_data: Dict) -> str:
        """Formats the structured data into a human-readable string."""
        output_parts = []
        if structured_data.get("text"):
            output_parts.append(structured_data["text"])
        
        if structured_data.get("checklist"):
            checklist = structured_data["checklist"]
            output_parts.append(f"\n**{checklist.get('title', 'Checklist')}:**")
            for item in checklist.get("items", []):
                output_parts.append(f"- {item}")
        
        if structured_data.get("table"):
            table = structured_data["table"]
            headers = table.get("headers", [])
            rows = table.get("rows", [])
            if headers and rows:
                output_parts.append(f"\n| {' | '.join(headers)} |")
                output_parts.append(f"| {' | '.join(['---'] * len(headers))} |")
                for row in rows:
                    output_parts.append(f"| {' | '.join(row)} |")
            
        if structured_data.get("source_url"):
            output_parts.append(f"\nSource: {structured_data['source_url']}")
            
        return "\n".join(output_parts)

    def chat(self, message: str, context: Optional[Dict] = None) -> Dict:
        """Processes a chat message and returns a structured dictionary response."""
        try:
            if context:
                full_message = f"Player's current status: Year {context.get('year', 1)}, {context.get('season', 'Spring')}, Day {context.get('day', 1)}. Question: {message}"
            else:
                full_message = message

            response = self.agent_executor.invoke({"input": full_message})
            output = response.get("output", '{"text": "Sorry, I had trouble processing that."}')
            
            try:
                structured_output = json.loads(output)
            except json.JSONDecodeError:
                structured_output = {"text": output}

            if not structured_output.get("source_url") and self.mode != AgentMode.HINTS:
                logger.info("No source_url in LLM response, finding a fallback.")
                fallback_results = self.rag_system.search(message, n_results=1)
                if fallback_results:
                    structured_output["source_url"] = fallback_results[0]['metadata'].get('url')

            formatted_text = self._format_structured_output(structured_output)

            return {
                "text": formatted_text,
                "image_url": structured_output.get("image_url"),
                "table": structured_output.get("table"),
                "checklist": structured_output.get("checklist"),
                "source_url": structured_output.get("source_url")
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {"text": "I apologize, but I encountered an error while processing your request. Please try again or rephrase your query."}
    
    def get_conversation_history(self) -> List[BaseMessage]:
        """Get the current conversation history."""
        return self.memory.chat_memory.messages
    
    def clear_memory(self):
        """Clear the conversation memory."""
        self.memory.clear()
        logger.info("Conversation memory cleared")
    
    def get_mode_info(self) -> Dict:
        """Get information about the current mode."""
        mode_descriptions = {
            AgentMode.HINTS: {
                "name": "Hints Mode",
                "description": "Provides subtle guidance and hints without spoilers",
                "style": "Encouraging nudges that let you discover solutions",
                "response_length": "Concise (under 200 words)",
                "spoiler_protection": "High - avoids revealing solutions directly"
            },
            AgentMode.WALKTHROUGH: {
                "name": "Full Walkthrough Mode", 
                "description": "Provides detailed step-by-step instructions",
                "style": "Comprehensive guides with complete solutions",
                "response_length": "Detailed (comprehensive explanations)",
                "spoiler_protection": "Low - provides complete information"
            }
        }
        
        return mode_descriptions[self.mode]

if __name__ == '__main__':
    agent = StardewAgent(mode=AgentMode.WALKTHROUGH)
    test_query = "What monsters are in the volcano dungeon?"
    print(f"Testing query: {test_query}")
    response = agent.chat(test_query)
    print("\nStructured Response:")
    print(json.dumps(response, indent=2))

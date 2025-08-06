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
            temperature=0.6,
            openai_api_key=settings.openai_api_key
        )
        
        self.memory = ConversationBufferWindowMemory(
            k=5, return_messages=True, memory_key="chat_history"
        )
        
        self.tools = self._create_tools()
        self.agent_executor = self._create_agent_executor()
    
    def _create_tools(self) -> List[Tool]:
        """Creates tools that can return structured data."""
        return [
            Tool(
                name="search_stardew_knowledge",
                description="Search for general information. Returns text, and potentially an image or a data table.",
                func=self._search_knowledge_tool
            ),
            Tool(
                name="get_specific_info",
                description="Get detailed information about a specific topic in Stardew Valley (crops, animals, characters, locations, etc.).",
                func=self._get_specific_info_tool
            ),
            Tool(
                name="plan_crop_farming",
                description="Plan a crop farming strategy, including land size, seeds, fertilizer, and startup funds for a target yield of a specific crop in a given season. Input should be a string like 'crop_name, target_yield, season'.",
                func=self._plan_crop_tool
            )
        ]

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
        walkthrough_prompt = """You are a master Stardew Valley strategist. Your goal is to provide comprehensive, step-by-step guides, **always tailored to the player's current situation.**

**Player Context:**
- You will be given the player's current Year, Season, and Day.
- **THIS IS CRITICAL:** Use this information to make your advice timely and relevant. For example, do not suggest planting Spring crops in Fall. Check birthdays, festivals, or villager schedules based on the current date.

**Conversation Context:**
- Pay close attention to the `chat_history`. It contains previous turns of the conversation.
- Use this history to understand follow-up questions and resolve pronouns (e.g., if the user asks about "Leah" and then asks "where does she live?", you MUST know "she" is Leah).

**Reasoning Process:**
1.  **Analyze Query & Context:** Analyze the user's question, their game status, and the chat history.
2.  **Tool Selection:**
    *   For crafting recipes, bundle requirements, or step-by-step tasks, **immediately use the `create_checklist` tool**.
    *   For specific data lookup (like a fish's location), use `get_specific_info`.
    *   For general questions, use `search_stardew_knowledge`.
3.  **Synthesize (If Necessary):** If a simple tool call isn't enough (e.g., complex strategy), deconstruct the problem, execute multiple tool calls, and synthesize the results into a cohesive answer.

**Formatting Instructions:**
- **Use Markdown for all text responses.** This includes headings, subheadings, bulleted lists, and bold text to create a clear and readable response.

**Output Format:**
- **CRITICAL:** Your final output to the user MUST be a single, valid JSON object.
- The root of this JSON object must contain the keys 'text', 'image_url', 'table', 'checklist', and 'source_url'.
- Populate these fields with the information you gather. If a field is not applicable (e.g., no table was found), its value must be `null`.
- When you use the `create_checklist` tool, place its dictionary output directly into the `checklist` field of the final JSON. Do not wrap it in other keys.
"""
        
        hints_prompt = """You are a friendly Stardew Valley assistant.

**Instructions:**
1.  Use the player's context (Year, Season, Day) to give timely advice.
2.  Use the `chat_history` to understand follow-up.
3.  If asked for a recipe or bundle, use the `create_checklist` tool.
4.  **CRITICAL:** Your final output MUST be a single, valid JSON object with the keys 'text', 'image_url', 'table', 'checklist', and 'source_url'. Inapplicable fields must be `null`.
"""
        
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

            if not structured_output.get("source_url"):
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

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
from src.planner.crop_planner import CropPlanner # Add this import

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
        self.crop_planner = CropPlanner(self.rag_system) # Instantiate CropPlanner

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
                func=self.search_knowledge_tool
            ),
            Tool(
                name="get_specific_info",
                description="Get detailed information about a specific topic in Stardew Valley (crops, animals, characters, locations, etc.).",
                func=self._get_specific_info_tool
            ),
            Tool( # New tool for crop planning
                name="plan_crop_farming",
                description="Plan a crop farming strategy, including land size, seeds, fertilizer, and startup funds for a target yield of a specific crop in a given season. Input should be a string like 'crop_name, target_yield, season'.",
                func=self._plan_crop_tool # This will now call the new method
            )
        ]
        return tools

    def _search_knowledge_tool(self, query: str) -> str:
        """Helper to search knowledge base."""
        return self.rag_system.get_context_for_query(query)

    def _get_specific_info_tool(self, query: str) -> str:
        """Helper to get specific info."""
        # This could be enhanced to parse query for specific entities more robustly
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
            
    def set_mode(self, new_mode: AgentMode):
        """
        Sets the agent's operating mode and recreates the agent executor.
        """
        if self.mode != new_mode:
            self.mode = new_mode
            logger.info(f"Agent mode set to {self.mode.value}")
            # Recreate agent with new mode
            self.agent = self._create_agent()
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=self.memory,
                verbose=settings.debug,
                max_iterations=settings.max_response_length // 100, # Adjust max iterations based on response length
                early_stopping_method="generate"
            )
        
    def _create_agent(self):
        """Create the LangChain agent with appropriate prompts."""
        if self.mode == AgentMode.HINTS:
            system_message = """You are a helpful Stardew Valley assistant that provides HINTS and SUBTLE GUIDANCE.\n\nYour role:\n- Give players gentle nudges in the right direction\n- Avoid giving away complete solutions unless specifically asked\n- Keep responses concise and encouraging\n- Let players discover and learn on their own\n- Use phrases like "You might want to try...", "Consider...", "Have you thought about..."\n\nGuidelines:\n- Keep responses under 200 words\n- Focus on one main hint per response\n- Ask follow-up questions to guide discovery\n- Avoid spoilers about late-game content\n- Encourage experimentation and exploration\n\nWhen players ask questions, use your tools to find relevant information, then present it as a helpful hint rather than a complete answer."""

        else:  # WALKTHROUGH mode
            system_message = """You are a comprehensive Stardew Valley guide that provides DETAILED WALKTHROUGHS and COMPLETE SOLUTIONS.\n\nYour role:\n- Provide step-by-step instructions\n- Give complete and detailed explanations\n- Include all relevant information and context\n- Be thorough and systematic in your responses\n- Help players achieve their goals efficiently\n\nGuidelines:\n- Provide comprehensive answers with specific steps\n- Include relevant numbers, timings, and requirements\n- Give complete item lists and resource requirements\n- Explain the reasoning behind strategies\n- Cover multiple approaches when applicable\n\nWhen players ask questions, use your tools to gather comprehensive information and provide detailed, actionable guidance.\nYour user has asked for a crop planning feature. When a user asks for a plan for a specific crop, quantity, and season, use the `plan_crop_farming` tool.\nThe `plan_crop_farming` tool input format is 'crop_name, target_yield, season'. For example, if the user asks "plan to grow 100 wheat in summer", you should call the tool with `plan_crop_farming(wheat, 100, summer)`.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        return create_openai_functions_agent(self.llm, self.tools, prompt)

    def process_message(self, message: str, mode: Optional[str] = None) -> str:
        """Process a user message and return the agent's response."""
        if mode and mode.lower() in [m.value for m in AgentMode]:
            self.mode = AgentMode(mode.lower())
            logger.info(f"Agent mode set to {self.mode.value}")
        
        # Recreate agent with new mode if it changed
        self.agent = self._create_agent()
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=settings.debug,
            max_iterations=settings.max_response_length // 100, # Adjust max iterations based on response length
            early_stopping_method="generate"
        )
        
        try:
            response = self.agent_executor.invoke({"input": message})
            return response["output"]
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again or rephrase your query."
    
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


# Convenience functions for creating agents
def create_hints_agent() -> StardewAgent:
    """Create an agent in hints mode."""
    return StardewAgent(mode=AgentMode.HINTS)


def create_walkthrough_agent() -> StardewAgent:
    """Create an agent in walkthrough mode."""
    return StardewAgent(mode=AgentMode.WALKTHROUGH)


def main():
    """Test the agent functionality."""
    print("Testing Stardew Valley Agent...")
    
    # Test hints mode
    print("\n=== HINTS MODE ===")
    hints_agent = create_hints_agent()
    response = hints_agent.chat("How do I make money in early game?")
    print(f"Response: {response}")
    
    # Test walkthrough mode
    print("\n=== WALKTHROUGH MODE ===")
    walkthrough_agent = create_walkthrough_agent()
    response = walkthrough_agent.chat("How do I make money in early game?")
    print(f"Response: {response}")


if __name__ == "__main__":
    main()

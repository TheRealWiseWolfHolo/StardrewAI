"""LangChain agent for Stardew Valley assistance with Hints and Walkthrough modes."""

import logging
from enum import Enum
from typing import Dict, List, Optional

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from config.settings import settings
from src.rag.knowledge_base import StardewRAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentMode(Enum):
    """Agent operation modes."""
    HINTS = "hints"
    WALKTHROUGH = "walkthrough"


class StardewAgent:
    """AI agent for Stardew Valley assistance with configurable response modes."""
    
    def __init__(self, mode: AgentMode = AgentMode.HINTS):
        self.mode = mode
        self.rag_system = StardewRAGSystem()
        
        # Initialize OpenAI LLM
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            max_tokens=settings.max_response_length,
            openai_api_key=settings.openai_api_key
        )
        
        # Initialize memory
        self.memory = ConversationBufferWindowMemory(
            k=5,  # Remember last 5 exchanges
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate"
        )
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent."""
        tools = [
            Tool(
                name="search_stardew_knowledge",
                description="Search the Stardew Valley knowledge base for information about gameplay, items, characters, or strategies.",
                func=self._search_knowledge_tool
            ),
            Tool(
                name="get_specific_info",
                description="Get detailed information about a specific topic in Stardew Valley (crops, animals, characters, locations, etc.).",
                func=self._get_specific_info_tool
            )
        ]
        return tools
    
    def _search_knowledge_tool(self, query: str) -> str:
        """Tool function to search the knowledge base."""
        try:
            results = self.rag_system.search(query, n_results=3)
            if not results:
                return "No specific information found in the knowledge base."
            
            # Format results based on mode
            if self.mode == AgentMode.HINTS:
                # Provide concise, hint-like information
                context = results[0]['content'][:200] + "..."
                return f"Hint: {context}"
            else:
                # Provide detailed information
                context_parts = []
                for result in results:
                    title = result['metadata'].get('title', 'Unknown')
                    content = result['content'][:300]
                    context_parts.append(f"From {title}: {content}")
                return "\n\n".join(context_parts)
                
        except Exception as e:
            logger.error(f"Error in search tool: {str(e)}")
            return "Sorry, I couldn't retrieve information at the moment."
    
    def _get_specific_info_tool(self, topic: str) -> str:
        """Tool function to get specific information about a topic."""
        try:
            # Search for specific information
            enhanced_query = f"detailed information about {topic} in Stardew Valley"
            results = self.rag_system.search(enhanced_query, n_results=2)
            
            if not results:
                return f"No detailed information found about {topic}."
            
            # Return appropriate level of detail based on mode
            if self.mode == AgentMode.HINTS:
                return f"Quick tip about {topic}: {results[0]['content'][:150]}..."
            else:
                context = self.rag_system.get_context_for_query(enhanced_query, max_chunks=2)
                return context
                
        except Exception as e:
            logger.error(f"Error in specific info tool: {str(e)}")
            return f"Sorry, I couldn't get specific information about {topic}."
    
    def _create_agent(self):
        """Create the LangChain agent with appropriate prompts."""
        if self.mode == AgentMode.HINTS:
            system_message = """You are a helpful Stardew Valley assistant that provides HINTS and SUBTLE GUIDANCE.

Your role:
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

        else:  # WALKTHROUGH mode
            system_message = """You are a comprehensive Stardew Valley guide that provides DETAILED WALKTHROUGHS and COMPLETE SOLUTIONS.

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

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        return create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    def set_mode(self, mode: AgentMode):
        """Change the agent's response mode."""
        if self.mode != mode:
            self.mode = mode
            logger.info(f"Agent mode changed to: {mode.value}")
            # Recreate agent with new mode
            self.agent = self._create_agent()
            self.agent_executor = AgentExecutor(
                agent=self.agent,
                tools=self.tools,
                memory=self.memory,
                verbose=True,
                max_iterations=3,
                early_stopping_method="generate"
            )
    
    def chat(self, message: str) -> str:
        """Process a chat message and return a response."""
        try:
            # Add mode context to the message
            mode_context = f"[{self.mode.value.upper()} MODE] "
            enhanced_message = mode_context + message
            
            response = self.agent_executor.invoke({
                "input": enhanced_message
            })
            
            return response.get("output", "I'm sorry, I couldn't process your request.")
            
        except Exception as e:
            logger.error(f"Error processing chat message: {str(e)}")
            return "I encountered an error while processing your request. Please try again."
    
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

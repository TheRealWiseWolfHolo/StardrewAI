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
                description="Get detailed info on a topic. Prefers to find and return a data table if relevant.",
                func=self.get_specific_info_tool
            )
        ]

    def _format_structured_result(self, results: List[Dict]) -> str:
        """Formats search results into a structured JSON string for the LLM."""
        if not results:
            return json.dumps({"text": "No information found."})

        # Prioritize returning a table if one was found
        table_result = next((r for r in results if r['metadata'].get('source_type') == 'table'), None)
        if table_result:
            return json.dumps({
                "text": f"Found a data table for '{table_result['metadata']['title']}'.",
                "table": table_result['metadata'].get('table'),
                "image_url": table_result['metadata'].get('image_url'),
                "source_url": table_result['metadata'].get('url')
            })

        # Otherwise, return the top text result
        top_result = results[0]
        return json.dumps({
            "text": top_result['content'],
            "image_url": top_result['metadata'].get('image_url'),
            "source_url": top_result['metadata'].get('url')
        })

    def search_knowledge_tool(self, query: str) -> str:
        """Tool to search the KB. Returns a JSON string."""
        try:
            results = self.rag_system.search(query, n_results=3)
            return self._format_structured_result(results)
        except Exception as e:
            logger.error(f"Error in search tool: {e}")
            return json.dumps({"text": "Sorry, an error occurred during search."})
    
    def get_specific_info_tool(self, topic: str) -> str:
        """Tool for specific info, prioritizing tables. Returns a JSON string."""
        try:
            # First, search specifically for tables related to the topic
            table_results = self.rag_system.search(topic, n_results=2, filter_dict={'source_type': 'table'})
            if table_results:
                return self._format_structured_result(table_results)
            
            # If no table, do a general search
            general_results = self.rag_system.search(topic, n_results=3)
            return self._format_structured_result(general_results)
        except Exception as e:
            logger.error(f"Error in specific info tool: {e}")
            return json.dumps({"text": f"Sorry, an error occurred finding info on {topic}."})

    def _create_agent_executor(self):
        """Creates the LangChain agent executor."""
        system_message = self._get_system_message()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "Current game status: {context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        agent = create_openai_functions_agent(self.llm, self.tools, prompt)
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True # Important for structured output
        )
    
    def _get_system_message(self) -> str:
        """Gets the system message based on the current agent mode."""
        
        walkthrough_prompt = """You are a master Stardew Valley strategist. Your goal is to provide comprehensive, step-by-step guides, **always tailored to the player's current situation.**

**Player Context:**
- You will be given the player's current Year, Season, and Day.
- **THIS IS CRITICAL:** Use this information to make your advice timely and relevant. For example, do not suggest planting Spring crops in Fall. Check birthdays, festivals, or villager schedules based on the current date.

**Conversation Context:**
- Pay close attention to the `chat_history`. It contains previous turns of the conversation.
- Use this history to understand follow-up questions and resolve pronouns (e.g., if the user asks about "Leah" and then asks "where does she live?", you MUST know "she" is Leah).

**Reasoning Process:**
1.  **Analyze Query:** Is this a simple question or a complex strategic one? **Always consider the player's context and conversation history.**
2.  **Simple Queries:** Use a tool directly and return the result.
3.  **Complex Queries (IMPORTANT):**
    a. **Deconstruct:** Break the complex query into a logical sequence of smaller, specific sub-questions answerable by your tools, considering the player's context.
    b. **Execute Sub-Queries:** Use your tools to answer each sub-question one by one.
    c. **Synthesize:** Combine the information into a single, cohesive, and easy-to-understand step-by-step guide.

**Output Format:**
- Your final output MUST be a single JSON object with 'text' and optional 'image_url', 'table', and 'source_url' fields.
"""
        
        hints_prompt = """You are a friendly Stardew Valley assistant who gives helpful hints, **tailored to the player's current situation.**

**Player Context:**
- You will be given the player's current Year, Season, and Day.
- Use this to give relevant advice. E.g., remind them of a festival happening tomorrow.

**Conversation Context:**
- Pay close attention to the `chat_history` to understand follow-up questions.

**Answering Style:**
- Provide concise, timely tips.
- Your final output MUST be a single JSON object.
"""
        
        return walkthrough_prompt if self.mode == AgentMode.WALKTHROUGH else hints_prompt

    def set_mode(self, mode: AgentMode):
        """Changes the agent's mode and recreates the executor."""
        if self.mode != mode:
            self.mode = mode
            logger.info(f"Agent mode changed to: {mode.value}")
            self.agent_executor = self._create_agent_executor()
    
    def chat(self, message: str, context: Optional[Dict] = None) -> Dict:
        """Processes a chat message and returns a structured dictionary response."""
        try:
            # Include context in the input if it exists
            input_data = {"input": message}
            if context:
                input_data["context"] = f"Player's current status: Year {context.get('year', 1)}, {context.get('season', 'Spring')}, Day {context.get('day', 1)}."
            else:
                input_data["context"] = "Player status is not specified."

            response = self.agent_executor.invoke(input_data)
            output = response.get("output", '{"text": "Sorry, I had trouble processing that."}')
            
            # Ensure output is a valid JSON object
            try:
                structured_output = json.loads(output)
            except json.JSONDecodeError:
                # If the LLM failed to return JSON, wrap its text output
                structured_output = {"text": output}

            # If the LLM didn't include a source, find a relevant one.
            if not structured_output.get("source_url"):
                logger.info("No source_url in LLM response, finding a fallback.")
                fallback_results = self.rag_system.search(message, n_results=1)
                if fallback_results:
                    structured_output["source_url"] = fallback_results[0]['metadata'].get('url')

            # Standardize the final dictionary
            return {
                "text": structured_output.get("text"),
                "image_url": structured_output.get("image_url"),
                "table": structured_output.get("table"),
                "source_url": structured_output.get("source_url")
            }
            
        except Exception as e:
            logger.error(f"Error in agent.chat: {e}")
            return {"text": "An error occurred. Please try again."}

if __name__ == '__main__':
    # A simple test for the agent
    agent = StardewAgent(mode=AgentMode.WALKTHROUGH)
    test_query = "What monsters are in the volcano dungeon?"
    print(f"Testing query: {test_query}")
    response = agent.chat(test_query)
    print("\nStructured Response:")
    print(json.dumps(response, indent=2))
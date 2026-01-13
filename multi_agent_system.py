import json, os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
import asyncio
from dotenv import load_dotenv
from colorama import Fore, Style
import string

from google import genai
from google.genai import types
from google.adk.runners import Runner
from google.adk.agents.llm_agent import LlmAgent
from google.adk.memory import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService
from google.adk.tools import load_memory, preload_memory
from google.genai import types # For types.Content
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.run_config import RunConfig, StreamingMode

from prompts import PromptConfig
from config import ModelConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

class MultiAgentOrchestrator:
    """
    Multi-agent orchestrator using ADK Runner pattern
    Similar to LangGraph's state management and routing
    """
    
    def __init__(
        self,
        mcp_tools: List = [],
        rag_tools: List = [],
    ):
        """
        Initialize multi-agent orchestrator
        
        Args:
            mcp_tools: MCP tools for database access
            rag_tools: RAG similarity search tool
        """
        self.mcp_tools = mcp_tools
        self.rag_tools = rag_tools
        self.model_name = ModelConfig.MODEL_NAME

        self.stream_mode = StreamingMode.SSE
        
        # Load prompt configurations
        self.prompt_config = PromptConfig()
        self.app_name = ModelConfig.APP_NAME
        self.temperature = ModelConfig.TEMPERATURE
        
        # Initialize Google GenAI client
        if GOOGLE_API_KEY:
            self.client = genai.Client(api_key=GOOGLE_API_KEY)
        else:
            self.client = genai.Client()
        
        # Initialize ADK services
        self.session_service = InMemorySessionService()
        self.memory_service = InMemoryMemoryService()
        
        
        # Initialize agents
        self.orchestrator_agent = self._create_orchestrator_agent()
        self.mcp_tools_agent = self._create_mcp_tools_agent()
        self.rag_agent = self._create_rag_agent()
        self.final_response_agent = self._create_final_response_agent()
        
        # Create runners for each agent
        self.orchestrator_runner = None
        self.mcp_runner = None
        self.rag_runner = None
        self.final_runner = None
        
        logger.info("✅ Multi-Agent Orchestrator initialized successfully")

    def _format_prompt_with_user_id(self, prompt: str, user_id: str) -> str:
        """Format prompt by replacing {user_id} placeholder with actual user_id"""
        return prompt.replace("{user_id}", user_id)

    def _create_orchestrator_agent(self) -> LlmAgent:
        """Create orchestrator agent for intent classification"""
        logger.info("Creating Orchestrator Agent...")
        
        agent = LlmAgent(
            model=self.model_name,
            name='orchestrator_agent',
            instruction=self.prompt_config.get_orchestrator_prompt(),
            generate_content_config=types.GenerateContentConfig(
                temperature=self.temperature,
            ),
            tools=[load_memory],
            output_key="query_intent",
            after_agent_callback= self.auto_save_session_to_memory_callback
        )
        
        logger.info("✅ Orchestrator Agent created")
        return agent
    
    def _create_mcp_tools_agent(self) -> LlmAgent:
        """Create MCP tools agent for database operations"""
        logger.info("Creating MCP Tools Agent...")
        
        # Combine MCP tools with preload_memory tool
        print("mcp_tools",self.mcp_tools)
        tools = [load_memory]
        tools.extend(self.mcp_tools)
        
        agent = LlmAgent(
            model=self.model_name,
            name='mcp_tools_agent',
            instruction=self.prompt_config.get_mcp_tools_prompt(),
            tools=tools,
            generate_content_config=types.GenerateContentConfig(
                temperature=self.temperature,
            ),
            output_key="mcp_agent_output",
            after_agent_callback=self.auto_save_session_to_memory_callback
        )
        
        logger.info("✅ MCP Tools Agent created")
        return agent
    
    def _create_rag_agent(self) -> LlmAgent:
        """Create RAG agent for product knowledge"""
        logger.info("Creating RAG Agent...")
        tools = [load_memory]
        tools.extend(self.rag_tools)
        
        agent = LlmAgent(
            model=self.model_name,
            name='rag_agent',
            instruction=self.prompt_config.get_rag_prompt(),
            tools=tools,
            generate_content_config=types.GenerateContentConfig(
                temperature=self.temperature,
            ),
            output_key="rag_agent_output",
            after_agent_callback=self.auto_save_session_to_memory_callback
        )
        
        logger.info("✅ RAG Agent created")
        return agent
    
    def _create_final_response_agent(self) -> LlmAgent:
        """Create final response agent for synthesizing and formatting final output"""
        logger.info("Creating Final Response Agent...")
        
        agent = LlmAgent(
            model=self.model_name,
            name='final_response_agent',
            instruction=self.prompt_config.get_final_response_prompt(),
            tools=[preload_memory],
            generate_content_config=types.GenerateContentConfig(
                temperature=0.7,  # Slightly higher for natural responses
            ),
            output_key="final_response",
            after_agent_callback=self.auto_save_session_to_memory_callback
        )
        
        logger.info("✅ Final Response Agent created")
        return agent

    async def orchestrate(
        self,
        query: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Main orchestration method - coordinates agent execution
        Similar to LangGraph's graph execution
        
        Args:
            query: User query
            user_id: User identifier
            
        Returns:
            Final response dictionary
        """
        logger.info("=" * 80)
        logger.info(f"🎯 Starting Orchestration")
        logger.info(f"Query: {query}")
        logger.info(f"User: {user_id}")
        logger.info("=" * 80)
    
        try:
            # Step 1: Run Orchestrator Agent (Intent Classification)
            logger.info("\n" + "="*60)
            logger.info("STEP 1: ORCHESTRATOR - Intent Classification")
            logger.info("="*60)
            
            state = await self._run_orchestrator(user_id, query)
            
            if state.get('error'):
                return state
            
            # Step 2: Route based on intent
            logger.info(f"\n🎭 Intent Detected: {self.intent_state}")
            self.intent_state= self.intent_state.strip()
            intent_state_words = set(self.remove_punctuation(self.intent_state).split())
            intent_types = self.prompt_config.get_intent_types()
            
            mcp_output = None
            rag_output = None

            if len(set(intent_types['transaction'].split()) &(intent_state_words)) > 1:
                # Route to MCP Tools Agent
                mcp_output = await self._run_mcp_agent(user_id, query)
            
            elif len(set(intent_types['product'].split()) &(intent_state_words)) > 1:
                # Route to RAG Agent
                rag_output = await self._run_rag_agent(user_id, query)
            
            elif len(set(intent_types['hybrid'].split()) & (intent_state_words)) > 1:
                # Route to both agents
                mcp_output = await self._run_mcp_agent(user_id, query)
                rag_output = await self._run_rag_agent(user_id, query)
                
            
            # Step 3: Run Final Response Agent to synthesize output
            logger.info("\n" + "="*60)
            logger.info("STEP 4: FINAL RESPONSE - Synthesizing Output")
            logger.info("="*60)
            
            final_response = await self._run_final_response_agent(
                user_id=user_id,
                query=query,
                intent=self.intent_state,
                mcp_output=mcp_output,
                rag_output=rag_output
            )
            
            logger.info("\n" + "="*80)
            logger.info("✅ Orchestration Complete")
            logger.info("="*80)
            
            return {
                'success': True,
                'intent': self.intent_state,
                'final_response': final_response,
                'user_id': user_id
            }
        
        except Exception as e:
            logger.error(f"❌ Orchestration error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'user_id': user_id
            }
    
    async def _get_or_create_session(self, user_id: str, session_id: str):
        """Get or create session"""
        try:
            session = await self.session_service.create_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id,
                state={"user_id": user_id}
            )
            logger.info(f"✅ Created new session: {session_id}")
        except Exception:
            session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=session_id
            )
            logger.info(f"📖 Retrieved existing session: {session_id}")
        
        return session
    
    async def _run_orchestrator(
        self,
        user_id: str,
        query: str
    ):
        """Run orchestrator agent to classify intent"""
        try:
            session_id = "orchestrator_session"
            
            # # Format prompt with user_id
            # formatted_instruction = self._format_prompt_with_user_id(
            #     self.prompt_config.get_orchestrator_prompt(),
            #     user_id
            # )
            # self.orchestrator_agent.instruction = formatted_instruction
            
            # Create runner for orchestrator
            runner = Runner(
                agent=self.orchestrator_agent,
                app_name=self.app_name,
                session_service=self.session_service,
                memory_service=self.memory_service
            )
            
            session = await self._get_or_create_session(user_id, session_id)
            
            # Run orchestrator
            query_content = types.Content(role="user", parts=[types.Part(text=query)])
            events_async  = runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=query_content,
                run_config=RunConfig(streaming_mode=self.stream_mode),

            )
            async for event in events_async:
                if event.is_final_response():
                    print(Fore.MAGENTA + "\nFinal response received. Exiting loop.")
                    response = event.content.parts[0].text
                    break

                if event.content and event.content.parts:
                    if event.get_function_calls():
                        print(Fore.GREEN + "CALLING TOOL:", event.get_function_calls()[0].name)
                    elif event.get_function_responses():
                        print(Fore.GREEN + "GET TOOL RESPONSE SUCCESSFULLY")
                        # print(event.get_function_responses())
                    elif event.content.parts[0].text:
                        print(Fore.BLUE + event.content.parts[0].text, flush=True, end="")
                        # Parse response
            
            await self.get_query_intent(runner, user_id, session_id)
            response_text = response.strip()
            logger.info(f"Orchestrator raw response: {response_text}")
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    async def _run_mcp_agent(
        self,
        user_id: str,
        query: str
    ) -> str:
        """Run MCP tools agent"""
        logger.info("\n" + "="*60)
        logger.info("STEP 2: MCP TOOLS AGENT - Transaction Data")
        logger.info("="*60)
        
        try:
            session_id = "mcp_session"
            
            # # Format prompt with user_id
            # formatted_instruction = self._format_prompt_with_user_id(
            #     self.prompt_config.get_mcp_tools_prompt(),
            #     user_id
            # )
            # self.mcp_tools_agent.instruction = formatted_instruction
            
            # Create runner for MCP agent
            runner = Runner(
                agent=self.mcp_tools_agent,
                app_name=self.app_name,
                session_service=self.session_service,
                memory_service=self.memory_service
            )
            session = await self._get_or_create_session(user_id, session_id)
            
            query_content = types.Content(role="user", parts=[types.Part(text=query)])
            
            # Run MCP agent
            events_async  = runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=query_content,
                    run_config=RunConfig(streaming_mode=self.stream_mode),

                )
            async for event in events_async:
                if event.is_final_response():
                    print(Fore.MAGENTA + "\nFinal response received. Exiting loop.")
                    response = event.content.parts[0].text
                    break

                if event.content and event.content.parts:
                    if event.get_function_calls():
                        print(Fore.GREEN + "CALLING TOOL:", event.get_function_calls()[0].name)
                        try:
                            args = json.loads(event.get_function_calls()[0].args)
                            print(Fore.YELLOW + "Parameters being sent:", args)
                        except Exception as e:
                            print(Fore.RED + "Failed to parse arguments:", event.get_function_calls()[0].args)
                    elif event.get_function_responses():
                        print(Fore.GREEN + "GET TOOL RESPONSE SUCCESSFULLY")
                        # print(event.get_function_responses())
                    elif event.content.parts[0].text:
                        print(Fore.BLUE + event.content.parts[0].text, flush=True, end="")
                        # Parse response

            logger.info(f"✅ MCP Agent response: {response[:200]}...")
            return response
                
        except Exception as e:
            logger.error(f"MCP Agent error: {e}", exc_info=True)
            return f"Error retrieving transaction data: {str(e)}"
    
    async def _run_rag_agent(
        self,
        user_id: str,
        query: str
    ) -> str:
        """Run RAG agent"""
        logger.info("\n" + "="*60)
        logger.info("STEP 3: RAG AGENT - Product Knowledge")
        logger.info("="*60)
        
        try:
            session_id = "rag_session"
            
            # # Format prompt with user_id
            # formatted_instruction = self._format_prompt_with_user_id(
            #     self.prompt_config.get_rag_prompt(),
            #     user_id
            # )
            # self.rag_agent.instruction = formatted_instruction
            
            # Create runner for RAG agent
            runner = Runner(
                agent=self.rag_agent,
                app_name=self.app_name,
                session_service=self.session_service,
                memory_service=self.memory_service
            )
            session = await self._get_or_create_session(user_id, session_id)
            
            # Run RAG agent
            query_content = types.Content(role="user", parts=[types.Part(text=query)])
            events_async = runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=query_content,
                run_config=RunConfig(streaming_mode=self.stream_mode),

            )
            async for event in events_async:
                if event.is_final_response():
                    print(Fore.RED + "\nFinal response received. Exiting loop.")
                    response = event.content.parts[0].text
                    break

                if event.content and event.content.parts:
                    if event.get_function_calls():
                        print(Fore.GREEN + "CALLING TOOL:", event.get_function_calls()[0].name)
                    elif event.get_function_responses():
                        print(Fore.GREEN + "GET TOOL RESPONSE SUCCESSFULLY")
                        # print(event.get_function_responses())
                    elif event.content.parts[0].text:
                        print(Fore.BLUE + event.content.parts[0].text, flush=True, end="")
                        # Parse response
        
            logger.info(f"✅ RAG Agent response: {response[:200]}...")
            return response
            
        except Exception as e:
            logger.error(f"RAG Agent error: {e}", exc_info=True)
            return f"Error retrieving product information: {str(e)}"

    async def _run_final_response_agent(
        self,
        user_id: str,
        query: str,
        intent: str,
        mcp_output: Optional[str] = None,
        rag_output: Optional[str] = None
    ) -> str:
        """Run final response agent to synthesize outputs"""
        try:
            session_id = "final_response_session"
            
            # # Format prompt with user_id
            # formatted_instruction = self._format_prompt_with_user_id(
            #     self.prompt_config.get_final_response_prompt(),
            #     user_id
            # )
            # self.final_response_agent.instruction = formatted_instruction
            
            # Create runner for final response agent
            runner = Runner(
                agent=self.final_response_agent,
                app_name=self.app_name,
                session_service=self.session_service,
                memory_service=self.memory_service
            )
            session = await self._get_or_create_session(user_id, session_id)
            
            # Build context for final response
            context_parts = [f"Original User Query: {query}\n"]
            context_parts.append(f"Detected Intent: {intent}\n")
            
            if mcp_output:
                context_parts.append(f"\n--- Transaction Data ---\n{mcp_output}\n")
            
            if rag_output:
                context_parts.append(f"\n--- Product Information ---\n{rag_output}\n")
            
            context_parts.append("\nPlease synthesize a final, natural response for the user.")
            
            context_content = "".join(context_parts)
            
            # Run final response agent
            query_content = types.Content(role="user", parts=[types.Part(text=context_content)])
            events_async = runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=query_content,
                run_config=RunConfig(streaming_mode=self.stream_mode),

            )
            async for event in events_async:
                if event.is_final_response():
                    print(Fore.MAGENTA + "\nFinal response received. Exiting loop.")
                    response = event.content.parts[0].text
                    break

                if event.content and event.content.parts:
                    if event.get_function_calls():
                        print(Fore.GREEN + "CALLING TOOL:", event.get_function_calls()[0].name)
                    elif event.get_function_responses():
                        print(Fore.GREEN + "GET TOOL RESPONSE SUCCESSFULLY")
                        # print(event.get_function_responses())
                    elif event.content.parts[0].text:
                        print(Fore.BLUE + event.content.parts[0].text, flush=True, end="")
                        # Parse response
            
            logger.info(f"✅ Final Response: {response}...")
            return response
            
        except Exception as e:
            logger.error(f"Final Response Agent error: {e}", exc_info=True)
            return "I apologize, but I encountered an error generating the final response. Please try again."

    async def auto_save_session_to_memory_callback(self, callback_context: CallbackContext):
        """Automatically save session to memory after each agent interaction"""
        logger.info("💾 Auto-saving session to memory...")
        await callback_context._invocation_context.memory_service.add_session_to_memory(
            callback_context._invocation_context.session)
    
    async def get_query_intent(self,orch_runner:Runner,user_id:str,session_id:str=None) -> None:
        """Extract and store query intent from orchestrator output"""
        session = await self._get_or_create_session(user_id, session_id)
        self.intent_state = session.state.get("query_intent")
        print(f"Detected intent: {self.intent_state}")
        return None
    
    def remove_punctuation(self, text : str) -> str:
        """
        Removes all punctuation from the input text.
        
        Args:
            text (str): The input string.
        
        Returns:
            str: The string without punctuation.
        """
        # Create a translation table that maps punctuation to None
        translator = str.maketrans('', '', string.punctuation)
        return text.translate(translator).strip()

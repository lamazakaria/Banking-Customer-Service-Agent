"""
Banking Chatbot API
A FastAPI-based banking assistant with voice support and multi-agent orchestration.
"""

import sys
import time
import io
import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel
import httpx

from google import genai

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import services
from services.stt_service import get_stt_service
from services.tts_service import get_tts_service
from mongo_loader_splitter import MongoLoaderSplitter
from qdrant_vector_database import QdrantManager
from mcp_tools import MCPTools
from multi_agent_system import MultiAgentOrchestrator

# Load environment variables
load_dotenv()

# ==================== Configuration ====================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://127.0.0.1:27017")
DATABASE_NAME = "banking_db"
WHISPER_API_KEY = os.getenv("WHISPER_API_KEY")
VOICE_GOOGLE_API_KEY = os.getenv("VOICE_GOOGLE_API_KEY")
STT_PROVIDER = os.getenv("STT_PROVIDER", "openai")
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "openai")

# ==================== FastAPI App Setup ====================
app = FastAPI(
    title="Banking Chatbot API",
    description="AI-powered banking assistant with voice support",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Database Setup ====================
client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
customers_collection = db["customers"]
transactions_collection = db["transactions"]
accounts_collection = db["accounts"]
chat_history_collection = db["chat_history"]

# ==================== Security Setup ====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# ==================== Google Generative AI Client ====================
genai_client = genai.Client(api_key=VOICE_GOOGLE_API_KEY)

# ==================== Pydantic Models ====================
class UserSignup(BaseModel):
    """User signup request model"""
    customer_id: str
    password: str
    name: str
    email: str
    phone: str


class UserLogin(BaseModel):
    """User login request model"""
    customer_id: str
    password: str


class ChatQuery(BaseModel):
    """Text chat query model"""
    query: str
    user_id: str


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    timestamp: str


class TTSRequest(BaseModel):
    """Text-to-speech request model"""
    text: str
    voice: Optional[str] = None
    language: str = "en-US"


# ==================== JWT Utilities ====================
def create_access_token(data: dict) -> str:
    """Create JWT access token with expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token and return customer_id"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        customer_id = payload.get("sub")
        if customer_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return customer_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== Banking Agent ====================
class BankingAgent:
    """Main banking assistant agent with RAG and MCP tools"""
    
    def __init__(self):
        self.user_sessions = {}
        self.loader_splitter = MongoLoaderSplitter(
            db_name="banking_db",
            collection_name="bank_products",
            mongo_url="mongodb://localhost:27017/"
        )
        self.qdrant_manager = QdrantManager(collection_name="bank_products_collection")
        
        # Initialize vector store
        chunks = self.loader_splitter.generate_chunks()
        self.qdrant_manager.add_documents(chunks)
        
        # Initialize MCP tools
        self.mcp_tools = MCPTools()
        self.multi_agent = None

    def similarity_search(self, query: str, k: int = 2) -> list:
        """Perform similarity search over the Qdrant vector store"""
        return self.qdrant_manager.similarity_search(query=query, k=k)
    
    async def tools(self):
        """Initialize MCP toolsets"""
        self.mcp_toolset = await self.mcp_tools.get_tools_async()
        self.rag_mcp_tool_names = await self.mcp_tools.get_tools_async([
            "get_customer_accounts",
            "get_customer",
            "get_account"
        ])
    
    async def orchestrate(self, query: str, user_id: str) -> str:
        """Orchestrate multi-agent response to user query"""
        if self.multi_agent is None:
            await self.tools()
            self.multi_agent = MultiAgentOrchestrator(
                rag_tools=[self.similarity_search, self.rag_mcp_tool_names],
                mcp_tools=[self.mcp_toolset]
            )
        
        results = await self.multi_agent.orchestrate(query=query.lower(), user_id=user_id)
        response = results.get("final_response")
        
        if response is None:
            response = results.get("error", "Sorry, I couldn't process your request at this time.")
        
        return response


# Initialize agent
agent = BankingAgent()


# ==================== API Routes ====================

@app.post("/api/signup", tags=["Authentication"])
async def signup(user: UserSignup):
    """
    Register a new customer account
    
    Creates a new customer with hashed password and default profile data.
    """
    # Check if customer exists
    existing = await customers_collection.find_one({"id": user.customer_id})
    if existing:
        raise HTTPException(status_code=400, detail="Customer ID already exists")
    
    # Create customer with hashed password
    hashed_password = pwd_context.hash(user.password)
    customer_data = {
        "id": user.customer_id,
        "password": hashed_password,
        "full_name": "Mona El-Sayed",
        "date_of_birth": "1994-07-22",
        "email": "mona.elsayed@email.com",
        "phone_number": "+20-111-987-6543",
        "address": {
            "street": "45 Corniche Road",
            "city": "Alexandria",
            "country": "Egypt"
        },
        "customer_since": "2020-09-18",
        "kyc_status": "Verified"
    }
    
    await customers_collection.insert_one(customer_data)
    
    return {
        "message": "Account created successfully",
        "customer_id": user.customer_id
    }


@app.post("/api/login", tags=["Authentication"])
async def login(user: UserLogin):
    """
    Authenticate user and return access token
    
    Validates credentials and returns JWT token for subsequent requests.
    """
    customer = await customers_collection.find_one({"id": user.customer_id})
    
    if not customer or not pwd_context.verify(user.password, customer["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user.customer_id})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "customer_id": user.customer_id,
        "name": customer.get("name", "")
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_text(
    query: ChatQuery,
    customer_id: str = Depends(verify_token)
):
    """
    Process text-based chat query
    
    Sends user query to the banking agent and returns AI response.
    """
    # Verify authorization
    if query.user_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    # Process with agent
    response = await agent.orchestrate(query=query.query, user_id=customer_id)
    
    # Save to chat history
    chat_record = {
        "customer_id": customer_id,
        "query": query.query,
        "response": response,
        "timestamp": datetime.utcnow().isoformat(),
        "type": "text"
    }
    await chat_history_collection.insert_one(chat_record)
    
    return ChatResponse(
        response=response,
        timestamp=chat_record["timestamp"]
    )


@app.post("/api/chat/voice", tags=["Chat"])
async def chat_voice(
    audio: UploadFile = File(...),
    user_id: str = Form(...),
    customer_id: str = Depends(verify_token)
):
    """
    Process voice-based chat query
    
    Transcribes audio using Google Gemini, processes query, and returns text response.
    Audio must be in English for proper transcription.
    """
    # Verify authorization
    if user_id != customer_id:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    
    try:
        # Read audio file
        audio_content = await audio.read()
        print(f"Received audio: {audio.filename}, bytes={len(audio_content)}")

        # Prepare audio for Google API
        audio_file = io.BytesIO(audio_content)
        audio_file.name = audio.filename or "audio.mp3"

        # Upload to Google Generative AI
        uploaded_file = genai_client.files.upload(
            file=audio_file,
            config={"mimeType": audio.content_type or "audio/mpeg"}
        )

        # Wait for processing
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai_client.files.get(name=uploaded_file.name)

        # Transcribe audio
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                genai.types.Content(
                    parts=[
                        genai.types.Part(text="""Transcribe this audio in ENGLISH ONLY. 
                            If the audio is not in English, respond with:
                            "LANGUAGE_ERROR: Please record in English"

                            Remove filler words and false starts.
                            If audio quality is too poor, respond with:
                            "AUDIO_QUALITY_ERROR: Please record in a quieter environment"

                            Otherwise, provide clean English transcription only."""),
                        genai.types.Part(file_data=genai.types.FileData(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type
                        ))
                    ]
                )
            ],
            config={
                "response_mime_type": "text/plain",
                "temperature": 0.2
            }
        )

        # Handle transcription errors
        if "LANGUAGE_ERROR" in response.text:
            response_text = "Please re-record your audio in English"
            transcribed_text = ""
        elif "AUDIO_QUALITY_ERROR" in response.text:
            response_text = "Please re-record your audio in a quiet space with clear speech"
            transcribed_text = ""
        else:
            transcribed_text = response.text
            response_text = await agent.orchestrate(query=transcribed_text, user_id=customer_id)

        # Save to chat history
        chat_record = {
            "customer_id": customer_id,
            "query": transcribed_text,
            "response": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "voice"
        }
        await chat_history_collection.insert_one(chat_record)
        
        return {
            "transcribed_query": transcribed_text,
            "response": response_text,
            "timestamp": chat_record["timestamp"]
        }
    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing error: {str(e)}")


@app.post("/api/chat/tts", tags=["Chat"])
async def text_to_speech(
    request: TTSRequest,
    customer_id: str = Depends(verify_token)
):
    """
    Convert text to speech audio
    
    Returns audio stream of the provided text using configured TTS provider.
    """
    try:
        tts = get_tts_service("openai")
        audio_data = await tts.synthesize(request.text, voice="nova")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=response.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


@app.get("/api/chat/history", tags=["Chat"])
async def get_chat_history(
    customer_id: str = Depends(verify_token),
    limit: int = 50
):
    """
    Retrieve chat history for authenticated user
    
    Returns up to {limit} most recent chat messages.
    """
    history = await chat_history_collection.find(
        {"customer_id": customer_id}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    # Convert ObjectId to string for JSON serialization
    for record in history:
        record["_id"] = str(record["_id"])
    
    return {"history": history}


@app.get("/api/verify", tags=["Authentication"])
async def verify_auth(customer_id: str = Depends(verify_token)):
    """
    Verify authentication token validity
    
    Returns user information if token is valid.
    """
    customer = await customers_collection.find_one({"id": customer_id})
    return {
        "authenticated": True,
        "customer_id": customer_id,
        "name": customer.get("name", "")
    }


@app.get("/api/config", tags=["System"])
async def get_config():
    """Get current STT/TTS provider configuration"""
    return {
        "stt_provider": STT_PROVIDER,
        "tts_provider": TTS_PROVIDER
    }


# ==================== Startup Events ====================
@app.on_event("startup")
async def startup_event():
    """Initialize database indexes on startup"""
    try:
        # Test MongoDB connection
        await client.admin.command('ping')
        print("MongoDB connection successful!")
        
        # Create indexes
        await customers_collection.create_index("id", unique=True)
        await transactions_collection.create_index([("account_id", 1), ("timestamp", -1)])
        await chat_history_collection.create_index([("customer_id", 1), ("timestamp", -1)])
        print("Database indexes created successfully")
        
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        print("Please ensure MongoDB is running on mongodb://localhost:27017")
        print("The application will start but database operations will fail.")


# ==================== Main ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)
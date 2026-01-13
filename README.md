# Banking Chatbot API Documentation

## Overview

The Banking Chatbot API is an AI-powered banking assistant featuring multi-agent orchestration, voice support, and RAG (Retrieval-Augmented Generation) capabilities. The system uses a sophisticated agent-based architecture to route queries intelligently and provide contextual, accurate responses.

**Base URL (Development):** `http://127.0.0.1:5000`  
**Base URL (Production):** `https://your-domain.com`

**Version:** 1.0.0

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Multi-Agent System](#multi-agent-system)
3. [Authentication](#authentication)
4. [API Endpoints](#api-endpoints)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)


---


### Technology Stack

- **Backend Framework:** FastAPI (Python 3.8+)
- **Agent Framework:** Google ADK (Agent Development Kit)
- **LLM:** Google Gemini 2.5 Flash
- **Database:** MongoDB (NoSQL)
- **Vector Store:** Qdrant
- **Authentication:** JWT (JSON Web Tokens)
- **Voice Processing:** 
  - STT: Google Gemini
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla/Framework)
- **Security:** bcrypt password hashing

---

## Multi-Agent System

### Agent Architecture

The system employs four specialized agents working in concert:

#### 1. **Orchestrator Agent** (Intent Classifier)
- **Role:** Analyzes user queries and routes to appropriate agents
- **Capabilities:**
  - Intent classification (Transaction, Product, Hybrid)
  - Query understanding and decomposition
  - Session management
- **Output:** Intent classification result

#### 2. **MCP Tools Agent** (Database Operations)
- **Role:** Handles database queries and transaction data
- **Capabilities:**
  - Customer account retrieval
  - Transaction history queries
  - Account balance checks
  - Real-time data access via MCP (Model Context Protocol)
- **Tools:** 
  - `get_customer_accounts`
  - `get_customer`
  - `get_account`
  - `load_memory`
- **Output:** Transaction data and account information

#### 3. **RAG Agent** (Knowledge Base)
- **Role:** Retrieves product information using RAG
- **Capabilities:**
  - Semantic search over bank products
  - Product recommendations
  - Banking policy information
  - FAQ responses
- **Tools:**
  - `similarity_search` (Vector DB)
  - `load_memory`
- **Output:** Product information and knowledge base content

#### 4. **Final Response Agent** (Synthesizer)
- **Role:** Combines outputs into natural, coherent responses
- **Capabilities:**
  - Context synthesis
  - Response formatting
  - Natural language generation
  - Conversational tone adaptation
- **Output:** Final user-facing response

### Agent Workflow

```
User Query → Orchestrator Agent
              │
              ├─→ [Transaction Intent] → MCP Tools Agent
              │                            │
              ├─→ [Product Intent]     → RAG Agent
              │                            │
              └─→ [Hybrid Intent]      → Both Agents
                                           │
                                           ▼
                                    Final Response Agent
                                           │
                                           ▼
                                      User Response
```

### Intent Types

1. **Transaction Intent**
   - Keywords: balance, transaction, account, payment, transfer
   - Routes to: MCP Tools Agent
   - Examples: "What's my balance?", "Show recent transactions"

2. **Product Intent**
   - Keywords: loan, credit card, savings, product, interest rate
   - Routes to: RAG Agent
   - Examples: "What credit cards do you offer?", "Tell me about savings accounts"

3. **Hybrid Intent**
   - Mixed queries requiring both data and knowledge
   - Routes to: Both MCP Tools + RAG Agents
   - Examples: "Can I get a loan based on my account balance?", "What cards am I eligible for?"

### Session Management

Each agent maintains separate sessions using ADK's session service:
- **Session Types:**
  - `orchestrator_session` - Intent classification history
  - `mcp_session` - Database query context
  - `rag_session` - Knowledge retrieval context
  - `final_response_session` - Response synthesis context

- **Memory Service:** In-memory storage with auto-save callbacks
- **State Persistence:** Session state saved after each agent interaction

---

## Authentication

The API uses JWT (JSON Web Token) based authentication with bcrypt password hashing.

### Token Flow
1. User registers via `/api/signup` or logs in via `/api/login`
2. Server returns JWT access token (60-minute expiration)
3. Include token in subsequent requests via `Authorization: Bearer <token>` header
4. Token validates user identity and permissions

### Security Features
- Passwords hashed using bcrypt (cost factor: 12)
- JWT tokens signed with HS256 algorithm
- Token expiration and refresh mechanism
- HTTPS encryption in production
- CORS protection with origin whitelisting

---

## API Endpoints

### Authentication

#### POST `/api/signup`

Register a new customer account.

**Request Body:**
```json
{
  "customer_id": "CUST001",
  "password": "SecurePass123!",
  "name": "John Doe",
  "email": "john.doe@email.com",
  "phone": "+1-555-123-4567"
}
```

**Response:** `200 OK`
```json
{
  "message": "Account created successfully",
  "customer_id": "CUST001"
}
```

**Errors:**
- `400` - Customer ID already exists

---

#### POST `/api/login`

Authenticate user and receive access token.

**Request Body:**
```json
{
  "customer_id": "CUST001",
  "password": "SecurePass123!"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "customer_id": "CUST001",
  "name": "John Doe"
}
```

**Errors:**
- `401` - Invalid credentials

---

#### GET `/api/verify`

Verify authentication token validity.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "authenticated": true,
  "customer_id": "CUST001",
  "name": "John Doe"
}
```

**Errors:**
- `401` - Invalid or expired token

---

### Chat

#### POST `/api/chat`

Send text-based query to the banking assistant.

**Multi-Agent Processing:**
1. Query analyzed by Orchestrator Agent
2. Routed to appropriate specialized agent(s)
3. Response synthesized by Final Response Agent

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "query": "What is my account balance?",
  "user_id": "CUST001"
}
```

**Response:** `200 OK`
```json
{
  "response": "Your current account balance is $5,432.10",
  "timestamp": "2026-01-13T14:30:00.123456"
}
```

**Agent Flow Example:**
```
User Query: "What is my account balance?"
  ↓
Orchestrator: [Transaction Intent Detected]
  ↓
MCP Agent: Queries database for account data
  ↓
Final Response: "Your current account balance is $5,432.10"
```

**Errors:**
- `401` - Invalid or expired token
- `403` - Unauthorized access (user_id doesn't match token)

---

#### POST `/api/chat/voice`

Send voice-based query to the banking assistant.

**Processing Pipeline:**
1. Audio uploaded and transcribed (Google Gemini STT)
2. Transcribed text processed by Multi-Agent System
3. Text response returned (can be converted to speech via `/api/chat/tts`)

**Headers:**
```
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Data:**
- `audio` (file): Audio file (MP3, WAV, FLAC, OGG)
- `user_id` (string): Customer ID

**Response:** `200 OK`
```json
{
  "transcribed_query": "What is my account balance",
  "response": "Your current account balance is $5,432.10",
  "timestamp": "2026-01-13T14:30:00.123456"
}
```

**Special Responses:**

*Language Error:*
```json
{
  "transcribed_query": "",
  "response": "Please re-record your audio in English",
  "timestamp": "2026-01-13T14:30:00.123456"
}
```

*Audio Quality Error:*
```json
{
  "transcribed_query": "",
  "response": "Please re-record your audio in a quiet space with clear speech",
  "timestamp": "2026-01-13T14:30:00.123456"
}
```

**Errors:**
- `401` - Invalid or expired token
- `403` - Unauthorized access
- `500` - Voice processing error

**Notes:**
- Audio must be in English
- Supported formats: MP3, WAV, FLAC, OGG
- Maximum file size: 25MB
- Optimal recording: 16kHz sample rate, mono channel

---

#### POST `/api/chat/tts`

Convert text response to speech audio.

**Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "text": "Your account balance is $5,432.10",
  "voice": "nova",
  "language": "en-US"
}
```

**Available Voices:**
- OpenAI: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer`
- Google: `en-US-Standard-A` through `en-US-Standard-J`

**Response:** `200 OK`
- Content-Type: `audio/mpeg`
- Returns audio stream (MP3 format)

**Errors:**
- `401` - Invalid or expired token
- `500` - TTS processing error

---

#### GET `/api/chat/history`

Retrieve chat history for authenticated user.

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (optional, default=50): Number of messages to return

**Response:** `200 OK`
```json
{
  "history": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "customer_id": "CUST001",
      "query": "What is my account balance?",
      "response": "Your current account balance is $5,432.10",
      "timestamp": "2026-01-13T14:30:00.123456",
      "type": "text"
    },
    {
      "_id": "507f1f77bcf86cd799439012",
      "customer_id": "CUST001",
      "query": "Show recent transactions",
      "response": "Here are your 5 most recent transactions...",
      "timestamp": "2026-01-13T14:25:00.123456",
      "type": "voice"
    }
  ]
}
```

**Errors:**
- `401` - Invalid or expired token

---

### System

#### GET `/api/config`

Get current STT/TTS provider configuration.

**Response:** `200 OK`
```json
{
  "stt_provider": "google",
  "tts_provider": "openai"
}
```

---

## Data Models

### UserSignup
```typescript
{
  customer_id: string;    // Unique customer identifier
  password: string;       // Password (will be hashed with bcrypt)
  name: string;          // Full name
  email: string;         // Email address
  phone: string;         // Phone number with country code
}
```

### UserLogin
```typescript
{
  customer_id: string;
  password: string;
}
```

### ChatQuery
```typescript
{
  query: string;         // User's question or request
  user_id: string;       // Customer ID (must match JWT token)
}
```

### ChatResponse
```typescript
{
  response: string;      // AI assistant response
  timestamp: string;     // ISO 8601 format (YYYY-MM-DDTHH:mm:ss.ffffff)
}
```

### VoiceResponse
```typescript
{
  transcribed_query: string;  // Transcribed text from audio
  response: string;           // AI assistant response
  timestamp: string;          // ISO 8601 format
}
```


### ChatHistory
```typescript
{
  history: [
    {
      _id: string;           // MongoDB ObjectId
      customer_id: string;   // Customer identifier
      query: string;         // User query
      response: string;      // Assistant response
      timestamp: string;     // ISO 8601 format
      type: "text" | "voice" // Interaction type
    }
  ]
}
```

---

## Error Handling

### Standard Error Response
```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Description | Common Causes |
|------|-------------|---------------|
| 200  | Success | Request completed successfully |
| 400  | Bad Request | Invalid input, customer already exists |
| 401  | Unauthorized | Invalid/expired token, wrong credentials |
| 403  | Forbidden | user_id doesn't match token |
| 500  | Internal Server Error | Agent failure, database error, external API error |

### Error Examples

**Authentication Error:**
```json
{
  "detail": "Invalid credentials"
}
```

**Token Expired:**
```json
{
  "detail": "Token expired"
}
```

**Multi-Agent Error:**
```json
{
  "detail": "Sorry, I couldn't process your request at this time."
}
```

### Retry Logic

```javascript
async function retryRequest(fn, maxRetries = 3) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * (i + 1)));
    }
  }
}

// Usage
const response = await retryRequest(() => 
  client.sendTextMessage('What is my balance?')
);
```

---


### Installation

```bash
# Clone repository
git clone <repository-url>
cd banking-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run MCP Server

python mcp_server.py
```
# Run the application
cd ..
python main.py
```

### Production Deployment

#### Using Gunicorn (HTTPS)
```bash
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:443 \
  --keyfile=/path/to/key.pem \
  --certfile=/path/to/cert.pem
```


### Security Best Practices

1. **Password Security**
   - Minimum 8 characters
   - Bcrypt hashing with cost factor 12
   - Never log passwords

2. **Token Security**
   - 60-minute expiration (configurable)
   - Stored securely in httpOnly cookies (recommended) or localStorage
   - Refresh token mechanism for long sessions


3. **CORS Configuration**
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://your-domain.com"],  # Specific origins
       allow_credentials=True,
       allow_methods=["GET", "POST"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```


5. **Input Validation**
   - Pydantic models validate all inputs
   - Sanitize user queries before processing
   - File upload size limits

6. **Database Security**
   - MongoDB authentication enabled
   - Separate read/write users
   - Connection encryption

---


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
5. [Frontend Integration](#frontend-integration)
6. [Data Models](#data-models)
7. [Error Handling](#error-handling)
8. [Setup & Configuration](#setup--configuration)
9. [Security & HTTPS](#security--https)

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
- **Security:** HTTPS/TLS, bcrypt password hashing

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

## Frontend Integration

### HTML/CSS/JavaScript Client

#### Project Structure
```
frontend/
├── index.html
├── css/
│   ├── main.css
│   ├── chat.css
│   └── auth.css
├── js/
│   ├── app.js
│   ├── auth.js
│   ├── chat.js
│   └── voice.js
└── assets/
    ├── images/
    └── icons/
```

#### Key CSS Classes

**Authentication Pages:**
```css
.auth-container {
  max-width: 400px;
  margin: 50px auto;
  padding: 30px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.auth-input {
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.auth-button {
  padding: 12px;
  background: #1976d2;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}
```

**Chat Interface:**
```css
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f5f5;
}

.message {
  margin-bottom: 15px;
  padding: 12px 16px;
  border-radius: 12px;
  max-width: 70%;
}

.message-user {
  background: #1976d2;
  color: white;
  margin-left: auto;
  text-align: right;
}

.message-assistant {
  background: white;
  color: #333;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.input-area {
  display: flex;
  gap: 10px;
  padding: 20px;
  background: white;
  border-top: 1px solid #e0e0e0;
}

.voice-button {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: #d32f2f;
  color: white;
  border: none;
  cursor: pointer;
}

.voice-button.recording {
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}
```

#### JavaScript API Client

```javascript
// API Client Configuration
const API_BASE_URL = 'https://your-domain.com/api';

class BankingAPIClient {
  constructor() {
    this.token = localStorage.getItem('auth_token');
    this.customerId = localStorage.getItem('customer_id');
  }

  // Authentication
  async login(customerId, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_id: customerId, password })
    });
    
    if (!response.ok) throw new Error('Login failed');
    
    const data = await response.json();
    this.token = data.access_token;
    this.customerId = data.customer_id;
    
    localStorage.setItem('auth_token', this.token);
    localStorage.setItem('customer_id', this.customerId);
    
    return data;
  }

  async signup(customerId, password, name, email, phone) {
    const response = await fetch(`${API_BASE_URL}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        customer_id: customerId, 
        password, 
        name, 
        email, 
        phone 
      })
    });
    
    if (!response.ok) throw new Error('Signup failed');
    return await response.json();
  }

  // Chat
  async sendTextMessage(query) {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ 
        query, 
        user_id: this.customerId 
      })
    });
    
    if (!response.ok) throw new Error('Chat request failed');
    return await response.json();
  }

  async sendVoiceMessage(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    formData.append('user_id', this.customerId);

    const response = await fetch(`${API_BASE_URL}/chat/voice`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`
      },
      body: formData
    });
    
    if (!response.ok) throw new Error('Voice request failed');
    return await response.json();
  }

  async textToSpeech(text, voice = 'nova') {
    const response = await fetch(`${API_BASE_URL}/chat/tts`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ text, voice, language: 'en-US' })
    });
    
    if (!response.ok) throw new Error('TTS request failed');
    return await response.blob();
  }

  async getChatHistory(limit = 50) {
    const response = await fetch(
      `${API_BASE_URL}/chat/history?limit=${limit}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`
        }
      }
    );
    
    if (!response.ok) throw new Error('History request failed');
    return await response.json();
  }
}

// Usage Example
const client = new BankingAPIClient();

// Login
await client.login('CUST001', 'password123');

// Send message
const response = await client.sendTextMessage('What is my balance?');
console.log(response.response);

// Voice recording
const mediaRecorder = new MediaRecorder(stream);
const chunks = [];
mediaRecorder.ondataavailable = e => chunks.push(e.data);
mediaRecorder.onstop = async () => {
  const blob = new Blob(chunks, { type: 'audio/webm' });
  const result = await client.sendVoiceMessage(blob);
  console.log(result.response);
};
```

#### WebSocket Support (Future Enhancement)

For real-time streaming responses:

```javascript
const ws = new WebSocket('wss://your-domain.com/ws/chat');

ws.onopen = () => {
  ws.send(JSON.stringify({
    token: client.token,
    query: 'What is my balance?'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'agent_update') {
    console.log(`Agent: ${data.agent_name}`);
  } else if (data.type === 'response_chunk') {
    appendToUI(data.text);
  }
};
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

### TTSRequest
```typescript
{
  text: string;          // Text to convert to speech
  voice?: string;        // Voice name (default: "nova")
  language: string;      // Language code (default: "en-US")
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

## Setup & Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Security
SECRET_KEY=your-secret-key-change-in-production-min-32-chars

# Database
MONGODB_URL=mongodb://127.0.0.1:27017
DATABASE_NAME=banking_db

# API Keys
GOOGLE_API_KEY=your-google-api-key
VOICE_GOOGLE_API_KEY=your-google-voice-api-key
WHISPER_API_KEY=your-openai-api-key

# Service Providers
STT_PROVIDER=google              # Options: openai, google, azure
TTS_PROVIDER=openai              # Options: openai, google, azure

# Token Configuration
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALGORITHM=HS256

# Multi-Agent Configuration
APP_NAME=banking_chatbot
MODEL_NAME=gemini-2.5-flash
TEMPERATURE=0.3

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=bank_products_collection

# HTTPS Configuration (Production)
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

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

# Install frontend dependencies (if using build tools)
cd frontend
npm install
npm run build

# Start MongoDB
mongod --dbpath /path/to/data

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

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

#### Using Nginx (Reverse Proxy)
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Interactive API Documentation

Once running, access:
- **Swagger UI:** `https://your-domain.com/docs`
- **ReDoc:** `https://your-domain.com/redoc`

---

## Security & HTTPS

### HTTPS Setup

#### Development (Self-Signed Certificate)
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 \
  -keyout key.pem -out cert.pem \
  -days 365 -nodes

# Run with HTTPS
uvicorn main:app --host 0.0.0.0 --port 443 \
  --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```

#### Production (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
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

3. **HTTPS/TLS**
   - TLS 1.3 minimum
   - Strong cipher suites
   - HSTS headers enabled

4. **CORS Configuration**
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


# Contract Analysis Platform

This project is a GenAI-powered platform that analyzes legal contracts, extracts key clauses, and evaluates contract health. It features a FastAPI backend, a Streamlit frontend, and integrates with LangChain for managing prompt templates and orchestrating LLM interactions. The system connects to OpenAI's API for language processing and uses MongoDB for data storage

## Features

- **User Authentication**: JWT-based authentication system
- **Contract Analysis**: GenAI-powered PDF contract analysis with clause extraction
- **Contract Evaluation**: GenAI-powered contract health assessment
- **Detailed Approval Diagnostics**: Risk level, missing critical clauses, specific issues, and required changes
- **Bilingual AI Responses**: English and Arabic output support
- **OCR for Scanned Contracts**: English/Arabic OCR fallback for image-based PDFs
- **Client Management**: CRUD operations for clients and contracts
- **Admin Dashboard**: System metrics and logs monitoring
- **Real-time Processing**: Async processing with background tasks

## Tech Stack

- **Backend**: FastAPI, MongoDB
- **Frontend**: Streamlit
- **GenAI**: OpenAI GPT-4
- **Authentication**: JWT with bcrypt
- **Containerization**: Docker & Docker Compose

## Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Python 3.11+ (for local development)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd contract-analysis-platform
```

### 2. Environment Configuration

Copy the example environment file and update with your values:

```bash
cp .env.example .env
```

Edit `.env` file with your configurations:
```env
SECRET_KEY=your-super-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
MONGODB_URL=mongodb://admin:admin123@mongodb:27017/contract_analysis?authSource=admin
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:8501
```

### 3. Docker Deployment (Recommended)

Build and run all services:

```bash
docker-compose up --build
```

This will start:
- **MongoDB**: Port 27017
- **Backend API**: Port 8000
- **Frontend**: Port 8501

### 4. Local Development Setup

If you prefer to run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Start MongoDB (using Docker)
docker-compose up -d mongodb 

# Set environment variables
export API_BASE_URL=http://localhost:8000

# Run backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run frontend (in another terminal)
streamlit run frontend/streamlit_app.py --server.port 8501
```

**Note**: When running locally, make sure to set `API_BASE_URL=http://localhost:8000` for the frontend to connect to the backend.

## Access the Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **API Redoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login (returns JWT token)

### Contract Analysis
- `POST /genai/analyze-contract` - Upload PDF, extract text (native or OCR), and extract clauses
- `POST /genai/evaluate-contract` - Evaluate contract health (English/Arabic response)

### Client & Contract Management
- `POST /clients` - Create new client
- `GET /clients/{id}/contracts` - Get client contracts
- `POST /contracts` - Create new contract
- `GET /contracts/{id}` - Get contract details
- `PUT /contracts/{id}` - Update contract
- `DELETE /contracts/{id}` - Delete contract
- `POST /contracts/{id}/init-genai` - Trigger AI analysis
- `POST /contracts/{id}/chat` - Ask AI questions about a specific contract

### System Monitoring
- `GET /logs` - Get system logs (with filters)
- `GET /metrics` - Get system metrics
- `GET /healthz` - Health check
- `GET /readyz` - Readiness check

## Authentication

All endpoints except `/auth/*`, `/healthz`, and `/readyz` require JWT authentication.

1. Register or login to get access token
2. Include token in Authorization header: `Bearer <token>`

## Usage Guide

### 1. Register/Login
- Access the frontend at http://localhost:8501
- Register a new account or login with existing credentials

### 2. Analyze Contract
- Navigate to "Contract Analysis" tab
- Create a new client or select an existing one
- Upload a PDF contract file
- Select response language (English/Arabic) and OCR preference
- Click "Analyze Contract Clauses" to extract clauses using AI
- Click "Evaluate Contract Health" to get AI assessment
- Review structured diagnostics (risk level, missing clauses, specific issues, required changes)
- Use "Run Complete Analysis Pipeline" for full automated analysis
- Use "Ask AI About This Contract" to ask natural-language questions about the currently selected contract

### 3. Manage Data
- Use "Data Management" tab to view existing clients and contracts
- The main workflow is through the "Contract Analysis" tab

### 4. Monitor System
- Access "Admin Dashboard" for system metrics and logs
- View health checks, request metrics, and system logs
- Filter logs by user, endpoint, or status

## Testing

The API includes comprehensive error handling and logging. All actions are logged with timestamps and user information.

### Health Checks
- `GET /healthz` - Basic health check
- `GET /readyz` - Database connectivity check

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key (required) | No default |
| `OPENAI_API_KEY` | OpenAI API key | Required for GenAI endpoints |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:8501` |
| `MONGODB_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | `30` |

## Database Schema

### Collections:
- **users**: User accounts with hashed passwords
- **clients**: Client information
- **contracts**: Contract metadata and content
- **contract_analyses**: AI analysis results
- **logs**: System activity logs

## Docker Services

The docker-compose setup includes:

- **MongoDB**: Document database with persistent storage
- **Backend**: FastAPI application with auto-reload
- **Frontend**: Streamlit web interface with proper container networking

## Security Features

- Password hashing with bcrypt
- JWT token-based authentication
- CORS protection
- Input validation with Pydantic
- Error handling without sensitive data exposure

## Monitoring & Logging

- Request/response logging
- User activity tracking
- Error tracking with timestamps
- System metrics (success rate, request counts)

## Development

### Adding New Endpoints

1. Add route to `main.py`
2. Include authentication dependency: `Depends(get_current_user)`
3. Add logging for the action
4. Update frontend if needed

### Database Operations

The app uses Motor (async MongoDB driver) for database operations. All operations are async and properly handle errors.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Troubleshooting

### Common Issues:

1. **OpenAI API Key**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Database Connection**: Check MongoDB is running
3. **Port Conflicts**: Ensure ports 8000, 8501, 27017, 6379 are available
4. **Docker Issues**: Run `docker-compose down` and `docker-compose up --build`

### Logs:
- Backend logs: `docker-compose logs backend`
- Frontend logs: `docker-compose logs frontend`
- Database logs: `docker-compose logs mongodb`

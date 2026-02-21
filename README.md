# RepoMind AI - Phase 2: Code Processing Engine

A GitHub repository analysis tool with advanced code parsing, chunking, and dependency mapping.

## 🚀 Features

### Phase 1 (Repository Ingestion)
- **Repository Ingestion**: Fetch and analyze GitHub repositories
- **File Filtering**: Automatically filters irrelevant files (node_modules, build artifacts, etc.)
- **Language Detection**: Identifies programming languages from file extensions
- **Local Storage**: Persists analysis results in browser localStorage

### Phase 2 (Code Processing Engine)
- **Language-Specific Parsing**: AST parsing for Python, JavaScript/TypeScript, Java, and Go
- **Logical Chunking**: Splits code into 300-800 token chunks respecting function/class boundaries
- **Token Estimation**: OpenAI-compatible token counting with tiktoken
- **Dependency Mapping**: Builds dependency graphs and detects circular dependencies
- **Repository Indexing**: Creates searchable index with metadata and statistics
- **Responsive UI**: Clean, modern interface with processing results

## 📋 Tech Stack

### Backend
- **FastAPI** (Python 3.10+)
- **httpx** for API calls
- **python-dotenv** for environment management
- **Pydantic** for data validation
- **tiktoken** for OpenAI-compatible token counting
- **networkx** for dependency graph analysis
- **javalang** for Java parsing
- **tree-sitter** for JavaScript/TypeScript parsing

### Frontend
- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **Fetch API**

## 🛠️ Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create environment file:
```bash
cp ../.env.example .env
```

5. Edit `.env` file (optional):
```env
GITHUB_TOKEN=your_github_token_here
GROQ_API_KEY=your_groq_api_key_here
```

6. Start the backend server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

## 🌐 Usage

### Phase 1: Repository Analysis

1. Open your browser and navigate to `http://localhost:3000`
2. Enter a GitHub repository URL (e.g., `https://github.com/owner/repo`)
3. Click "Analyze Repository"
4. View the file analysis results
5. Data persists across browser sessions

### Phase 2: Code Processing

1. After Phase 1 analysis, click "Process Repository" or navigate to `/process`
2. Wait for processing to complete (parsing, chunking, dependency analysis)
3. View detailed processing results:
   - Token statistics and chunk efficiency
   - Language distribution
   - Dependency graphs and circular dependencies
   - Processing metrics

## 📊 API Endpoints

### POST /api/analyze
Analyzes a GitHub repository (Phase 1).

**Request:**
```json
{
  "repo_url": "https://github.com/owner/repo"
}
```

**Response:**
```json
{
  "repo": "owner/repo",
  "files": [
    {
      "path": "src/main.py",
      "size": 1200,
      "language": "python",
      "download_url": "..."
    }
  ]
}
```

### POST /api/process
Processes repository with Phase 2 analysis.

**Request:**
```json
{
  "repo": "owner/repo",
  "files": [...] // Phase 1 output
}
```

**Response:**
```json
{
  "repo": "owner/repo",
  "total_files": 45,
  "total_chunks": 127,
  "total_tokens": 45678,
  "max_tokens": 780,
  "avg_tokens": 359.8,
  "languages": {"python": 25, "javascript": 15, "typescript": 5},
  "chunks": [...],
  "dependencies": {...}
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "phase": "Phase 2"
}
```

## 🧪 Testing

### Backend Tests
Run tests from the backend directory:
```bash
cd backend
pytest test_main.py -v  # Phase 1 tests
pytest test_processing.py -v  # Phase 2 tests
```

### Phase 2 Test Coverage
- Python AST parsing and chunking
- Token counting accuracy
- Dependency graph construction
- Repository indexing
- Error handling for malformed code

## 📁 Project Structure

```
repomind/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── github.py            # GitHub API integration
│   ├── schemas.py           # Pydantic models
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Python dependencies
│   ├── test_main.py         # Phase 1 tests
│   ├── test_processing.py   # Phase 2 tests
│   └── processing/         # Phase 2 processing modules
│       ├── __init__.py
│       ├── parser.py        # Language-specific AST parsing
│       ├── chunker.py      # Logical code chunking
│       ├── tokenizer.py     # Token estimation
│       ├── dependency.py   # Dependency mapping
│       └── indexer.py      # Repository indexing
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Home page
│   │   ├── analyze/
│   │   │   └── page.tsx     # Phase 1 analysis results
│   │   ├── process/
│   │   │   └── page.tsx     # Phase 2 processing results
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Global styles
│   ├── lib/
│   │   ├── storage.ts       # localStorage utilities
│   │   └── config.ts       # Configuration
│   ├── types/
│   │   └── index.ts         # TypeScript types
│   ├── package.json         # Node.js dependencies
│   ├── next.config.js       # Next.js configuration
│   ├── tailwind.config.js   # Tailwind configuration
│   └── tsconfig.json        # TypeScript configuration
├── .env.example             # Environment variables template
└── README.md               # This file
```

## 🔧 Configuration

### Environment Variables

- `GITHUB_TOKEN`: Optional GitHub personal access token for higher API rate limits
- `GROQ_API_KEY`: Groq API key (for future AI analysis features)
- `NEXT_PUBLIC_API_URL`: Frontend API URL (default: http://localhost:8000)

### File Filtering

The system automatically ignores:
- `node_modules/`, `.git/`, `dist/`, `build/`, `__pycache__/`
- `.env`, `.lock` files
- Image files (`.png`, `.jpg`, `.mp4`, etc.)
- Archive files (`.zip`, `.pdf`, etc.)
- Files larger than 500KB (Phase 1) or 1MB (Phase 2)

### Memory Limits

Phase 2 processing is designed to be memory-efficient:
- Maximum RAM usage: < 1GB
- Large files are skipped automatically
- Processing is parallelized when possible
- Timeout protection prevents hanging

## 🚨 Limitations

- Only analyzes public repositories
- No authentication system
- No vector database or AI analysis (Phase 3)
- Rate limited by GitHub API (60 requests/hour without token)
- Large repositories (>1000 files) may take longer to process

## 🔄 Next Steps (Phase 3)

- AI-powered code analysis
- Vector database integration
- Advanced filtering options
- User authentication
- Repository comparison features
- Semantic search capabilities

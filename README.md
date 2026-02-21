# RepoMind AI - Phase 1

A GitHub repository analysis tool built with FastAPI and Next.js.

## 🚀 Features

- **Repository Ingestion**: Fetch and analyze GitHub repositories
- **File Filtering**: Automatically filters irrelevant files (node_modules, build artifacts, etc.)
- **Language Detection**: Identifies programming languages from file extensions
- **Local Storage**: Persists analysis results in browser localStorage
- **Responsive UI**: Clean, modern interface with Tailwind CSS

## 📋 Tech Stack

### Backend
- **FastAPI** (Python 3.10+)
- **httpx** for API calls
- **python-dotenv** for environment management
- **Pydantic** for data validation

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

1. Open your browser and navigate to `http://localhost:3000`
2. Enter a GitHub repository URL (e.g., `https://github.com/owner/repo`)
3. Click "Analyze Repository"
4. View the file analysis results
5. Data persists across browser sessions

## 📊 API Endpoints

### POST /api/analyze
Analyzes a GitHub repository.

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

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

## 🧪 Testing

### Backend Tests
Run tests from the backend directory:
```bash
cd backend
pytest test_main.py -v
```

### Frontend Testing
The frontend includes basic validation and error handling that can be tested manually through the UI.

## 📁 Project Structure

```
repomind/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── github.py            # GitHub API integration
│   ├── schemas.py           # Pydantic models
│   ├── config.py            # Configuration
│   ├── requirements.txt     # Python dependencies
│   └── test_main.py         # Tests
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Home page
│   │   ├── analyze/
│   │   │   └── page.tsx     # Analysis results page
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Global styles
│   ├── lib/
│   │   └── storage.ts       # localStorage utilities
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

### File Filtering

The system automatically ignores:
- `node_modules/`, `.git/`, `dist/`, `build/`, `__pycache__/`
- `.env`, `.lock` files
- Image files (`.png`, `.jpg`, `.mp4`, etc.)
- Archive files (`.zip`, `.pdf`, etc.)
- Files larger than 500KB

## 🚨 Limitations

- Only analyzes public repositories
- No authentication system
- No vector database or AI analysis (Phase 2)
- Rate limited by GitHub API (60 requests/hour without token)

## 📝 License

This project is for educational purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 🔄 Next Steps (Phase 2)

- AI-powered code analysis
- Vector database integration
- Advanced filtering options
- User authentication
- Repository comparison features

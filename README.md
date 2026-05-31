# Job Hunter AI - Building with AI Agents

> An open workshop project by **AI Lagos** in partnership with **ALX** teaching developers and students how to build products, apps, and webapps using AI Agents.

## 📋 Overview

**Job Hunter AI** is a full-stack web application that demonstrates practical AI Agent architecture in action. It automatically searches for job opportunities across multiple platforms, analyzes job listings using Google's Gemini AI, matches them against your CV, and sends personalized recommendations via email.

This project serves as a hands-on learning resource for understanding how to integrate AI agents into real-world applications.

## ✨ Features

- **🔍 Multi-Source Job Search**: Aggregates job listings from:
  - Remotive
  - Arbeitnow
  - The Muse

- **🤖 AI-Powered Analysis**: Uses Google Gemini AI to:
  - Understand job requirements
  - Extract key qualifications
  - Score job matches against your CV
  - Generate personalized insights

- **📄 CV Intelligent Matching**: 
  - Upload your PDF resume
  - AI analyzes your skills and experience
  - Matches against job listings with accuracy scoring
  - Tailors job descriptions to your background

- **📧 Email Notifications**:
  - Automated email delivery of matched jobs
  - Personalized recommendations
  - Built with Resend email service

- **⏰ Scheduled Automation**:
  - Runs background jobs on schedule using APScheduler
  - Continuous job monitoring and matching
  - State persistence with JSON storage

- **💻 Modern Dashboard**:
  - Clean, responsive UI built with vanilla HTML/CSS/JavaScript
  - Real-time job card display
  - Match scoring visualization
  - CV upload and management
  - Sidebar navigation

## 🛠️ Tech Stack

### Backend
- **Flask** 3.0.3 - Web framework
- **Google Generative AI** (Gemini) - AI analysis and matching
- **APScheduler** - Background job scheduling
- **PyPDF2** - CV/Resume parsing
- **Resend** - Email service
- **Python-dotenv** - Environment configuration

### Frontend
- Vanilla HTML5
- CSS3 (responsive design)
- JavaScript (no external frameworks)

### APIs Integrated
- Remotive Job API
- Arbeitnow API
- The Muse API
- Google Generative AI API
- Resend Email API

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- API Keys for:
  - Google Generative AI (Gemini)
  - Resend Email Service
  - Optional: Individual job API keys

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/elmustapha100/jobhunter_ALX.git
   cd jobhunter_ALX
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```
   GOOGLE_API_KEY=your_gemini_api_key
   RESEND_API_KEY=your_resend_api_key
   ```

5. **Run the application**
   ```bash
   ./start.sh
   ```
   
   Or manually:
   ```bash
   python app.py
   ```

6. **Access the dashboard**
   - Open your browser to: `http://localhost:5000`

## 🎓 Learning Outcomes

This project demonstrates:

1. **AI Agent Architecture**: How to design and implement autonomous AI agents
2. **API Integration**: Connecting multiple external APIs
3. **Intelligent Matching**: Using AI to make smart decisions
4. **Automation**: Scheduling and running background tasks
5. **Full-Stack Development**: Backend AI logic with frontend UI
6. **State Management**: Persisting data and agent state
7. **Email Integration**: Notifying users of AI-driven results

## 📁 Project Structure

```
jobhunter_ALX/
├── app.py                 # Flask backend and AI agent logic
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (keep secret!)
├── .gitignore            # Git ignore rules
├── start.sh              # Launcher script
├── templates/
│   └── index.html        # Dashboard UI
├── uploads/              # User CV uploads
└── state.json            # Application state persistence
```

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Google Gemini AI
GOOGLE_API_KEY=your_api_key_here

# Resend Email Service
RESEND_API_KEY=your_resend_api_key_here

# Application
FLASK_ENV=development
DEBUG=True
```

### Adding Your Information

1. Upload your CV via the dashboard
2. Configure your email preferences
3. Customize job search criteria
4. Set matching thresholds

## 🤖 How the AI Agent Works

1. **Search Phase**: Scrapes job listings from multiple APIs
2. **Extraction Phase**: Parses job requirements and qualifications
3. **Analysis Phase**: Uses Gemini AI to understand job needs
4. **CV Matching Phase**: Compares CV content against job requirements
5. **Scoring Phase**: Generates match scores (0-100%)
6. **Notification Phase**: Sends top matches via email
7. **State Update Phase**: Stores results for dashboard display

## 🚨 Security Notes

⚠️ **Never commit your `.env` file!** It contains sensitive API keys.

- Add `.env` to `.gitignore`
- Use environment variables for all secrets
- Rotate API keys if accidentally exposed
- Use `.env.example` for documentation

## 📝 Common Commands

```bash
# Run the application
python app.py

# Run with the launcher script
./start.sh

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate virtual environment
deactivate

# Check git status
git status

# View recent commits
git log --oneline -10
```

## 🐛 Troubleshooting

**API Keys not working?**
- Verify keys are correctly set in `.env`
- Check API key permissions and quotas
- Ensure keys haven't expired

**No jobs found?**
- Check internet connection
- Verify job APIs are accessible
- Review API rate limits

**Email not sending?**
- Verify Resend API key is correct
- Check email configuration
- Review Resend dashboard for errors

## 🤝 Contributing

This is an educational project. Contributions and improvements are welcome!

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📚 Resources

- [Google Generative AI Documentation](https://ai.google.dev/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [AI Lagos Community](https://ailagos.com)
- [ALX Africa](https://www.alxafrica.com)

## 📄 License

This project is part of the AI Lagos x ALX open workshop initiative. Feel free to use it for learning and educational purposes.

## 🙏 Acknowledgments

- **AI Lagos** - Community and workshop hosting
- **ALX Africa** - Partnership and educational support
- **Google Generative AI** - AI capabilities
- All contributors and learners in this workshop

---



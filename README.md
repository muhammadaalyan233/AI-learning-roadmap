# AI-learning-roadmap
# 🧭 AI Learning Roadmap Generator

A Streamlit app that generates a personalised, phase-by-phase learning roadmap using Google's Gemini Flash model.

Enter a **field**, your **skill level** (Beginner / Intermediate / Advanced), the **time you have** and your **weekly study hours**. The app returns a roadmap with phases, topics, resources, projects, milestones and a capstone project. You can download it as Markdown.

## Features
- Structured JSON output from Gemini, validated before display (retries on malformed output)
- Phases that fit your total time (weeks or months)
- Collapsible phase cards with topics, resources, project and milestone
- Markdown download
- API key via Streamlit secrets, environment variable, or the sidebar

## Project structure
```
.
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Run locally
```bash
git clone https://github.com/<your-username>/ai-roadmap-generator.git
cd ai-roadmap-generator

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Get a free API key at <https://aistudio.google.com/apikey>, then either:

**Option A - secrets file (recommended)**
Create `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "your-key-here"
# optional
# GEMINI_MODEL = "gemini-3.5-flash"
```

**Option B - environment variable**
```bash
export GEMINI_API_KEY="your-key-here"     # Windows PowerShell: $env:GEMINI_API_KEY="your-key-here"
```

**Option C** - paste the key into the sidebar when the app opens.

Start the app:
```bash
streamlit run app.py
```

## Changing the model
The default is `gemini-3.5-flash`. Google retires older Flash models regularly (for example `gemini-2.5-flash` is scheduled to shut down on 16 Oct 2026). If you get a "model not found" error, check <https://ai.google.dev/gemini-api/docs/deprecations>, then set `GEMINI_MODEL` in secrets or edit the model box in the sidebar. No code change needed.

## Deploy on Streamlit Community Cloud
1. Push this repo to GitHub (public or private).
2. Go to <https://share.streamlit.io> and sign in with GitHub.
3. Click **Create app** → choose your repo, branch `main`, main file `app.py`.
4. Open **Advanced settings → Secrets** and paste:
   ```toml
   GEMINI_API_KEY = "your-key-here"
   ```
5. Click **Deploy**. Your app gets a public `*.streamlit.app` URL.

## Security notes
- Never commit your API key. `.streamlit/secrets.toml` and `.env` are in `.gitignore`.
- A public deployment uses *your* key and quota. Consider leaving the secret unset so visitors enter their own key in the sidebar, or set quota limits in Google AI Studio.

## Limitations
- Roadmaps are AI-generated. Verify resources and time estimates before relying on them.
- Resource names are suggestions; links are intentionally not generated to avoid broken or invented URLs.

## License
MIT

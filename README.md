# elder-guardian-ai

AI-powered elder financial exploitation early-warning system.

A family member uploads a CSV of an elderly person's bank transactions(Actual product will use Plaid to link bank account securely). A multi-agent AI pipeline (LangGraph + scikit-learn + PyTorch + NetworkX) scores exploitation risk, and if the risk score exceeds 65, sends an SMS + email alert to a trusted emergency contact with a plain-English explanation written by Claude.

## Stack
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend:** Python FastAPI
- **Pipeline:** LangGraph multi-agent (5 agents)
- **ML:** Isolation Forest, LSTM Autoencoder, NetworkX graph scoring, SHAP
- **LLM:** Anthropic Claude
- **Database:** Supabase (PostgreSQL + Auth)
- **Alerts:** Twilio (SMS), Resend (email)
- **Hosting:** Vercel (frontend), Railway (backend)

## Status
Phase 1 - thin slice in progress.

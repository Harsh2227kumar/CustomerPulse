# CustomerPulse AI — GitHub Rules & Development Guidelines

> Enterprise-grade team workflow and development standards for CustomerPulse AI

---

# 1. Repository Information

## Repository Name

```text
customerpulse-ai
```

## Repository Visibility

- Private during development
- Public later if required

---

# 2. Branching Strategy

## Main Branches

```text
main
develop
```

---

## Branch Purpose

### `main`

Production-ready stable branch.

Rules:
- No direct pushes
- Only reviewed PR merges
- Used for final deployment/demo

---

### `develop`

Main collaborative development branch.

Rules:
- All completed features merge here first
- Active integration branch

---

## Feature Branch Naming

Each developer MUST create separate feature branches.

Format:

```text
feature/<feature-name>
```

Examples:

```text
feature/dashboard-ui
feature/complaint-form
feature/cfpb-ingestion
feature/websocket-service
feature/churn-prediction
```

---

# 3. Mandatory Git Workflow

## Step 1 — Pull Latest Changes

```bash
git checkout develop
git pull origin develop
```

---

## Step 2 — Create Feature Branch

```bash
git checkout -b feature/my-feature
```

---

## Step 3 — Work & Commit

```bash
git add .
git commit -m "feat: added complaint submission API"
```

---

## Step 4 — Push Branch

```bash
git push origin feature/my-feature
```

---

## Step 5 — Create Pull Request

```text
feature/my-feature → develop
```

---

## Step 6 — Code Review

- PR must be reviewed
- Fix conflicts if any
- Merge only after approval

---

# 4. Branch Protection Rules

## Protect `main`

Enable:

- Require pull request before merging
- Require approvals
- Restrict direct pushes
- Prevent force pushes
- Require status checks

---

## Protect `develop`

Enable:

- Require pull request
- Prevent force pushes

---

# 5. Team Responsibilities

| Member | Responsibility |
|---|---|
| Harsh | Backend + API |
| Yash | Data ingestion + Database |
| Atharva | Frontend |
| Sparsh | DevOps + Deployment |

---

# 6. Mandatory Project Structure

```text
customerpulse-ai/
│
├── frontend/
├── backend/
├── scripts/
├── infra/
├── docs/
├── shared/
├── .github/
├── docker-compose.yml
├── .env.template
├── .gitignore
├── README.md
└── LICENSE
```

---

# 7. Detailed Project Structure

```text
customerpulse-ai/                      # Root project directory
│
├── frontend/                         # React frontend application
│   ├── public/                       # Static public assets
│   │
│   ├── src/                          # Main frontend source code
│   │   ├── api/                      # API calls to backend
│   │   ├── assets/                   # Images, icons, fonts
│   │   ├── components/               # Reusable UI components
│   │   ├── pages/                    # Application pages
│   │   ├── layouts/                  # Shared layouts
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── context/                  # React Context providers
│   │   ├── routes/                   # Route definitions
│   │   ├── utils/                    # Helper functions
│   │   ├── styles/                   # CSS and styling
│   │   ├── types/                    # TypeScript interfaces
│   │   └── main.tsx                  # Frontend entry point
│   │
│   ├── package.json                  # Frontend dependencies
│   └── vite.config.ts                # Vite configuration
│
├── backend/                          # FastAPI backend
│   ├── app/
│   │   ├── api/                      # API endpoints
│   │   ├── core/                     # Configs & auth
│   │   ├── models/                   # SQLAlchemy models
│   │   ├── schemas/                  # Pydantic schemas
│   │   ├── services/                 # Business logic
│   │   ├── websocket/                # WebSocket handlers
│   │   ├── ai/                       # AI processing modules
│   │   ├── db/                       # Database setup
│   │   ├── utils/                    # Backend helpers
│   │   └── main.py                   # Backend entry point
│   │
│   ├── requirements.txt              # Python dependencies
│   └── Dockerfile                    # Backend Docker config
│
├── scripts/                          # Utility scripts
│   ├── seed_cfpb.py                  # Seed CFPB complaint data
│   ├── generate_embeddings.py        # Generate vector embeddings
│   └── cleanup.py                    # Cleanup scripts
│
├── infra/                            # Infrastructure configs
│   ├── nginx/                        # Nginx configs
│   ├── docker/                       # Docker configs
│   ├── terraform/                    # Terraform IaC
│   └── aws/                          # AWS deployment configs
│
├── docs/                             # Documentation
│   ├── architecture/                 # System architecture docs
│   ├── api/                          # API docs
│   ├── diagrams/                     # DFD/UML diagrams
│   └── reports/                      # Reports and presentations
│
├── shared/                           # Shared resources
│   ├── schema/                       # Shared JSON schema
│   ├── constants/                    # Shared constants
│   └── types/                        # Shared types/interfaces
│
├── .github/                          # GitHub configurations
│   ├── workflows/                    # GitHub Actions workflows
│   │   ├── backend-ci.yml
│   │   ├── frontend-ci.yml
│   │   └── deploy.yml
│   │
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docker-compose.yml                # Multi-container setup
├── .env.template                     # Environment variable template
├── .gitignore                        # Git ignored files
├── README.md                         # Main documentation
└── LICENSE                           # License file
```

---

# 8. API Contract Rules (CRITICAL)

The API schema is the SINGLE SOURCE OF TRUTH.

Location:

```text
shared/schema/
```

Rules:
- No random API changes
- No key renaming without discussion
- Frontend and backend must follow same schema

---

# 9. Commit Message Rules

## Format

```text
type: message
```

---

## Examples

```text
feat: added websocket notification service
fix: resolved database connection issue
docs: updated architecture documentation
refactor: optimized AI processing service
style: improved dashboard spacing
```

---

# 10. Pull Request Rules

Every PR must include:

- What changed
- Why it changed
- Screenshots (if frontend)
- API changes
- Database changes
- Testing completed

---

# 11. GitHub Issues Rules

Use GitHub Issues for ALL tasks.

## Recommended Labels

```text
frontend
backend
database
deployment
AI
bug
urgent
enhancement
documentation
```

---

# 12. Environment Variable Rules

## NEVER Upload

```text
.env
AWS keys
Anthropic API key
SSH keys
Database passwords
```

---

## Use `.env.template`

Example:

```env
DATABASE_URL=
ANTHROPIC_API_KEY=
REDIS_URL=
S3_BUCKET_NAME=
```

---

# 13. Mandatory `.gitignore`

```gitignore
node_modules/
.env
.venv/
dist/
build/
__pycache__/
```

---

# 14. Docker Rules

Every service must run independently.

Required containers:

- Frontend
- Backend
- Redis
- PostgreSQL (local or AWS RDS)

---

# 15. CI/CD Rules

Use GitHub Actions.

## Frontend Pipeline

- Install dependencies
- Lint
- Build

---

## Backend Pipeline

- Install dependencies
- Run tests
- Validate imports

---

# 16. Coding Standards

## General Rules

- Write modular code
- Avoid large files
- Use reusable components
- Separate business logic from UI
- Use environment variables properly

---

## Frontend Rules

- Reusable components only
- Avoid duplicated code
- Use TypeScript interfaces
- Use centralized API services

---

## Backend Rules

- Keep API routes clean
- Business logic goes inside `services/`
- AI logic stays inside `ai/`
- Validate all requests using Pydantic

---

# 17. AI Development Rules

Location:

```text
backend/app/ai/
```

Rules:
- Keep prompts centralized
- Separate AI providers from business logic
- Store confidence score logic separately
- Never hardcode responses

---

# 18. Database Rules

- Use AWS RDS as shared DB
- No local SQLite databases
- Use migrations properly
- Do not directly modify production tables

---

# 19. Security Rules

## Never Commit

- API keys
- Passwords
- Tokens
- SSH keys

---

## Always Use

- Environment variables
- Protected branches
- PR reviews
- Minimal permissions

---

# 20. Documentation Rules

Update docs whenever:

- Architecture changes
- API changes
- Database schema changes
- Deployment changes

---

# 21. Recommended Folder Ownership

| Folder | Owner |
|---|---|
| frontend | Atharva |
| backend/app/api | Harsh |
| backend/app/db | Yash |
| infra | Sparsh |

---

# 22. Final Development Philosophy

CustomerPulse AI must follow:

- Real data
- Real AI
- Clean architecture
- Team collaboration
- Enterprise-grade workflows
- Modular development
- Secure infrastructure

---

# 23. Things STRICTLY NOT Allowed

❌ Direct push to `main`

❌ Uploading `.env`

❌ Working on same branch together

❌ Hardcoded secrets

❌ Random API schema changes

❌ Force pushing shared branches

❌ Uploading `node_modules`

❌ Uploading `.venv`

❌ Breaking folder structure without discussion

---

# 24. Recommended GitHub Repository Settings

## Enable

- Issues
- Projects
- Discussions
- Wiki
- Actions

---

# 25. Final Branch Flow

```text
main
  ↑
develop
  ↑
feature/*
```

---

# 26. Final Goal

Build an enterprise-grade AI operational intelligence platform using:

- Real CFPB complaint data
- AWS-native infrastructure
- Claude AI
- Real-time dashboards
- Predictive intelligence
- Professional development workflows

---

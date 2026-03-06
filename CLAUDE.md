# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## What This Is

This is a **Claude Workspace Template** — a structured environment designed for working with Claude Code as a powerful agent assistant across sessions. The user will spin up fresh Claude Code sessions repeatedly, using `/prime` at the start of each to load essential context without bloat.

**This file (CLAUDE.md) is the foundation.** It is automatically loaded at the start of every session. Keep it current — it is the single source of truth for how Claude should understand and operate within this workspace.

---

## The Claude-User Relationship

Claude operates as an **agent assistant** with access to the workspace folders, context files, commands, and outputs. The relationship is:

- **User**: Defines goals, provides context about their role/function, and directs work through commands
- **Claude**: Reads context, understands the user's objectives, executes commands, produces outputs, and maintains workspace consistency

Claude should always orient itself through `/prime` at session start, then act with full awareness of who the user is, what they're trying to achieve, and how this workspace supports that.

---

## Workspace Structure

```
.
├── CLAUDE.md                          # This file — core context, always loaded
├── .claude/
│   └── commands/                      # Slash commands Claude can execute
│       ├── prime.md                   # /prime — session initialization
│       ├── create-plan.md             # /create-plan — create implementation plans
│       └── implement.md               # /implement — execute plans
├── context/                           # Background context about the user and project
│   ├── personal-info.md               # Omar — 20yo econ student, Python course
│   ├── business-info.md               # Project overview: v2 Parliament Edition
│   ├── strategy.md                    # Strategic priorities and success criteria
│   ├── current-data.md                # Project status tracker
│   └── deep-research-report.md        # Real-world news (Feb-Mar 2026) used in LLM prompts
├── plans/                             # Implementation plans
│   ├── 2026-03-03-economy-collapse-speedrun.md  # v1 plan (historical)
│   └── 2026-03-04-economy-collapse-v2-parliament.md  # v2 plan (current)
├── economy-collapse-speedrun/         # The game project
│   ├── server.py                      # FastAPI + WebSockets, phase management
│   ├── game.py                        # Game state, roles, proposals, voting, scoring
│   ├── economy.py                     # Economy model (6 indicators, 0-100)
│   ├── llm.py                         # OpenRouter: scenario gen + evaluation + narrative
│   ├── config.py                      # Settings + GameSettings dataclass
│   ├── static/host.html               # Projector display
│   ├── static/player.html             # Phone UI (role-based)
│   ├── .env                           # API key, model, ngrok URL
│   ├── requirements.txt               # Python dependencies
│   ├── README.md                      # Project readme
│   ├── how_to_start.md                # Step-by-step startup guide
│   └── ngrok                          # ngrok binary
├── outputs/                           # Work products and deliverables
├── reference/                         # Templates, examples, reusable patterns
├── scripts/                           # Automation scripts (if applicable)
└── shell-aliases.md                   # Claude Code shell alias setup (cs/cr)
```

**Key directories:**

| Directory    | Purpose                                                                             |
| ------------ | ----------------------------------------------------------------------------------- |
| `context/`   | Who the user is, their role, current priorities, strategies. Read by `/prime`.      |
| `plans/`     | Detailed implementation plans. Created by `/create-plan`, executed by `/implement`. |
| `outputs/`   | Deliverables, analyses, reports, and work products.                                 |
| `reference/` | Helpful docs, templates and patterns to assist in various workflows.                |
| `scripts/`   | Any automation or tooling scripts.                                                  |

---

## Commands

### /prime

**Purpose:** Initialize a new session with full context awareness.

Run this at the start of every session. Claude will:

1. Read CLAUDE.md and context files
2. Summarize understanding of the user, workspace, and goals
3. Confirm readiness to assist

### /create-plan [request]

**Purpose:** Create a detailed implementation plan before making changes.

Use when adding new functionality, commands, scripts, or making structural changes. Produces a thorough plan document in `plans/` that captures context, rationale, and step-by-step tasks.

Example: `/create-plan add a competitor analysis command`

### /implement [plan-path]

**Purpose:** Execute a plan created by /create-plan.

Reads the plan, executes each step in order, validates the work, and updates the plan status.

Example: `/implement plans/2026-01-28-competitor-analysis-command.md`

---

## Critical Instruction: Maintain This File

**Whenever Claude makes changes to the workspace, Claude MUST consider whether CLAUDE.md needs updating.**

After any change — adding commands, scripts, workflows, or modifying structure — ask:

1. Does this change add new functionality users need to know about?
2. Does it modify the workspace structure documented above?
3. Should a new command be listed?
4. Does context/ need new files to capture this?

If yes to any, update the relevant sections. This file must always reflect the current state of the workspace so future sessions have accurate context.

---

## Session Workflow

1. **Start**: Run `/prime` to load context
2. **Work**: Use commands or direct Claude with tasks
3. **Plan changes**: Use `/create-plan` before significant additions
4. **Execute**: Use `/implement` to execute plans
5. **Maintain**: Claude updates CLAUDE.md and context/ as the workspace evolves

---

## Active Projects

### Econoland — Parliament Edition (`economy-collapse-speedrun/`)

Live multiplayer political simulation for a Python class presentation. A randomly elected parliament writes policy proposals on their phones (visible live on the projector, character by character), the rest of the class votes, and an AI secretly grades every proposal — revealed at game over with witty commentary. Two modes: Constructive (build economy, names revealed) and Destructive (collapse it, anonymous). Round-based system (3/5/7 rounds) with host End Game button.

**Tech:** FastAPI + WebSockets + OpenRouter (Grok) + vanilla HTML/JS + ngrok

**To run:** Start ngrok (`cd economy-collapse-speedrun && ./ngrok http 8000`), update `.env` with the ngrok URL, then `python3 server.py`. See `economy-collapse-speedrun/how_to_start.md` for full instructions.

**v2 Plan:** `plans/2026-03-04-economy-collapse-v2-parliament.md`
**v1 Plan (historical):** `plans/2026-03-03-economy-collapse-speedrun.md`

---

## Notes

- Keep context minimal but sufficient — avoid bloat
- Plans live in `plans/` with dated filenames for history
- Outputs are organized by type/purpose in `outputs/`
- Reference materials go in `reference/` for reuse
- `__pycache__/` and `.DS_Store` can be safely deleted (build artifacts)

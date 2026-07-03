# AI Sync Agent

An autonomous local AI agent that watches your project folders and keeps
them automatically synchronized with GitHub — commit messages, staging,
committing and pushing all handled in the background while you just work
in your editor (VS Code or otherwise).

---

## Features

- Watches one or more local folders for file/folder creation, modification,
  deletion, and renames (via `watchdog`).
- Debounces rapid successive saves into a single commit (no commit spam).
- Auto-detects project type: Python, Java, JavaScript, React, Node.js, HTML/CSS.
- Auto-detects existing Git repos, or initializes one (`git init`,
  `.gitignore`, branch setup) if missing.
- Asks for the GitHub remote URL **once** per folder, then remembers it
  permanently in a config file.
- Generates **intelligent, conventional-commit-style messages** from the
  actual diff (e.g. `feat: add 3 file(s) (Python)`).
- Automatically stages, commits, and pushes (`git add .`, `git commit`,
  `git push origin main`).
- Retries pushes with exponential backoff on transient network failures.
- Supports multiple folder → repository mappings simultaneously.
- Structured logs for changes, commits, pushes, and failures.
- Configurable via `.env` and a YAML/JSON config file.
- Recovers automatically after a restart (syncs anything that changed
  while the agent was offline).
- Cross-platform: Windows, Linux, macOS.

---

## Project Structure

```
ai-sync-agent/
├── agent.py               # Main entry point / orchestrator
├── watcher.py              # Filesystem monitoring + debounce + project detection
├── git_manager.py           # Git operations (init, add, commit, push, retries)
├── commit_generator.py       # Intelligent commit message generation
├── config_manager.py          # Config schema (pydantic) + JSON/YAML persistence
├── logger_manager.py           # Centralized loguru logging setup
├── repository_mapper.py         # Folder <-> GitHub repo mapping + one-time prompt
├── settings.py                   # Environment-driven global settings
├── requirements.txt
├── README.md
├── .env.example
├── .gitignore
├── config/
│   └── config.example.yaml         # Sample configuration reference
├── logs/                             # Runtime logs (auto-created)
├── cache/                             # Runtime state cache (auto-created)
└── tests/                              # Pytest test suite
```

---

## Installation

### 1. Prerequisites
- Python 3.9+
- Git installed and available on your `PATH`
- A GitHub account and (for HTTPS) a personal access token, or SSH keys
  configured for `git@github.com`

### 2. Clone / copy this project, then install dependencies

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:
```
GIT_USER_NAME=Your Name
GIT_USER_EMAIL=you@example.com
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx   # if using HTTPS remotes
```

---

## Usage

### Watch the current/default configured folders
```bash
python agent.py
```

### Watch a specific folder
```bash
python agent.py "D:/Projects/RealEstateProject"
```

### Watch multiple folders at once
```bash
python agent.py "/home/user/projects/api" "/home/user/projects/frontend"
```

On first run for a new folder, the agent will:
1. Detect the project type.
2. Initialize Git if needed (`git init`, `.gitignore`, branch `main`).
3. Prompt **once** for the GitHub repository URL if no remote is mapped:
   ```
   [SETUP] No GitHub remote configured for:
     /home/user/projects/api
   Enter the GitHub repository URL (e.g. https://github.com/user/repo.git):
   ```
4. Save that mapping permanently to `config/config.yaml`.
5. Start watching — from then on, saves in your editor are automatically
   committed and pushed within a few seconds (debounce window).

Stop the agent any time with `Ctrl+C` — it shuts down cleanly.

---

## Example Workflow

1. You edit a file in VS Code and save.
2. The agent detects the change instantly.
3. It waits `AGENT_DEBOUNCE_SECONDS` (default 5s) for additional saves to
   settle, so a burst of edits becomes one commit, not ten.
4. Files are staged (`git add .`).
5. A commit message is generated from the actual diff, e.g.:
   ```
   feat: add 2 file(s), update 1 file(s) (React)

   Added: components/Card.jsx, components/Card.css
   Modified: App.jsx
   ```
6. The commit is created and pushed to `origin/main`.
7. The operation is logged to `logs/commits.log` and `logs/pushes.log`.

---

## Configuration Reference

Configuration is auto-generated at `config/config.yaml` (or `.json` if
`AGENT_CONFIG_FORMAT=json`). See `config/config.example.yaml` for the
expected shape. Key fields per folder mapping:

| Field | Description |
|---|---|
| `folder_path` | Absolute path to the watched folder |
| `remote_url` | GitHub repository URL |
| `branch` | Target branch (default `main`) |
| `project_type` | Auto-detected project type |
| `auto_push` | Whether to push automatically after each commit |
| `debounce_seconds` | Per-folder debounce override |
| `last_synced_commit` | SHA of the last commit successfully synced |

### Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GIT_USER_NAME` | — | Git commit author name |
| `GIT_USER_EMAIL` | — | Git commit author email |
| `GITHUB_TOKEN` | — | GitHub PAT for HTTPS auth |
| `AGENT_CONFIG_DIR` | `./config` | Where config files are stored |
| `AGENT_LOG_DIR` | `./logs` | Where log files are stored |
| `AGENT_CACHE_DIR` | `./cache` | Where recovery state is stored |
| `AGENT_CONFIG_FORMAT` | `yaml` | `yaml` or `json` |
| `AGENT_DEBOUNCE_SECONDS` | `5` | Seconds to wait before committing |
| `AGENT_DEFAULT_BRANCH` | `main` | Default branch name |
| `AGENT_GIT_REMOTE_NAME` | `origin` | Remote name |
| `AGENT_AUTO_PUSH` | `true` | Auto push after commit |
| `AGENT_MAX_GIT_RETRIES` | `3` | Retry attempts for push |
| `AGENT_GIT_RETRY_BACKOFF` | `2` | Seconds, multiplied by attempt number |
| `AGENT_LOG_LEVEL` | `INFO` | Log verbosity |

---

## Logs

All logs are written under `logs/`:
- `agent.log` — general activity
- `changes.log` — detected file/folder changes
- `commits.log` — every commit made
- `pushes.log` — every push attempt/result
- `failures.log` — warnings and errors across all components

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

The test suite covers config persistence, commit message generation,
project-type detection, debounce behavior, Git operations (init/commit),
and the one-time repository-mapping prompt flow.

---

## Troubleshooting

**"Invalid GitHub URL" when entering the repo URL**
Use the full HTTPS or SSH form:
`https://github.com/user/repo.git` or `git@github.com:user/repo.git`.

**Push fails with authentication errors**
- For HTTPS: ensure `GITHUB_TOKEN` is set in `.env`, or configure a Git
  credential helper (`git config --global credential.helper store`/`manager`).
- For SSH: ensure your SSH key is added to your GitHub account and
  `ssh -T git@github.com` succeeds.

**Nothing gets committed**
- Check `logs/failures.log` for errors.
- Confirm the folder isn't entirely covered by `.gitignore`.
- Confirm `AGENT_AUTO_PUSH` / the folder mapping's `auto_push` is `true`
  if you expect pushes, not just commits.

**Too many commits for one edit**
Increase `AGENT_DEBOUNCE_SECONDS` (or the folder's `debounce_seconds` in
`config/config.yaml`).

**Agent doesn't pick up changes**
- Some network filesystems / Docker volume mounts don't emit proper
  inotify events. Try running the watched folder on a native filesystem.
- On Linux, if you hit `inotify watch limit reached`, increase it:
  `sudo sysctl fs.inotify.max_user_watches=524288`.

**Re-mapping a folder to a different repository**
Edit `config/config.yaml` directly and change the `remote_url` for that
folder's mapping, or delete the mapping entry and restart the agent to
be prompted again.

**I want to stop auto-pushing but keep auto-committing**
Set `auto_push: false` for that folder in `config/config.yaml`.

---

## Design Notes

- **Debounce**: each folder has its own `threading.Timer` that resets on
  every filesystem event; the timer only fires (triggering a sync) once
  events stop arriving for `debounce_seconds`.
- **Commit intelligence**: `commit_generator.py` inspects the actual
  added/modified/deleted file sets (not just "files changed") and picks
  a conventional-commit prefix (`feat`, `fix`, `chore`) plus a summary
  line and a detail block listing affected files (truncated for large
  changesets).
- **Retry/backoff**: `git_manager.retry()` wraps push operations with a
  configurable number of attempts and linear backoff to ride out
  transient network issues.
- **Recovery**: on startup, the agent checks every configured folder for
  uncommitted changes (e.g. made while the agent wasn't running) and
  syncs them immediately before starting to watch live.

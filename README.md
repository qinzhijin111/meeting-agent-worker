# AgentMeet Agent Worker

Python agent worker for the AgentMeet realtime meeting platform.

The worker connects to the same LiveKit project used by the Next.js web application and runs AI participants inside meeting rooms.

## Current Status

Week 5 initial implementation:

- Agent repository structure
- Local Python environment
- Minimal LiveKit agent participant
- Agent identity and metadata

AI behaviors such as note taking, assistance, and translation will be added in later stages.

## Project Structure

```text
meeting-agent-worker/
├── agent.py
├── modal_app.py
├── agents/
├── tools/
├── models/
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Local Development

### Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Environment Variables

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configure:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=replace_me
LIVEKIT_API_SECRET=replace_me
```

Never commit the real `.env` file.

## Run the Worker

Start the worker in development mode:

```powershell
python agent.py dev
```

For direct local testing against a specific LiveKit room:

```powershell
python agent.py connect --room <livekit-room-name> --participant-identity agent:minimal:local
```

## Architecture

The web application owns:

- authentication
- room creation and passwords
- human LiveKit tokens
- agent dispatch
- meeting UI

The agent worker owns:

- agent runtime behavior
- agent room participation
- AI processing
- agent output generation

The worker never receives the room password.

## Week 5: Agent Worker and Modal Deployment

This repository contains the Python LiveKit Agent worker for AgentMeet.

### Implemented

- LiveKit Agent worker
- Agent Registry and metadata validation
- Note Taker, Assistant, and Translator agent types
- Explicit dispatch support
- Modal deployment
- Health endpoint on port `8081`
- Modal Secret injection

### Local development

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Run the worker locally:

```powershell
python agent.py dev
```

### Modal deployment

Deploy the worker:

```powershell
modal deploy modal_app.py
```

View logs:

```powershell
modal app logs agentmeet-agent-worker -f
```

The Modal Secret is named:

```text
agentmeet-livekit
```

Required environment variables:

```text
LIVEKIT_URL
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
```

Real secret values must not be committed to Git.

### Agent flow

```text
Web App
→ LiveKit explicit dispatch
→ Modal-hosted worker
→ Agent joins the meeting room
```

The host can also stop an active agent, which removes the LiveKit dispatch and updates the agent state in `room_agents`.

### Week 5 verification

- Agent can join an active room
- Duplicate starts are prevented
- Invalid agent types fail safely
- Worker can run on Modal
- Human calls continue if the agent fails
- Host can start and stop an agent

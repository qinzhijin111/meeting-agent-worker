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

## Week 6 - Note Taker and Meeting Output

Week 6 extends the basic LiveKit worker with a passive Note Taker that listens to human participants, collects finalized transcript segments, generates structured meeting notes, and persists meeting output through the web application.

### Note Taker Behavior

The Note Taker:

- joins the LiveKit room as an AI participant
- subscribes to human microphone tracks
- ignores other AI agents
- processes finalized speech-to-text segments only
- associates transcript segments with LiveKit participant identity
- uses the participant display name when available
- does not publish speech back into the meeting

Development logs may contain finalized transcript segments, so synthetic or demo meeting content should be used during testing.

### Structured Meeting Output

At the end of a Note Taker session, the worker generates a validated structured result containing:

- meeting summary
- decisions
- action items
- open questions

The output is validated with Pydantic before persistence.

Example structure:

```json
{
  "summary": "The team discussed the upcoming dashboard release.",
  "decisions": [
    "Release the dashboard on Friday."
  ],
  "action_items": [
    {
      "description": "Prepare the release checklist.",
      "owner": "Alice",
      "due_date": "Thursday"
    }
  ],
  "open_questions": [
    "Who will monitor the deployment?"
  ]
}
```

### Transcript Handling

Only finalized speech-to-text events are stored as transcript segments.

Each finalized transcript segment can contain:

- speaker identity
- speaker display name when available
- LiveKit audio track ID
- transcript text
- detected language
- confidence
- speech start and end timing

Interim transcripts are intentionally ignored because their text may still change.

### Meeting Output Persistence

The worker does not use its local filesystem as the permanent copy of meeting output.

Structured meeting notes are sent to the protected Next.js endpoint:

```text
POST /api/internal/agent-output
```

The request includes:

- room ID
- agent session ID
- notes generation status
- structured meeting notes when available
- a safe error message when generation fails

The worker authenticates to the internal endpoint with a shared server secret.

### Required Environment Variables

Add the following variables to the local `.env` file:

```env
AGENT_OUTPUT_URL=http://localhost:3000/api/internal/agent-output
AGENT_WORKER_SHARED_SECRET=
```

`AGENT_WORKER_SHARED_SECRET` must match the value configured in the `meeting-web` application.

Do not commit the real secret.

The existing LiveKit variables are also required:

```env
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

### Notes Generation States

The meeting-output workflow supports these states:

- `waiting` - no output has been generated yet
- `processing` - final notes are currently being generated
- `ready` - complete structured notes were generated successfully
- `partial` - useful meeting data exists, but final generation did not complete successfully
- `error` - meeting-note generation failed without usable final output

Persistence failures are handled separately from structured note generation so that successfully generated notes are not discarded simply because the persistence request fails.

### Local Development

Activate the Python virtual environment:

```powershell
cd D:\LIVEQ\meeting-agent-worker
.\.venv\Scripts\Activate.ps1
```

Run the test suite:

```powershell
python -m pytest
```

Run syntax checks:

```powershell
python -m py_compile agent.py
python -m py_compile agents\notes_agent.py
python -m py_compile models\metadata.py
python -m py_compile models\outputs.py
python -m py_compile models\transcript.py
python -m py_compile tools\persistence.py
```

Start the local worker:

```powershell
python agent.py dev
```

When testing the local worker, do not simultaneously run another worker that could receive the same LiveKit dispatch.

### Week 6 Testing

Week 6 testing includes:

- short meeting with one speaker
- three-speaker meeting with speaker attribution
- no speech or very short speech
- controlled failure after transcript collection
- refreshing the summary page while notes are processing
- validating action-item JSON against the expected schema

Detailed expected and actual results are documented in:

```text
docs/week-6-test-cases.md
```

### Privacy and Data Handling

The Note Taker processes meeting audio for speech-to-text only after the host explicitly starts the agent.

The MVP does not intentionally store raw meeting audio.

Structured notes may contain:

- summaries
- decisions
- action items
- open questions

AI-generated notes may be incomplete or inaccurate and should be reviewed before relying on important decisions, owners, or deadlines.

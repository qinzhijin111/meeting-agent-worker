
import subprocess
import time

import modal


APP_NAME = "agentmeet-agent-worker"
SECRET_NAME = "agentmeet-livekit"

REMOTE_DIR = "/opt/agent"


image = (
    modal.Image.debian_slim(
        python_version="3.12"
    )
    .pip_install_from_requirements(
        "requirements.txt"
    )
    .add_local_dir(
        ".",
        REMOTE_DIR,
        copy=True,
        ignore=[
            ".venv/**",
            ".git/**",
            ".env",
            "**/__pycache__/**",
            "**/*.pyc",
        ],
    )
    .workdir(REMOTE_DIR)
)


app = modal.App(
    APP_NAME
)


livekit_secret = (
    modal.Secret.from_name(
        SECRET_NAME,
        required_keys=[
            "LIVEKIT_URL",
            "LIVEKIT_API_KEY",
            "LIVEKIT_API_SECRET",
        ],
    )
)


@app.server(
    port=8081,
    image=image,
    secrets=[
        livekit_secret
    ],

    # Keep one worker warm for
    # reliable demo dispatch.
    min_containers=1,

    # One AgentServer process can
    # handle multiple agent jobs
    # for this internship demo.
    max_containers=1,

    startup_timeout=60,
    exit_grace_period=30,
)
class AgentWorker:
    @modal.enter()
    def start_worker(
        self,
    ) -> None:
        print(
            "Starting AgentMeet "
            "LiveKit worker..."
        )

        self.process = (
            subprocess.Popen(
                [
                    "python",
                    "agent.py",
                    "start",
                ]
            )
        )

        time.sleep(2)

        if (
            self.process.poll()
            is not None
        ):
            raise RuntimeError(
                "LiveKit worker exited "
                "during startup."
            )

    @modal.exit()
    def stop_worker(
        self,
    ) -> None:
        process = getattr(
            self,
            "process",
            None,
        )

        if (
            process is None
            or process.poll()
            is not None
        ):
            return

        print(
            "Stopping AgentMeet "
            "LiveKit worker..."
        )

        process.terminate()

        try:
            process.wait(
                timeout=20
            )
        except (
            subprocess.TimeoutExpired
        ):
            process.kill()

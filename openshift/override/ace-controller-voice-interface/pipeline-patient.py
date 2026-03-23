# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Voice Agent WebRTC Pipeline.

This module implements a voice agent pipeline using WebRTC for real-time
speech-to-speech communication with dynamic prompt support.
"""

import argparse
import asyncio
import json
import os

import sys
import uuid
from pathlib import Path
import httpx
import uvicorn
import yaml
from config import Config
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import InputAudioRawFrame, LLMMessagesFrame, TTSAudioRawFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.transports.base_transport import TransportParams
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import (
    IceServer,
    SmallWebRTCConnection,
)
from websocket_transcript_output import WebsocketTranscriptOutput

from nvidia_pipecat.processors.audio_util import AudioRecorder
from nvidia_pipecat.processors.nvidia_context_aggregator import (
    NvidiaTTSResponseCacher,
    create_nvidia_context_aggregator,
)
from nvidia_pipecat.processors.transcript_synchronization import (
    BotTranscriptSynchronization,
    UserTranscriptSynchronization,
)
from nvidia_pipecat.services.nvidia_rag import NvidiaRAGService
from nvidia_pipecat.services.riva_speech import RivaASRService, RivaTTSService

load_dotenv(override=True)

config_path = os.getenv("CONFIG_PATH")
if not config_path:
    raise ValueError("CONFIG_PATH environment variable is not set")
try:
    config = Config(**yaml.safe_load(Path(config_path).read_text()))
except FileNotFoundError as e:
    raise FileNotFoundError(f"Config file not found at: {config_path}") from e
except yaml.YAMLError as e:
    raise ValueError(f"Invalid YAML in config file: {e}") from e

# Kubernetes/OpenShift: CONFIG often still points at docker-compose hostnames (e.g.
# app-server-healthcare-assistant). Override when the pipeline receives RAG_SERVER_URL.
_rag_url = os.getenv("RAG_SERVER_URL", "").strip()
if _rag_url:
    config = config.model_copy(
        update={
            "NvidiaRAGService": config.NvidiaRAGService.model_copy(
                update={"rag_server_url": _rag_url}
            )
        }
    )

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store connections by pc_id
pcs_map: dict[str, SmallWebRTCConnection] = {}
contexts_map: dict[str, OpenAILLMContext] = {}
tasks_map: dict[str, PipelineTask] = {}
# run_bot does heavy work before tasks_map is set; cancel this task if WebRTC closes first
run_bot_async_tasks: dict[str, asyncio.Task] = {}

DEFAULT_METERED_CREDENTIALS_URL = "https://fax.metered.live/api/v1/turn/credentials"


def _is_turn_url(u: str) -> bool:
    ul = u.strip().lower()
    return ul.startswith("turn:") or ul.startswith("turns:")


def _pick_aioice_turn_url(urls: list[str]) -> str | None:
    """Pick a single TURN URL for aioice/aiortc.

    Metered returns several endpoints (UDP ``turn:``, TCP ``turns:``, etc.). aioice often hits
    STUN **401** on ``CHANNEL_BIND`` when it multiplexes multiple relays or mixed TLS/UDP.

    Default: prefer UDP ``turn:``. Set ``PIPELINE_AIOICE_PREFER=tls`` (or ``tcp`` / ``turns``) if
    UDP to the relay is blocked.
    """
    cleaned = [u.strip() for u in urls if u.strip()]
    if not cleaned:
        return None

    prefer = os.getenv("PIPELINE_AIOICE_PREFER", "udp").strip().lower()
    prefer_tls = prefer in ("tls", "tcp", "turns", "turns:")

    if prefer_tls:
        for u in cleaned:
            if u.lower().startswith("turns:"):
                return u
        for u in cleaned:
            ul = u.lower()
            if "transport=tcp" in ul and ul.startswith("turn:"):
                return u

    def is_plain_turn_udp(u: str) -> bool:
        ul = u.lower()
        return ul.startswith("turn:") and not ul.startswith("turns:") and "transport=tcp" not in ul

    for u in cleaned:
        if is_plain_turn_udp(u):
            return u
    for u in cleaned:
        ul = u.lower()
        if ul.startswith("turn:") and not ul.startswith("turns:"):
            return u
    return cleaned[0]


def _limit_aioice_turn_groups(servers: list[IceServer]) -> list[IceServer]:
    """Metered can return multiple distinct (username, credential) groups; aioice may 401 on extras."""
    try:
        n = int(os.getenv("PIPELINE_AIOICE_MAX_TURN_GROUPS", "1"))
    except ValueError:
        n = 1
    n = max(1, n)
    if len(servers) > n:
        logger.info(
            "aioice: {} TURN credential group(s) in ICE config; using first {} only (PIPELINE_AIOICE_MAX_TURN_GROUPS)",
            len(servers),
            n,
        )
        return servers[:n]
    return servers


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def static_turn_ice_servers_from_env() -> list[IceServer]:
    """Static ``TURN_*`` from Helm/env — Metered dashboard long-lived credentials sometimes work better with aioice."""
    if not os.getenv("TURN_SERVER_URL"):
        return []
    return _limit_aioice_turn_groups(
        [
            IceServer(
                urls=os.getenv("TURN_SERVER_URL", ""),
                username=os.getenv("TURN_USERNAME", ""),
                credential=os.getenv("TURN_PASSWORD", ""),
            )
        ]
    )


def static_turn_ice_servers_for_browser() -> dict | None:
    """Same ICE as :func:`static_turn_ice_servers_from_env` in ``RTCPeerConnection`` JSON shape."""
    servers = static_turn_ice_servers_from_env()
    if not servers:
        return None
    ice_servers: list[dict] = []
    for s in servers:
        ice_servers.append(
            {
                "urls": s.urls,
                "username": getattr(s, "username", "") or "",
                "credential": getattr(s, "credential", "") or "",
            }
        )
    return {"iceServers": ice_servers}


def ice_servers_from_metered_body(data: dict | list) -> list[IceServer]:
    """Convert Metered REST JSON (or browser RTCIceServer[]) to pipecat IceServer entries.

    Keeps only ``turn:`` / ``turns:`` URLs (drops pure STUN), merges URLs per
    username/credential, then **selects one** URL per group for aioice stability.
    """
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and "iceServers" in data:
        entries = data["iceServers"]
    else:
        return []
    merged: dict[tuple[str, str], list[str]] = {}
    for item in entries:
        if not isinstance(item, dict):
            continue
        urls = item.get("urls")
        if urls is None:
            continue
        if isinstance(urls, str):
            url_parts = [urls]
        elif isinstance(urls, list):
            url_parts = [u for u in urls if isinstance(u, str)]
        else:
            continue
        turn_parts = [u for u in url_parts if _is_turn_url(u)]
        if not turn_parts:
            continue
        username = str(item.get("username", "") or "")
        credential = str(item.get("credential", "") or "")
        key = (username, credential)
        merged.setdefault(key, []).extend(turn_parts)
    out: list[IceServer] = []
    for (username, credential), url_list in merged.items():
        only = _pick_aioice_turn_url(url_list)
        if only:
            logger.debug("aioice using single TURN URL: {}", only)
            out.append(IceServer(urls=only, username=username, credential=credential))
    return _limit_aioice_turn_groups(out)


async def resolve_pipecat_ice_servers(request: dict) -> list[IceServer]:
    """Prefer ICE from the browser WebSocket payload (same creds as RTCPeerConnection); else Metered REST / static TURN."""
    if _env_truthy("PIPELINE_ICE_USE_STATIC_ONLY"):
        s = static_turn_ice_servers_from_env()
        if s:
            logger.info("Python peer ICE: PIPELINE_ICE_USE_STATIC_ONLY — using TURN_* env only")
            return s
    raw = request.get("iceServers")
    if isinstance(raw, list) and raw:
        servers = ice_servers_from_metered_body({"iceServers": raw})
        if servers:
            logger.info(
                "Python peer using {} ICE server group(s) from browser (same credentials as RTCPeerConnection)",
                len(servers),
            )
            return servers
        logger.warning("Browser sent iceServers but none were usable TURN entries; falling back to server-side ICE")
    return await build_pipecat_ice_servers()


async def fetch_metered_turn_body() -> dict | list:
    """Fetch Metered TURN credentials JSON. Raises HTTPException on failure."""
    api_key = os.getenv("METERED_TURN_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="METERED_TURN_API_KEY not configured")
    base = os.getenv("METERED_CREDENTIALS_URL", DEFAULT_METERED_CREDENTIALS_URL).strip()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(base, params={"apiKey": api_key})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        logger.error("TURN credentials request failed: {}", e)
        raise HTTPException(status_code=502, detail="Failed to fetch TURN credentials") from e


async def build_pipecat_ice_servers() -> list[IceServer]:
    """ICE servers for the Python peer (aioice). Prefer Metered REST so creds match the browser; else static TURN_*."""
    if _env_truthy("PIPELINE_ICE_USE_STATIC_ONLY"):
        s = static_turn_ice_servers_from_env()
        if s:
            return s
    if os.getenv("METERED_TURN_API_KEY", "").strip():
        try:
            data = await fetch_metered_turn_body()
        except HTTPException as e:
            logger.warning(
                "Python peer ICE: Metered fetch failed ({}), falling back to TURN_* env if set",
                e.detail,
            )
            data = None
        if data is not None:
            servers = ice_servers_from_metered_body(data)
            if servers:
                logger.info(
                    "Python peer using {} ICE server(s) from Metered REST (same as /api/ice_config)",
                    len(servers),
                )
                return servers
    s = static_turn_ice_servers_from_env()
    if s:
        return s
    return []


async def run_bot(webrtc_connection, ws: WebSocket):
    """Run the voice agent bot with WebRTC connection and WebSocket.

    Args:
        webrtc_connection: The WebRTC connection for audio streaming
        ws: WebSocket connection for communication
    """
    stream_id = uuid.uuid4()
    transport_params = TransportParams(
        audio_in_enabled=True,
        audio_in_sample_rate=16000,
        audio_out_sample_rate=16000,
        audio_out_enabled=True,
        vad_analyzer=SileroVADAnalyzer(),
        audio_out_10ms_chunks=5,
    )

    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=transport_params,
    )

    agent = NvidiaRAGService(
        collection_name=config.NvidiaRAGService.collection_name,
        enable_citations=config.NvidiaRAGService.enable_citations,
        rag_server_url=config.NvidiaRAGService.rag_server_url,
        use_knowledge_base=config.NvidiaRAGService.use_knowledge_base,
        max_tokens=config.NvidiaRAGService.max_tokens,
        filler=config.Pipeline.filler,
        session = httpx.AsyncClient(timeout=float(os.getenv("REQUEST_TIMEOUT", 15.0)))
    )

    stt = RivaASRService(
        server=config.RivaASRService.server,
        api_key=os.getenv("NVIDIA_API_KEY"),
        language=config.RivaASRService.language,
        sample_rate=config.RivaASRService.sample_rate,
        automatic_punctuation=True,
        model=config.RivaASRService.model,
        function_id=config.RivaASRService.function_id,
    )

    # Load IPA dictionary with error handling
    ipa_file = Path(__file__).parent / "ipa.json"
    try:
        with open(ipa_file, encoding="utf-8") as f:
            ipa_dict = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"IPA dictionary file not found at {ipa_file}")
        raise FileNotFoundError(f"IPA dictionary file not found at {ipa_file}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in IPA dictionary file: {e}")
        raise ValueError(f"Invalid JSON in IPA dictionary file: {e}") from e
    except Exception as e:
        logger.error(f"Error loading IPA dictionary: {e}")
        raise

    tts = RivaTTSService(
        server=config.RivaTTSService.server,
        api_key=os.getenv("NVIDIA_API_KEY"),
        voice_id=config.RivaTTSService.voice_id,
        model=config.RivaTTSService.model,
        function_id=config.RivaTTSService.function_id,
        language=config.RivaTTSService.language,
        zero_shot_audio_prompt_file=(
            Path(os.getenv("ZERO_SHOT_AUDIO_PROMPT")) if os.getenv("ZERO_SHOT_AUDIO_PROMPT") else None
        ),
        ipa_dict=ipa_dict,
    )
    # by default, audio recording is disabled, 
    # if you want to record audio, set the environment variable DUMP_AUDIO_FILES to true in ace_controller.env file
    enable_audio_recording = os.getenv("DUMP_AUDIO_FILES", "false").lower() == "true"
    if enable_audio_recording:
        # Create audio_dumps directory if it doesn't exist
        audio_dumps_dir = Path(__file__).parent / "audio_dumps"
        audio_dumps_dir.mkdir(exist_ok=True)

        asr_recorder = AudioRecorder(
            output_file=str(audio_dumps_dir / f"asr_recording_{stream_id}.wav"),
            params=transport_params,
            frame_type=InputAudioRawFrame,
        )

        tts_recorder = AudioRecorder(
            output_file=str(audio_dumps_dir / f"tts_recording_{stream_id}.wav"),
            params=transport_params,
            frame_type=TTSAudioRawFrame,
        )
    else:
        asr_recorder = None
        tts_recorder = None

    # Used to synchronize the user and bot transcripts in the UI
    stt_transcript_synchronization = UserTranscriptSynchronization()
    tts_transcript_synchronization = BotTranscriptSynchronization()

    messages = [
        
    ]

    context = OpenAILLMContext(messages)

    # Store context globally so WebSocket can access it
    pc_id = webrtc_connection.pc_id
    contexts_map[pc_id] = context

    # Configure speculative speech processing based on environment variable
    # set this variable to true only if your agent backend does not retain every incoming request and the agent response in memory
    # we will keep this set to false since the healthcare agent retains memory in langgraph
    enable_speculative_speech = os.getenv("ENABLE_SPECULATIVE_SPEECH", "false").lower() == "true"

    if enable_speculative_speech:
        context_aggregator = create_nvidia_context_aggregator(context, send_interims=True)
        tts_response_cacher = NvidiaTTSResponseCacher()
    else:
        context_aggregator = agent.create_context_aggregator(context)
        tts_response_cacher = None

    transcript_processor_output = WebsocketTranscriptOutput(ws)

    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            *([asr_recorder] if asr_recorder else []),  # Include asr_recorder only if enabled
            stt,  # Speech-To-Text
            stt_transcript_synchronization,
            context_aggregator.user(),
            agent,  # Agent Backend
            tts,  # Text-To-Speech
            *([tts_recorder] if tts_recorder else []),  # Include tts_recorder only if enabled
            *([tts_response_cacher] if tts_response_cacher else []),  # Include cacher only if enabled
            tts_transcript_synchronization,
            transcript_processor_output,
            transport.output(),  # Websocket output to client
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            send_initial_empty_metrics=True,
            start_metadata={"stream_id": stream_id},
        ),
    )
    tasks_map[pc_id] = task

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Wait 50ms for custom prompt from UI before starting conversation
        await asyncio.sleep(0.05)
        # Kick off the conversation.
        # messages.append({"role": "system", "content": "Please introduce yourself to the user."})
        await task.queue_frames([LLMMessagesFrame(messages)])

    runner = PipelineRunner(handle_sigint=False)

    try:
        await runner.run(task)
    finally:
        tasks_map.pop(pc_id, None)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for handling voice agent connections.

    Args:
        websocket: The WebSocket connection to handle
    """
    await websocket.accept()
    try:
        request = await websocket.receive_json()
        pc_id = request.get("pc_id")

        if pc_id and pc_id in pcs_map:
            pipecat_connection = pcs_map[pc_id]
            logger.info(f"Reusing existing connection for pc_id: {pc_id}")
            await pipecat_connection.renegotiate(sdp=request["sdp"], type=request["type"])
            answer = pipecat_connection.get_answer()
        else:
            servers = await resolve_pipecat_ice_servers(request)
            if not servers:
                logger.warning(
                    "Python peer has no TURN/STUN ICE servers — WebRTC usually fails across NAT to OpenShift. "
                    "Configure METERED_TURN_API_KEY (GET /ice_config) or TURN_SERVER_URL + TURN_USERNAME + TURN_PASSWORD; "
                    "export them when running deploy-app.sh so the Secret is populated."
                )
            pipecat_connection = SmallWebRTCConnection(servers)
            await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

            @pipecat_connection.event_handler("closed")
            async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
                cid = webrtc_connection.pc_id
                logger.info(f"Discarding peer connection for pc_id: {cid}")
                pcs_map.pop(cid, None)
                contexts_map.pop(cid, None)
                t = tasks_map.pop(cid, None)
                if t:
                    await t.cancel()
                    logger.info(f"Cancelled pipeline task for pc_id={cid}")
                bot_job = run_bot_async_tasks.pop(cid, None)
                if bot_job and not bot_job.done():
                    bot_job.cancel()
                    logger.info(f"Cancelled run_bot asyncio task for pc_id={cid}")

            answer = pipecat_connection.get_answer()
            pc_key = answer["pc_id"]

            async def run_bot_wrapper():
                try:
                    await run_bot(pipecat_connection, websocket)
                except asyncio.CancelledError:
                    logger.info("run_bot task cancelled (WebRTC closed during startup?) pc_id={}", pc_key)
                    raise
                finally:
                    run_bot_async_tasks.pop(pc_key, None)

            run_bot_async_tasks[pc_key] = asyncio.create_task(run_bot_wrapper())

        pcs_map[answer["pc_id"]] = pipecat_connection

        await websocket.send_json(answer)

        # Keep the connection open and print text messages
        while True:
            try:
                message = await websocket.receive_text()
                # Parse JSON message from UI
                try:
                    data = json.loads(message)
                    message = data.get("message", "").strip()
                    if data.get("type") == "context_reset" and message:
                        print(f"Received context reset from UI: {message}")
                        logger.info(f"Context reset from UI: {message}")

                        # Replace entire conversation context with new system prompt
                        pc_id = pipecat_connection.pc_id
                        if pc_id in contexts_map:
                            context = contexts_map[pc_id]
                            context.set_messages([{"role": "system", "content": message}])
                        else:
                            print(f"No context found for pc_id: {pc_id}")

                except json.JSONDecodeError:
                    print(f"Non-JSON message: {message}")
            except WebSocketDisconnect:
                logger.info("Signaling WebSocket closed")
                break
            except Exception as e:
                err = str(e)
                if "1005" in err or "NO_STATUS_RCVD" in err:
                    logger.info("Signaling WebSocket closed without status (tab/proxy): {}", e)
                else:
                    logger.error("Error processing message: {}", e)
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected from websocket")


@app.get("/ice_config")
async def ice_config():
    """ICE for the browser: Metered REST if ``METERED_TURN_API_KEY`` is set, else static ``TURN_*`` env (same as Python peer).

    Metered returns JSON suitable for ``RTCPeerConnection({ iceServers: ... })`` (often a bare array).
    Without Metered, configure ``TURN_SERVER_URL`` and optional ``TURN_USERNAME`` / ``TURN_PASSWORD``.
    """
    if os.getenv("METERED_TURN_API_KEY", "").strip():
        data = await fetch_metered_turn_body()
        if isinstance(data, list):
            return {"iceServers": data}
        if isinstance(data, dict) and "iceServers" in data:
            return data
        raise HTTPException(status_code=502, detail="Unexpected TURN credentials response shape")
    static = static_turn_ice_servers_for_browser()
    if static:
        return static
    raise HTTPException(
        status_code=503,
        detail="No TURN configured: set METERED_TURN_API_KEY or TURN_SERVER_URL (+ TURN_USERNAME / TURN_PASSWORD if required)",
    )


@app.get("/get_prompt")
async def get_prompt():
    """Get the default system prompt."""
    return {
        "prompt": "Not set in ace-controller, set in agent backend",
        "name": "System Prompt",
        "description": "Default system prompt for the System as set at the backend",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WebRTC demo")
    parser.add_argument("--host", default="0.0.0.0", help="Host for HTTP server (default: localhost)")
    parser.add_argument("--port", type=int, default=7860, help="Port for HTTP server (default: 7860)")
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    logger.remove(0)
    if args.verbose:
        logger.add(sys.stderr, level="TRACE")
    else:
        logger.add(sys.stderr, level="DEBUG")

    logger.info(
        "pipeline-patient starting (verbose={} → loguru {})",
        bool(args.verbose),
        "TRACE" if args.verbose else "DEBUG",
    )
    if os.getenv("TURN_SERVER_URL"):
        logger.info("TURN_SERVER_URL is set (server-side ICE uses TURN; GET /ice_config uses same static TURN if Metered unset)")
    else:
        logger.info("TURN_SERVER_URL unset — server ICE is host/STUN only; cross-NAT often needs TURN")
    if os.getenv("METERED_TURN_API_KEY"):
        logger.info(
            "METERED_TURN_API_KEY is set — browser uses GET /ice_config; Python peer uses the same Metered REST ICE"
        )

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ws_ping_interval=20.0,
        ws_ping_timeout=20.0,
    )

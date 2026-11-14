"""
Realtime STT Provider Abstraction & AssemblyAI Universal-3.6 Pro Realtime Client
tests/realtime_stt_eval/backend/app/provider.py
"""

import abc
import asyncio
import json
import time
import urllib.parse
from typing import AsyncGenerator, Dict, Any, Optional
import websockets
from websockets.client import WebSocketClientProtocol

from .config import settings

class RealtimeSTTProvider(abc.ABC):
    """Abstract interface for streaming realtime speech-to-text providers."""
    
    @abc.abstractmethod
    async def start_session(self, session_id: str) -> Dict[str, Any]:
        """Initiate streaming connection with the provider."""
        pass

    @abc.abstractmethod
    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Stream a binary audio frame (PCM16 16kHz mono)."""
        pass

    @abc.abstractmethod
    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream incoming transcription events from the provider."""
        pass

    @abc.abstractmethod
    async def stop_session(self) -> Dict[str, Any]:
        """Request graceful flush and termination from the provider."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Close connection and clean up resources."""
        pass


class AssemblyAIRealtimeProvider(RealtimeSTTProvider):
    """
    AssemblyAI Universal-3.6 Pro Realtime WebSocket Client (v3 API).
    Endpoint: wss://streaming.assemblyai.com/v3/ws
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        speech_model: str = "universal-3-6-pro",
        domain: str = "medical-v1",
        speaker_labels: bool = True,
        sample_rate: int = 16000,
        max_speakers: int = 2
    ):
        self.api_key = api_key or settings.assemblyai_api_key
        self.speech_model = speech_model
        self.domain = domain
        self.speaker_labels = speaker_labels
        self.sample_rate = sample_rate
        self.max_speakers = max_speakers
        
        self.ws: Optional[WebSocketClientProtocol] = None
        self.session_id: Optional[str] = None
        self.remote_session_id: Optional[str] = None
        self.is_connected = False
        self.is_flushing = False
        self._receive_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def start_session(self, session_id: str) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "replace_me" or self.api_key == "your_assemblyai_api_key_here":
            raise ValueError(
                "AssemblyAI API key is missing or set to placeholder. "
                "Please configure ASSEMBLYAI_API_KEY in tests/realtime_stt_eval/.env"
            )

        self.session_id = session_id
        
        # Build query parameters for AssemblyAI v3 endpoint
        params = {
            "speech_model": self.speech_model,
            "sample_rate": str(self.sample_rate),
        }
        if self.domain:
            params["domain"] = self.domain
        if self.speaker_labels:
            params["speaker_labels"] = "true"
            params["max_speakers"] = str(self.max_speakers)

        url = f"{settings.assemblyai_ws_url}?{urllib.parse.urlencode(params)}"
        headers = {
            "Authorization": self.api_key
        }

        # Connect to AssemblyAI Streaming WebSocket
        self.ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=20,
            max_size=10 * 1024 * 1024
        )
        self.is_connected = True
        self.is_flushing = False

        # Start background receive task to populate event queue
        self._receive_task = asyncio.create_task(self._read_messages_loop())

        return {
            "status": "connected",
            "provider": "assemblyai",
            "model": self.speech_model,
            "domain": self.domain,
            "speaker_labels": self.speaker_labels,
        }

    async def send_audio(self, pcm_bytes: bytes) -> None:
        """Sends binary PCM16 audio frame."""
        if not self.is_connected or not self.ws:
            return
        if self.is_flushing:
            return
        try:
            await self.ws.send(pcm_bytes)
        except Exception as e:
            await self._event_queue.put({"type": "error", "error": f"Audio send failed: {e}"})

    async def _read_messages_loop(self):
        """Internal receiver loop that reads messages from AssemblyAI."""
        try:
            async for raw_msg in self.ws:
                if isinstance(raw_msg, str):
                    try:
                        data = json.loads(raw_msg)
                        msg_type = data.get("type") or data.get("message_type")
                        
                        if msg_type == "Begin":
                            self.remote_session_id = data.get("id")
                            await self._event_queue.put({"type": "begin", "data": data})

                        elif msg_type == "Turn":
                            await self._event_queue.put({"type": "turn", "data": data})

                        elif msg_type == "SpeechStarted":
                            await self._event_queue.put({"type": "speech_started", "data": data})

                        elif msg_type == "Termination":
                            await self._event_queue.put({"type": "termination", "data": data})
                            break

                        else:
                            await self._event_queue.put({"type": "other", "data": data})
                    except Exception as err:
                        await self._event_queue.put({"type": "error", "error": f"JSON decode error: {err}"})
                elif isinstance(raw_msg, bytes):
                    # Raw binary not expected from server
                    pass
        except websockets.ConnectionClosed:
            pass
        except Exception as ex:
            await self._event_queue.put({"type": "error", "error": str(ex)})
        finally:
            self.is_connected = False
            await self._event_queue.put({"type": "connection_closed"})

    async def receive_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Yields transcription events from the provider."""
        while self.is_connected or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

    async def stop_session(self) -> Dict[str, Any]:
        """
        Sends Terminate message to flush remaining audio and wait for final response.
        """
        if not self.is_connected or not self.ws:
            return {"status": "already_stopped"}

        self.is_flushing = True
        t0 = time.time()
        try:
            # Terminate message format as required by AssemblyAI streaming v3
            await self.ws.send(json.dumps({"type": "Terminate"}))
        except Exception as e:
            return {"status": "error", "error": f"Failed to send Terminate: {e}"}

        # Wait for Termination event up to 5 seconds
        termination_received = False
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if not self.is_connected:
                termination_received = True
                break
            await asyncio.sleep(0.05)

        flush_duration_ms = (time.time() - t0) * 1000.0
        return {
            "status": "stopped",
            "flush_duration_ms": round(flush_duration_ms, 2),
            "termination_received": termination_received
        }

    async def close(self) -> None:
        self.is_connected = False
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
        self.ws = None

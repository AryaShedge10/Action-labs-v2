"""
Debug script: connects directly to NeMo-Speech.cpp WebSocket and prints
every raw event so we can see the exact protocol structure.

Run:
    .venv\Scripts\python scripts\debug_nemo_events.py

Speak for ~10 seconds, then press Ctrl+C.
"""
import asyncio
import json
import sys
import threading
import numpy as np

try:
    import websockets
    import sounddevice as sd
except ImportError:
    print("Installing sounddevice...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "sounddevice"], check=True)
    import sounddevice as sd
    import websockets

NEMO_URL = "ws://127.0.0.1:8090/v1/audio/transcriptions/realtime"
SAMPLE_RATE = 16000
CHUNK = 4096  # power of two, ~256ms

audio_queue = asyncio.Queue()
stop_event = asyncio.Event()

def mic_callback(indata, frames, time_info, status):
    pcm = (indata[:, 0] * 32767).astype(np.int16)
    try:
        audio_queue.put_nowait(pcm.tobytes())
    except Exception:
        pass

async def main():
    print(f"Connecting to {NEMO_URL} ...")
    async with websockets.connect(NEMO_URL, max_size=10*1024*1024) as ws:
        print("Connected. Waiting for session.created...")

        # Receive session.created
        raw = await ws.recv()
        data = json.loads(raw)
        print(f"\n[RECV] {json.dumps(data, indent=2)}\n")

        # Send session.update
        config = {
            "type": "session.update",
            "session": {
                "sample_rate": SAMPLE_RATE,
                "language": "en-US",
                "automatic_punctuation": True,
                "word_timestamps": True,
                "speaker_diarization": True,
            }
        }
        await ws.send(json.dumps(config))
        print(f"[SENT] session.update\n")

        # Wait for session.updated
        raw = await ws.recv()
        data = json.loads(raw)
        print(f"[RECV] {json.dumps(data, indent=2)}\n")

        print("=== Speak now (Ctrl+C to stop) ===\n")

        # Start mic
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK,
            callback=mic_callback,
        )
        stream.start()

        async def send_audio():
            while not stop_event.is_set():
                try:
                    chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.5)
                    await ws.send(chunk)
                except asyncio.TimeoutError:
                    continue

        async def recv_events():
            try:
                async for raw_msg in ws:
                    if isinstance(raw_msg, bytes):
                        continue
                    data = json.loads(raw_msg)
                    print(f"[RECV type={data.get('type')}]")
                    # Print full event for unknown types
                    t = data.get("type", "")
                    if t in ("conversation.item.input_audio_transcription.delta",
                             "conversation.item.input_audio_transcription.completed"):
                        print(json.dumps(data, indent=2))
                    else:
                        print(json.dumps(data, indent=2))
                    print()
            except Exception as e:
                print(f"recv error: {e}")

        try:
            await asyncio.gather(send_audio(), recv_events())
        except asyncio.CancelledError:
            pass
        finally:
            stream.stop()
            stop_event.set()
            await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            print("\n[SENT] commit — waiting for final events...")
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")

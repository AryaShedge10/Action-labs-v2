"""
Direct NeMo-Speech.cpp WebSocket test harness.
tests/realtime_nvidia/scripts/test_realtime_events.py

Purpose: Establish the raw NVIDIA event contract BEFORE modifying the frontend.
         Bypasses FastAPI backend and UI entirely.

Usage:
  Mic (natural speech — no forced pauses):
    .venv\Scripts\python scripts\test_realtime_events.py --no-diarization --endpointing 800

  WAV file:
    .venv\Scripts\python scripts\test_realtime_events.py --wav recordings/clinical_test_dialogue.wav

  With diarization:
    .venv\Scripts\python scripts\test_realtime_events.py --endpointing 800

Protocol (NeMo-Speech.cpp v0.2.0):
  CLIENT -> session.update  (before audio)
  CLIENT -> binary PCM16 frames (continuous)
  CLIENT -> input_audio_buffer.commit  (graceful stop)
  SERVER -> delta events  (sub-word, live hypothesis)
  SERVER -> completed events  (final utterance, after endpointing silence)
  SERVER -> input_audio_buffer.committed  (all done)
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    import numpy as np
    import websockets
except ImportError:
    print("Run: .venv\\Scripts\\pip install websockets numpy")
    sys.exit(1)

NEMO_URL = "ws://127.0.0.1:8090/v1/audio/transcriptions/realtime"
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── State ──────────────────────────────────────────────────────────────────
t_connect: float = 0.0
delta_count: int = 0
completed_count: int = 0
all_events: list = []
running_partial: str = ""
stop_sending = asyncio.Event()


def elapsed() -> float:
    return round(time.time() - t_connect, 3)


def record(data: dict):
    all_events.append({"elapsed_s": elapsed(), **data})


# ── Main ────────────────────────────────────────────────────────────────────

async def run(diarization: bool, wav_path: str | None, endpointing_ms: int):
    global t_connect, delta_count, completed_count, running_partial

    print(f"\n{'='*60}")
    print(f"NeMo-Speech.cpp Direct Test")
    print(f"  URL:          {NEMO_URL}")
    print(f"  Diarization:  {diarization}")
    print(f"  Endpointing:  {endpointing_ms}ms")
    print(f"  Source:       {'mic' if not wav_path else wav_path}")
    print(f"{'='*60}\n")

    try:
        ws_conn = websockets.connect(
            NEMO_URL,
            max_size=10 * 1024 * 1024,
            open_timeout=10,
        )
        async with ws_conn as ws:
            t_connect = time.time()

            # ── session.created ───────────────────────────────────────────
            raw = await ws.recv()
            data = json.loads(raw)
            record(data)
            print(f"[{elapsed():7.3f}s] session.created  model={data.get('session',{}).get('model','?')}")

            # ── session.update ────────────────────────────────────────────
            cfg = {
                "type": "session.update",
                "session": {
                    "sample_rate": 16000,
                    "language": "en-US",
                    "automatic_punctuation": True,
                    "word_timestamps": True,
                    "speaker_diarization": diarization,
                    "endpointing_ms": endpointing_ms,
                }
            }
            await ws.send(json.dumps(cfg))
            print(f"[{elapsed():7.3f}s] session.update   diarization={diarization}  endpointing_ms={endpointing_ms}")

            # ── session.updated ───────────────────────────────────────────
            raw = await ws.recv()
            data = json.loads(raw)
            record(data)
            confirmed = data.get("session", {})
            print(f"[{elapsed():7.3f}s] session.updated  {confirmed}\n")

            # ── Load audio ────────────────────────────────────────────────
            if wav_path:
                try:
                    import soundfile as sf
                    audio, sr = sf.read(wav_path, dtype="int16")
                    if audio.ndim > 1:
                        audio = audio.mean(axis=1).astype(np.int16)
                    if sr != 16000:
                        print(f"[WARN] WAV is {sr}Hz — NeMo expects 16kHz")
                    raw_bytes = audio.tobytes()
                    duration = len(audio) / 16000
                    print(f"[{elapsed():7.3f}s] WAV loaded  {duration:.1f}s  {len(raw_bytes)} bytes")
                except ImportError:
                    print("[ERROR] soundfile not installed: .venv\\Scripts\\pip install soundfile")
                    return
                except FileNotFoundError:
                    print(f"[ERROR] WAV not found: {wav_path}")
                    return
            else:
                raw_bytes = None
                print(f"[{elapsed():7.3f}s] Mic mode — speak naturally, then wait ~2s, then Ctrl+C")
                print(f"           The test will gracefully commit before closing.\n")

            print(f"{'='*60}")
            print(f"Streaming audio...")
            print(f"{'='*60}\n")

            # ── Audio sender ──────────────────────────────────────────────
            async def send_audio():
                # Match NeMo's 160ms encoder step exactly
                FRAME_SAMPLES = 2560   # 160ms × 16000
                FRAME_BYTES = FRAME_SAMPLES * 2
                FRAME_SLEEP = 0.160

                frames_sent = 0
                t_audio_start = time.time()

                if raw_bytes:
                    for i in range(0, len(raw_bytes), FRAME_BYTES):
                        chunk = raw_bytes[i:i + FRAME_BYTES]
                        if not chunk:
                            break
                        await ws.send(chunk)
                        frames_sent += 1
                        # Real-time pacing
                        elapsed_real = time.time() - t_audio_start
                        expected = frames_sent * FRAME_SLEEP
                        if expected > elapsed_real:
                            await asyncio.sleep(expected - elapsed_real)

                    print(f"\n[{elapsed():7.3f}s] WAV complete ({frames_sent} frames). "
                          f"Waiting 3s for endpointing to fire...")
                    await asyncio.sleep(3.0)

                else:
                    # Mic capture
                    try:
                        import sounddevice as sd
                        q: asyncio.Queue = asyncio.Queue()

                        def cb(indata, frames_in, ti, status):
                            pcm = (indata[:, 0] * 32767).astype(np.int16)
                            try:
                                q.put_nowait(pcm.tobytes())
                            except Exception:
                                pass

                        stream = sd.InputStream(
                            samplerate=16000, channels=1, dtype="float32",
                            blocksize=FRAME_SAMPLES, callback=cb
                        )
                        stream.start()
                        try:
                            while not stop_sending.is_set():
                                try:
                                    chunk = await asyncio.wait_for(q.get(), timeout=0.3)
                                    await ws.send(chunk)
                                    frames_sent += 1
                                except asyncio.TimeoutError:
                                    continue
                        finally:
                            stream.stop()
                            # Give NeMo 2s to fire final endpointing after mic stops
                            print(f"\n[{elapsed():7.3f}s] Mic stopped. Waiting 2s for endpointing...")
                            await asyncio.sleep(2.0)

                    except ImportError:
                        print("[ERROR] sounddevice not installed: .venv\\Scripts\\pip install sounddevice")
                        print("  Use --wav option instead.")
                        return

                # Graceful commit — let NeMo finalize any remaining audio
                try:
                    await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                    print(f"[{elapsed():7.3f}s] input_audio_buffer.commit sent")
                    # Wait up to 10s for committed acknowledgment
                    await asyncio.sleep(10.0)
                except Exception as e:
                    print(f"[{elapsed():7.3f}s] commit error: {e}")

            # ── Event receiver ────────────────────────────────────────────
            async def recv_events():
                global delta_count, completed_count, running_partial
                t_first_delta = None

                try:
                    async for raw_msg in ws:
                        if isinstance(raw_msg, bytes):
                            continue
                        try:
                            data = json.loads(raw_msg)
                        except Exception:
                            continue

                        record(data)
                        mtype = data.get("type", "")
                        t = elapsed()

                        # DELTA
                        if mtype == "conversation.item.input_audio_transcription.delta":
                            delta_count += 1
                            frag = data.get("delta", "")
                            audio_t = data.get("audio_processed", 0)

                            if t_first_delta is None:
                                t_first_delta = t
                                print(f"[{t:7.3f}s] *** FIRST DELTA (latency={t:.3f}s from connect)")

                            if frag:
                                running_partial += frag
                                display = running_partial
                                if len(display) > 72:
                                    display = "..." + display[-69:]
                                print(f"\r[{t:7.3f}s] LIVE [{audio_t:.1f}s]: {display}    ",
                                      end="", flush=True)

                        # COMPLETED
                        elif mtype == "conversation.item.input_audio_transcription.completed":
                            completed_count += 1
                            transcript = data.get("transcript", "")
                            words = data.get("words", [])
                            seg_start = data.get("start", 0)
                            seg_end = data.get("end", 0)

                            # Reset partial — next utterance is a new segment
                            running_partial = ""

                            print(f"\n{'─'*60}")
                            print(f"[{t:7.3f}s] *** COMPLETED #{completed_count} ***")
                            print(f"  text     : '{transcript}'")
                            print(f"  timing   : {seg_start:.2f}s → {seg_end:.2f}s")
                            print(f"  words    : {len(words)}")

                            if words:
                                spk_counts: dict = {}
                                for w in words:
                                    s = w.get("speaker")
                                    if s is not None:
                                        spk_counts[s] = spk_counts.get(s, 0) + 1
                                print(f"  speakers : {spk_counts}  "
                                      f"(1-based int → speaker_0, speaker_1 after mapping)")
                                print(f"  sample   :", end="")
                                for w in words[:4]:
                                    print(f" '{w.get('word')}'[spk={w.get('speaker')}]", end="")
                                print()
                            else:
                                print(f"  [!] words[] empty — no word-level speaker data")
                            print(f"{'─'*60}\n")

                        # COMMITTED
                        elif mtype == "input_audio_buffer.committed":
                            print(f"\n[{t:7.3f}s] input_audio_buffer.committed — session complete")
                            return

                        # ERROR
                        elif mtype == "error":
                            err = data.get("error", {})
                            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                            print(f"\n[{t:7.3f}s] SERVER ERROR: {msg}")

                        else:
                            print(f"\n[{t:7.3f}s] {mtype}")

                except websockets.exceptions.ConnectionClosedError as e:
                    code = e.rcvd.code if e.rcvd else "?"
                    reason = e.rcvd.reason if e.rcvd else ""
                    print(f"\n[{elapsed():7.3f}s] SERVER CLOSED CONNECTION  code={code}  reason='{reason}'")
                    if code == 1011:
                        print(f"  code 1011 = Internal server error on the NeMo side")
                        print(f"  Possible causes:")
                        print(f"    - Audio format issue (sample rate, bit depth)")
                        print(f"    - CUDA/VRAM pressure during sustained streaming")
                        print(f"    - NeMo streaming-RNNT state accumulation bug")
                        print(f"    - Known NeMo-Speech.cpp issue with long sessions")
                        print(f"  Check Window 1 (nemo-speech serve) for the server-side error message.")
                    elif code == 1000:
                        print(f"  code 1000 = Normal closure (expected)")
                except websockets.exceptions.ConnectionClosedOK:
                    print(f"\n[{elapsed():7.3f}s] Connection closed normally")
                except Exception as ex:
                    print(f"\n[{elapsed():7.3f}s] recv error: {type(ex).__name__}: {ex}")

            # Run both tasks
            send_task = asyncio.create_task(send_audio())
            recv_task = asyncio.create_task(recv_events())

            try:
                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=300,
                )
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
            except KeyboardInterrupt:
                stop_sending.set()
                await asyncio.sleep(2.5)

    except ConnectionRefusedError:
        print(f"[ERROR] Cannot connect to {NEMO_URL}")
        print(f"  Start NeMo server first:")
        print(f"  nemo-speech serve --asr-model nemotron-3.5 --diar-model nemotron-3-diarization --port 8090")
        return
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return

    # ── Summary ──────────────────────────────────────────────────────────────
    total = elapsed()
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"  Total time   : {total:.2f}s")
    print(f"  Deltas       : {delta_count}")
    print(f"  Completed    : {completed_count}")
    print()

    if delta_count == 0 and completed_count == 0:
        print("  [?] No events received at all")
        print("      → Check NeMo server is running on port 8090")
        print("      → Check microphone permission")
    elif delta_count == 0 and completed_count > 0:
        empty = all(
            not e.get("transcript", "").strip()
            for e in all_events
            if e.get("type") == "conversation.item.input_audio_transcription.completed"
        )
        if empty:
            print("  [INFO] 0 deltas, 1 completed with empty text")
            print("         → Audio reached NeMo and was processed successfully")
            print("         → No speech detected (normal for synthetic/silent audio)")
        else:
            print("  [?] Completed events but no deltas")
            print("      → Endpointing fired but partials not emitted")
    elif delta_count > 0 and completed_count == 0:
        print(f"  [!] {delta_count} deltas but 0 completed events")
        print(f"      → Endpointing did not fire at {endpointing_ms}ms")
        print(f"      → Was there a 1011 server error above?")
        print(f"      → If yes: check Window 1 (nemo-speech serve) for the crash reason")
        print(f"      → If no:  try natural speech + wait 3s in silence before Ctrl+C")
    else:
        print(f"  [OK] delta={delta_count} completed={completed_count}")
        print(f"       → ASR pipeline working correctly end-to-end")

    # Save events
    log_file = LOGS_DIR / "nvidia_events.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for e in all_events:
            f.write(json.dumps(e) + "\n")
    print(f"\n  Events log : {log_file}")

    example_file = LOGS_DIR / "example_event_flow.json"
    with open(example_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, indent=2)
    print(f"  Full log   : {example_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeMo-Speech.cpp direct WebSocket test")
    parser.add_argument("--no-diarization", action="store_true",
                        help="Disable speaker diarization (isolate ASR)")
    parser.add_argument("--wav", type=str, default=None,
                        help="WAV file to stream instead of microphone")
    parser.add_argument("--endpointing", type=int, default=800,
                        help="End-of-utterance silence threshold ms (default 800)")
    args = parser.parse_args()

    try:
        asyncio.run(run(
            diarization=not args.no_diarization,
            wav_path=args.wav,
            endpointing_ms=args.endpointing,
        ))
    except KeyboardInterrupt:
        print("\nStopped.")

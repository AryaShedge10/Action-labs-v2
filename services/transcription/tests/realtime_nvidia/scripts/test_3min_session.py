"""
Point 7: 3-minute sustained session test.
Tests whether:
  - Server stays up past the 77s 1011 crash point
  - Completed events fire mid-conversation (endpointing)
  - Speaker changes are detected
  - Stop-to-final time

Run:
    .venv\Scripts\python scripts\test_3min_session.py
    .venv\Scripts\python scripts\test_3min_session.py --duration 180

Will use microphone. Speak naturally for the duration, then let it auto-stop.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

try:
    import numpy as np
    import sounddevice as sd
    import websockets
except ImportError as e:
    print(f"Missing: {e}")
    print("Run: .venv\\Scripts\\pip install websockets numpy sounddevice")
    sys.exit(1)

NEMO_URL = "ws://127.0.0.1:8090/v1/audio/transcriptions/realtime"
LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


async def run(duration_s: int, endpointing_ms: int):
    print(f"\n{'='*60}")
    print(f"3-Minute Sustained Session Test")
    print(f"  Duration:     {duration_s}s")
    print(f"  Endpointing:  {endpointing_ms}ms")
    print(f"  URL:          {NEMO_URL}")
    print(f"{'='*60}\n")
    print("Speak naturally for the full duration.")
    print("Try: doctor/patient sentences with natural pauses.\n")

    t_connect = time.time()
    delta_count = 0
    completed_count = 0
    server_error = None
    all_events = []
    running_partial = ""

    completed_timestamps = []
    speaker_changes = []
    last_speaker = None

    async with websockets.connect(NEMO_URL, max_size=10*1024*1024, open_timeout=10) as ws:
        # session.created
        raw = await ws.recv()
        data = json.loads(raw)
        print(f"[{time.time()-t_connect:.2f}s] session.created")

        # session.update
        await ws.send(json.dumps({"type": "session.update", "session": {
            "sample_rate": 16000, "language": "en-US",
            "automatic_punctuation": True, "word_timestamps": True,
            "speaker_diarization": True, "endpointing_ms": endpointing_ms,
        }}))

        raw = await ws.recv()
        print(f"[{time.time()-t_connect:.2f}s] session.updated")

        stop_flag = asyncio.Event()

        async def send_audio():
            FRAME = 2560
            q: asyncio.Queue = asyncio.Queue()
            def cb(indata, frames_in, ti, status):
                pcm = (indata[:,0] * 32767).astype(np.int16)
                try: q.put_nowait(pcm.tobytes())
                except: pass

            stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                    blocksize=FRAME, callback=cb)
            stream.start()
            t_end = time.time() + duration_s
            frames = 0
            while time.time() < t_end and not stop_flag.is_set():
                try:
                    chunk = await asyncio.wait_for(q.get(), timeout=0.3)
                    await ws.send(chunk)
                    frames += 1
                except asyncio.TimeoutError:
                    continue
            stream.stop()
            elapsed = time.time() - t_connect
            print(f"\n[{elapsed:.2f}s] Audio stopped ({frames} frames). Committing...")
            await asyncio.sleep(3.0)  # wait for endpointing
            try:
                await ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                print(f"[{time.time()-t_connect:.2f}s] Committed")
            except Exception as e:
                print(f"commit error: {e}")

        async def recv_events():
            nonlocal delta_count, completed_count, server_error, running_partial
            nonlocal last_speaker

            try:
                async for raw_msg in ws:
                    if isinstance(raw_msg, bytes): continue
                    try: data = json.loads(raw_msg)
                    except: continue

                    all_events.append({"t": round(time.time()-t_connect, 3), **data})
                    mtype = data.get("type", "")
                    t = time.time() - t_connect

                    if mtype == "conversation.item.input_audio_transcription.delta":
                        delta_count += 1
                        frag = data.get("delta", "")
                        if frag:
                            running_partial += frag
                            display = running_partial[-60:] if len(running_partial) > 60 else running_partial
                            print(f"\r[{t:.2f}s] LIVE: {display}    ", end="", flush=True)

                    elif mtype == "conversation.item.input_audio_transcription.completed":
                        completed_count += 1
                        transcript = data.get("transcript", "")
                        words = data.get("words", [])
                        running_partial = ""

                        # Speaker detection
                        spk_counts: dict = {}
                        for w in words:
                            s = w.get("speaker")
                            if s is not None:
                                spk_counts[s] = spk_counts.get(s, 0) + 1
                        dominant = max(spk_counts, key=spk_counts.get) if spk_counts else None

                        if dominant and dominant != last_speaker:
                            if last_speaker is not None:
                                speaker_changes.append({
                                    "at_s": round(t, 2),
                                    "from": last_speaker,
                                    "to": dominant
                                })
                            last_speaker = dominant

                        completed_timestamps.append(round(t, 2))

                        print(f"\n[{t:.2f}s] COMPLETED #{completed_count}  "
                              f"spk={dominant}  words={len(words)}  "
                              f"text='{transcript[:60]}'")

                    elif mtype == "input_audio_buffer.committed":
                        print(f"\n[{t:.2f}s] COMMITTED — session complete")
                        stop_flag.set()
                        return

                    elif mtype == "error":
                        server_error = data.get("error", str(data))
                        print(f"\n[{t:.2f}s] SERVER ERROR: {server_error}")

            except websockets.exceptions.ConnectionClosedError as e:
                code = e.rcvd.code if e.rcvd else "?"
                server_error = f"code={code}"
                t = time.time() - t_connect
                print(f"\n[{t:.2f}s] CONNECTION CLOSED  {server_error}")
                if code == 1011:
                    print(f"  1011 = NeMo internal error — check Window 1 for crash message")
                stop_flag.set()

        send_task = asyncio.create_task(send_audio())
        recv_task = asyncio.create_task(recv_events())
        await asyncio.gather(send_task, recv_task, return_exceptions=True)

    total = time.time() - t_connect

    # ── Report ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"POINT 7 REPORT — {duration_s}s SUSTAINED SESSION")
    print(f"{'='*60}")
    print(f"  Total wall time      : {total:.2f}s")
    print(f"  Delta events         : {delta_count}")
    print(f"  Completed events     : {completed_count}")
    print(f"  Server error         : {server_error or 'None'}")
    print(f"  Server stayed up     : {'YES — past 77s' if total > 77 and not server_error else 'NO — crashed at ' + f'{total:.1f}s' if server_error else 'YES'}")
    print()
    print(f"  Endpointing fired    : {'YES' if completed_count > 0 else 'NO'}")
    if completed_timestamps:
        intervals = [completed_timestamps[i+1] - completed_timestamps[i]
                     for i in range(len(completed_timestamps)-1)]
        print(f"  Completed at times   : {completed_timestamps}")
        if intervals:
            print(f"  Avg between finals   : {sum(intervals)/len(intervals):.2f}s")
    print()
    print(f"  Speaker changes      : {len(speaker_changes)}")
    for sc in speaker_changes:
        print(f"    at {sc['at_s']}s: speaker {sc['from']} → {sc['to']}")
    print()

    # Stop-to-final estimate
    if completed_timestamps:
        last_final_t = completed_timestamps[-1]
        print(f"  Last completed at    : {last_final_t:.2f}s (of {total:.2f}s total)")
    print(f"{'='*60}")

    # Save log
    log = LOGS_DIR / f"session_3min_{int(time.time())}.json"
    with open(log, "w", encoding="utf-8") as f:
        json.dump({
            "duration_s": duration_s,
            "total_wall_s": round(total, 2),
            "delta_count": delta_count,
            "completed_count": completed_count,
            "server_error": server_error,
            "completed_timestamps": completed_timestamps,
            "speaker_changes": speaker_changes,
            "events": all_events[:200],
        }, f, indent=2)
    print(f"\n  Log saved: {log}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=180, help="Test duration in seconds")
    parser.add_argument("--endpointing", type=int, default=800, help="Endpointing ms")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.duration, args.endpointing))
    except KeyboardInterrupt:
        print("\nStopped manually.")

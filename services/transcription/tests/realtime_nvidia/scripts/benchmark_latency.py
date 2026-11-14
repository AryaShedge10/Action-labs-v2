"""
Latency Benchmark Script — NVIDIA NeMo-Speech.cpp Realtime
tests/realtime_nvidia/scripts/benchmark_latency.py

Phase 37: Measures all defined latency metrics.
Phase 38: Sustained realtime test (60s / 5min / 20min modes).
Phase 39: GPU profiling where available.

Run from tests/realtime_nvidia/:
    .venv\Scripts\python scripts\benchmark_latency.py --duration 60
    .venv\Scripts\python scripts\benchmark_latency.py --duration 300
    .venv\Scripts\python scripts\benchmark_latency.py --duration 1200

Requires: test backend running on port 8004 + NeMo-Speech.cpp on port 8888.
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

try:
    import websockets
    import numpy as np
    import soundfile as sf
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Activate test venv: .venv\\Scripts\\activate")
    raise SystemExit(1)

BACKEND_WS = "ws://127.0.0.1:8004/test/realtime/{session_id}/stream"
BACKEND_START = "http://127.0.0.1:8004/test/realtime/start"
BACKEND_STOP = "http://127.0.0.1:8004/test/realtime/{session_id}/stop"

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class LatencyBenchmark:
    """Measures realtime latency from audio send to transcript visibility."""

    def __init__(self):
        self.t_capture_start: float = 0.0
        self.t_first_audio_sent: float = 0.0
        self.t_first_asr_event: float = 0.0
        self.t_first_visible_text: float = 0.0
        self.t_first_partial: float = 0.0
        self.t_first_final: float = 0.0
        self.t_stop: float = 0.0
        self.t_final_transcript_saved: float = 0.0

        self.partial_events: list = []
        self.final_events: list = []
        self.speaker_events: list = []

        self.segment_count = 0
        self.duplicate_count = 0
        self.dropped_frames = 0

        self._seen_segment_ids: set = set()
        self._seen_segment_texts: dict = {}   # seg_id → last text

    def record_partial(self, seg: dict, recv_time: float):
        seg_id = seg.get("segment_id", "")
        text = seg.get("text", "")

        if self.t_first_asr_event == 0.0:
            self.t_first_asr_event = recv_time
        if text and self.t_first_visible_text == 0.0:
            self.t_first_visible_text = recv_time
        if seg.get("status") == "LIVE" and self.t_first_partial == 0.0:
            self.t_first_partial = recv_time

        # Duplicate detection: same seg_id + same text = duplicate event
        if seg_id in self._seen_segment_texts:
            if self._seen_segment_texts[seg_id] == text:
                self.duplicate_count += 1

        self._seen_segment_texts[seg_id] = text
        self._seen_segment_ids.add(seg_id)
        self.partial_events.append({"time": recv_time, "seg_id": seg_id, "len": len(text)})

    def record_final(self, seg: dict, recv_time: float):
        if self.t_first_final == 0.0:
            self.t_first_final = recv_time
        self.segment_count += 1
        self.final_events.append({
            "time": recv_time,
            "seg_id": seg.get("segment_id"),
            "role": seg.get("role"),
            "len": len(seg.get("text", "")),
        })

    def record_speaker(self, seg: dict, recv_time: float):
        self.speaker_events.append({
            "time": recv_time,
            "seg_id": seg.get("segment_id"),
            "role": seg.get("role"),
        })

    def compute_metrics(self) -> dict:
        base = self.t_capture_start or self.t_first_audio_sent

        def ms_since(t: float) -> float:
            if t == 0.0 or base == 0.0:
                return None
            return round((t - base) * 1000.0, 2)

        # Sustained backlog: average gap between consecutive partial events
        backlog_ms = 0.0
        if len(self.partial_events) >= 2:
            gaps = []
            for i in range(1, len(self.partial_events)):
                gaps.append(self.partial_events[i]["time"] - self.partial_events[i-1]["time"])
            backlog_ms = round(sum(gaps) / len(gaps) * 1000.0, 2)

        # RTF approximation from session duration
        total_wall = 0.0
        if self.t_stop > 0 and self.t_capture_start > 0:
            total_wall = round(self.t_stop - self.t_capture_start, 2)

        return {
            "time_to_first_asr_event_ms": ms_since(self.t_first_asr_event),
            "time_to_first_visible_text_ms": ms_since(self.t_first_visible_text),
            "time_to_first_partial_ms": ms_since(self.t_first_partial),
            "time_to_first_final_turn_ms": ms_since(self.t_first_final),
            "stop_to_final_ms": (
                round((self.t_final_transcript_saved - self.t_stop) * 1000.0, 2)
                if self.t_stop > 0 and self.t_final_transcript_saved > 0 else None
            ),
            "sustained_backlog_avg_ms": backlog_ms,
            "total_partial_events": len(self.partial_events),
            "total_final_segments": self.segment_count,
            "speaker_revisions": len(self.speaker_events),
            "duplicate_events": self.duplicate_count,
            "dropped_frames": self.dropped_frames,
            "wall_clock_s": total_wall,
        }


async def run_benchmark(duration_s: int, audio_file: str = None) -> dict:
    """
    Stream audio (from file or synthetic) through backend and measure latency.
    """
    import httpx

    bm = LatencyBenchmark()

    print(f"\n[Benchmark] Starting {duration_s}s test...")

    # -- Start session --
    async with httpx.AsyncClient() as http:
        r = await http.post(BACKEND_START, timeout=15)
        if r.status_code != 200:
            raise RuntimeError(f"Backend start failed: {r.status_code} {r.text}")
        session_data = r.json()

    session_id = session_data["session_id"]
    print(f"[Benchmark] Session: {session_id}")

    ws_url = BACKEND_WS.format(session_id=session_id)

    # -- Load or generate audio --
    if audio_file and Path(audio_file).exists():
        audio_data, sr = sf.read(audio_file, dtype="int16")
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)
        if sr != 16000:
            print(f"[WARN] Audio is {sr}Hz — NeMo expects 16kHz")
    else:
        # Generate test signal (sine tone — not real speech)
        print("[INFO] No audio file provided — using synthetic sine tone (latency test only)")
        t = np.linspace(0, duration_s, duration_s * 16000, endpoint=False)
        audio_data = (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        audio_data = (audio_data * 32767).astype(np.int16)

    raw_bytes = audio_data.tobytes()
    frame_bytes = 1600 * 2  # 100ms frames

    bm.t_capture_start = time.time()

    # -- Stream audio and receive events --
    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        async def send_audio():
            nonlocal bm
            first = True
            for i in range(0, len(raw_bytes), frame_bytes):
                chunk = raw_bytes[i: i + frame_bytes]
                if not chunk:
                    break
                try:
                    await ws.send(chunk)
                    if first:
                        bm.t_first_audio_sent = time.time()
                        first = False
                except Exception as e:
                    bm.dropped_frames += 1
                    print(f"[WARN] Frame drop: {e}")
                await asyncio.sleep(0.1)

            await asyncio.sleep(0.5)
            bm.t_stop = time.time()
            await ws.send(json.dumps({"action": "stop"}))

        async def recv_events():
            async for raw in ws:
                t_recv = time.time()
                try:
                    ev = json.loads(raw)
                except Exception:
                    continue

                ev_type = ev.get("type", "")

                if ev_type == "segment_update":
                    seg = ev.get("segment", {})
                    if seg.get("status") == "LIVE":
                        bm.record_partial(seg, t_recv)
                    elif seg.get("status") == "FINAL":
                        bm.record_final(seg, t_recv)

                elif ev_type == "speaker_revision":
                    seg = ev.get("segment", {})
                    bm.record_speaker(seg, t_recv)

                elif ev_type == "final_summary":
                    bm.t_final_transcript_saved = t_recv
                    segs = ev.get("all_segments", [])
                    for s in segs:
                        bm.record_final(s, t_recv)
                    return  # Done

        try:
            await asyncio.wait_for(
                asyncio.gather(send_audio(), recv_events()),
                timeout=duration_s + 30,
            )
        except asyncio.TimeoutError:
            print(f"[WARN] Benchmark timeout after {duration_s + 30}s")

    metrics = bm.compute_metrics()
    return metrics


def format_report(metrics: dict, duration_s: int, latency_mode: str) -> str:
    def fmt(v):
        if v is None:
            return "N/A"
        if isinstance(v, float):
            return f"{v:.1f}"
        return str(v)

    lines = [
        f"# Latency Benchmark — {duration_s}s Sustained Test",
        f"",
        f"Latency Mode: {latency_mode}",
        f"GPU: NVIDIA GeForce GTX 1650 (4096 MiB VRAM)",
        f"CUDA: 13.1 | Driver: 592.27",
        f"",
        f"## Latency Metrics",
        f"",
        f"| Metric | Measured |",
        f"|--------|----------|",
        f"| First ASR event | {fmt(metrics['time_to_first_asr_event_ms'])} ms |",
        f"| First visible text | {fmt(metrics['time_to_first_visible_text_ms'])} ms |",
        f"| First partial | {fmt(metrics['time_to_first_partial_ms'])} ms |",
        f"| First final turn | {fmt(metrics['time_to_first_final_turn_ms'])} ms |",
        f"| Stop → final saved | {fmt(metrics['stop_to_final_ms'])} ms |",
        f"| Sustained backlog avg | {fmt(metrics['sustained_backlog_avg_ms'])} ms |",
        f"| Wall clock | {fmt(metrics['wall_clock_s'])} s |",
        f"",
        f"## Event Counts",
        f"",
        f"| Count | Value |",
        f"|-------|-------|",
        f"| Total partial events | {metrics['total_partial_events']} |",
        f"| Total final segments | {metrics['total_final_segments']} |",
        f"| Speaker revisions | {metrics['speaker_revisions']} |",
        f"| Duplicate events | {metrics['duplicate_events']} |",
        f"| Dropped frames | {metrics['dropped_frames']} |",
        f"",
        f"## Targets (Phase 54)",
        f"",
        f"| Target | Threshold | Status |",
        f"|--------|-----------|--------|",
    ]

    def status(actual, target_ms, lower_is_better=True):
        if actual is None:
            return "⚠️ N/A"
        ok = actual <= target_ms if lower_is_better else actual >= target_ms
        return "✅ PASS" if ok else "❌ MISS"

    lines += [
        f"| First visible < 1000ms | 1000ms | {status(metrics['time_to_first_visible_text_ms'], 1000)} |",
        f"| First partial < 1500ms | 1500ms | {status(metrics['time_to_first_partial_ms'], 1500)} |",
        f"| First final < 3000ms   | 3000ms | {status(metrics['time_to_first_final_turn_ms'], 3000)} |",
        f"| Stop→final < 2000ms    | 2000ms | {status(metrics['stop_to_final_ms'], 2000)} |",
        f"| Backlog < 500ms        | 500ms  | {status(metrics['sustained_backlog_avg_ms'], 500)} |",
        f"| Zero duplicates        | 0      | {'✅ PASS' if metrics['duplicate_events'] == 0 else '❌ FAIL'} |",
        f"| Zero dropped frames    | 0      | {'✅ PASS' if metrics['dropped_frames'] == 0 else '⚠️ ' + str(metrics['dropped_frames']) + ' dropped'} |",
    ]

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser(description="NVIDIA NeMo latency benchmark")
    parser.add_argument("--duration", type=int, default=60,
                        help="Test duration in seconds (60, 300, 1200)")
    parser.add_argument("--audio", type=str, default=None,
                        help="Path to WAV file (16kHz mono). Omit for synthetic tone.")
    parser.add_argument("--latency-mode", type=str, default="low_latency",
                        choices=["low_latency", "very_low_latency", "ultra_low_latency"],
                        help="NeMo-Speech.cpp latency mode to benchmark")
    args = parser.parse_args()

    print(f"[Benchmark] Duration: {args.duration}s | Mode: {args.latency_mode}")
    print(f"[Benchmark] NOTE: latency_mode must match what NeMo-Speech.cpp server was started with.")
    print(f"[Benchmark] Restart run_nemo_server.bat with desired mode before benchmarking.")

    metrics = await run_benchmark(args.duration, args.audio)

    report = format_report(metrics, args.duration, args.latency_mode)
    print("\n" + report)

    # Save report
    report_file = REPORTS_DIR / f"benchmark_{args.duration}s_{args.latency_mode}.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"\n[Benchmark] Report saved: {report_file}")

    # Also save raw metrics JSON
    metrics_file = REPORTS_DIR / f"benchmark_{args.duration}s_{args.latency_mode}.json"
    metrics_file.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"[Benchmark] Raw metrics: {metrics_file}")


if __name__ == "__main__":
    asyncio.run(main())

"""
Transcript formatter for generating structured JSON output compatible with Team B and Team C.
"""
from typing import List, Dict, Optional
from datetime import datetime
import json
from pathlib import Path


class TranscriptFormatter:
    """Formats transcription segments into structured JSON."""

    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def format(
        self,
        segments: List[Dict],
        session_id: Optional[str] = None,
        speaker_labels: Optional[Dict[int, str]] = None,
    ) -> Dict:
        """
        Format transcript segments into structured JSON.
        Guarantees both start_time/end_time (Team B) and start/end (Team C) compatibility.
        """
        if session_id is None:
            session_id = self._generate_session_id()

        formatted_segments = []
        for idx, segment in enumerate(segments):
            spk = speaker_labels.get(idx, "UNKNOWN") if speaker_labels else segment.get("speaker", "UNKNOWN")
            spk = str(spk).upper()
            st = float(segment.get("start", segment.get("start_time", 0.0)))
            et = float(segment.get("end", segment.get("end_time", st)))
            conf = float(segment.get("confidence", 0.95))

            formatted_segment = {
                "id": f"seg_{idx+1:03d}",
                "speaker": spk,
                "start": st,
                "end": et,
                "start_time": st,
                "end_time": et,
                "text": segment.get("text", "").strip(),
                "confidence": conf,
            }
            formatted_segments.append(formatted_segment)

        total_duration = segments[-1]["end"] if segments and "end" in segments[-1] else (
            formatted_segments[-1]["end"] if formatted_segments else 0.0
        )

        transcript = {
            "session_id": session_id,
            "consultation_id": session_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "model": "whisper-local",
            "segments": formatted_segments,
            "metadata": {
                "total_segments": len(formatted_segments),
                "total_duration": total_duration,
                "speaker_diarization": "applied" if speaker_labels else "heuristic",
            },
        }

        return transcript

    def save(self, transcript: Dict, output_path: Optional[str] = None) -> str:
        """
        Save transcript to JSON file.
        """
        sid = transcript.get("consultation_id") or transcript.get("session_id")
        if output_path is None:
            if sid:
                output_path = self.output_dir / f"session_{sid}.json"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = self.output_dir / f"session_{timestamp}.json"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript, f, indent=2, ensure_ascii=False)

        print(f"\n[OK] Transcript saved to: {output_path}")
        return str(output_path)

    def _generate_session_id(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}"

    def to_json_string(self, transcript: Dict, pretty: bool = True) -> str:
        if pretty:
            return json.dumps(transcript, indent=2, ensure_ascii=False)
        return json.dumps(transcript, ensure_ascii=False)

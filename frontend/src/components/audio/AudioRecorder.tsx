import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Square, Pause, Play, Upload, AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "../../services/api";
import type { Encounter } from "../../types/clinical";

interface AudioRecorderProps {
  onSuccess: (encounter: Encounter) => void;
}

export default function AudioRecorder({ onSuccess }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [patientId, setPatientId] = useState("");
  const [patientName, setPatientName] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setSelectedFile(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.start(250); // 250ms chunks
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);

      timerRef.current = window.setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);

      toast.info("Recording consultation audio...", {
        description: "Speak clearly into your microphone.",
      });
    } catch (err) {
      console.error("Microphone access error:", err);
      toast.error("Microphone Access Denied", {
        description: "Please check your browser permissions or upload an audio file instead.",
      });
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      timerRef.current = window.setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);
    }
  };

  const stopAndProcessRecording = async () => {
    if (!mediaRecorderRef.current) return;

    if (timerRef.current) clearInterval(timerRef.current);
    setIsRecording(false);
    setIsPaused(false);

    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      await uploadAudioBlob(audioBlob, "consultation_recording.webm");
    };

    mediaRecorderRef.current.stop();
  };

  const uploadAudioBlob = async (blob: Blob | File, filename: string) => {
    setIsUploading(true);
    const toastId = toast.loading("Processing audio through Clinical Scribe pipeline...", {
      description: "Transcribing speech and extracting clinical SOAP entities...",
    });

    try {
      const encounter = await api.uploadAudio(
        blob,
        undefined,
        patientId.trim() || undefined,
        patientName.trim() || undefined
      );
      toast.success("Encounter Generated!", {
        id: toastId,
        description: `Successfully created encounter ${encounter.encounter_id}.`,
      });
      onSuccess(encounter);
    } catch (err: any) {
      console.error("Pipeline failure:", err);
      toast.error("Pipeline Processing Error", {
        id: toastId,
        description: err.message || "Failed to transcribe or analyze audio.",
      });
    } finally {
      setIsUploading(false);
      setDuration(0);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      toast.info(`Selected audio file: ${file.name}`);
    }
  };

  const handleUploadSelectedFile = async () => {
    if (!selectedFile) return;
    await uploadAudioBlob(selectedFile, selectedFile.name);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="rounded-2xl border border-clinical-200/80 bg-white p-6 shadow-lift">
      <div className="flex items-center justify-between border-b border-ink-100 pb-4">
        <div>
          <h2 className="text-lg font-bold text-ink-900">Live Consultation Recording</h2>
          <p className="text-xs text-ink-500">
            Record speech directly in browser or upload recorded encounter audio.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isRecording ? (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 animate-pulse">
              <span className="h-2 w-2 rounded-full bg-red-600" />
              {isPaused ? "Paused" : "Live Recording"} · {formatTime(duration)}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800">
              <CheckCircle2 size={12} /> Ready
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            Patient ID (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. PT-98214"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            disabled={isRecording || isUploading}
            className="mt-1 w-full rounded-xl border border-ink-200 px-3 py-2 text-sm text-ink-900 placeholder-ink-400 focus:border-clinical-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="text-xs font-semibold uppercase tracking-wide text-ink-500">
            Patient Name (Optional)
          </label>
          <input
            type="text"
            placeholder="e.g. Jane Doe"
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            disabled={isRecording || isUploading}
            className="mt-1 w-full rounded-xl border border-ink-200 px-3 py-2 text-sm text-ink-900 placeholder-ink-400 focus:border-clinical-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-xl bg-ink-50 p-4">
        <div className="flex items-center gap-3">
          {!isRecording ? (
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={startRecording}
              disabled={isUploading}
              className="inline-flex items-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-semibold text-white shadow-soft hover:bg-red-700 disabled:opacity-50"
            >
              <Mic size={16} /> Start Recording
            </motion.button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={isPaused ? resumeRecording : pauseRecording}
                className="inline-flex items-center gap-1.5 rounded-xl border border-ink-300 bg-white px-3 py-2 text-xs font-semibold text-ink-700 hover:bg-ink-100"
              >
                {isPaused ? <Play size={14} /> : <Pause size={14} />}
                {isPaused ? "Resume" : "Pause"}
              </button>
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={stopAndProcessRecording}
                className="inline-flex items-center gap-2 rounded-xl bg-clinical-900 px-4 py-2.5 text-sm font-semibold text-white shadow-lift hover:bg-clinical-800"
              >
                <Square size={16} /> End &amp; Generate Note
              </motion.button>
            </div>
          )}

          <div className="h-6 w-px bg-ink-200 hidden sm:block" />

          <div>
            <input
              type="file"
              ref={fileInputRef}
              accept="audio/*,.wav,.mp3,.m4a,.webm,.ogg"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isRecording || isUploading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-ink-200 bg-white px-3 py-2 text-xs font-medium text-ink-700 shadow-soft hover:border-clinical-300 disabled:opacity-50"
            >
              <Upload size={14} />
              {selectedFile ? selectedFile.name : "Choose Audio File"}
            </button>
          </div>

          {selectedFile && !isRecording && (
            <button
              onClick={handleUploadSelectedFile}
              disabled={isUploading}
              className="inline-flex items-center gap-1.5 rounded-xl bg-clinical-700 px-3 py-2 text-xs font-semibold text-white hover:bg-clinical-800 disabled:opacity-50"
            >
              Process File
            </button>
          )}
        </div>

        {isUploading && (
          <div className="flex items-center gap-2 text-xs font-medium text-clinical-800 animate-pulse">
            <RefreshCw size={14} className="animate-spin" />
            Transcribing &amp; extracting clinical note...
          </div>
        )}
      </div>
    </div>
  );
}


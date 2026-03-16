import { useRef, useCallback, useEffect } from "react";
import { toast } from "./useToast";

interface UseVoiceCaptureOptions {
  onTranscript: (text: string) => void;
}

interface UseVoiceCaptureReturn {
  isListening: boolean;
  start: () => void;
  stop: () => void;
  toggle: () => void;
  transcript: string;
}

// Check for browser support
const SpeechRecognition =
  typeof window !== "undefined"
    ? window.SpeechRecognition ?? window.webkitSpeechRecognition
    : undefined;

export function useVoiceCapture({
  onTranscript,
}: UseVoiceCaptureOptions): UseVoiceCaptureReturn {
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isListeningRef = useRef(false);
  const transcriptRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  // We track listening state via ref to avoid stale closures;
  // the caller uses isMicActive from App state for rendering.

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      isListeningRef.current = false;
      try {
        recognitionRef.current.stop();
      } catch {
        // already stopped
      }
      recognitionRef.current = null;
    }
  }, []);

  const start = useCallback(() => {
    if (!SpeechRecognition) {
      toast.show("Speech recognition not supported in this browser", "error");
      return;
    }

    // Stop any existing session
    stop();

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let final = "";
      let interim = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }

      if (final) {
        transcriptRef.current = final.trim();
        onTranscriptRef.current(final.trim());
        toast.success(`Voice: "${final.trim().slice(0, 60)}..."`);
      }

      if (interim) {
        transcriptRef.current = interim;
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      if (event.error === "not-allowed") {
        toast.show("Microphone permission denied", "error");
      } else if (event.error !== "aborted") {
        toast.show(`Voice error: ${event.error}`, "error");
      }
      isListeningRef.current = false;
    };

    recognition.onend = () => {
      // Restart if we're still supposed to be listening
      if (isListeningRef.current && recognitionRef.current) {
        try {
          recognitionRef.current.start();
        } catch {
          isListeningRef.current = false;
        }
      }
    };

    recognitionRef.current = recognition;
    isListeningRef.current = true;

    try {
      recognition.start();
      toast.show("Microphone active - listening...", "info");
    } catch {
      toast.show("Failed to start speech recognition", "error");
      isListeningRef.current = false;
    }
  }, [stop]);

  const toggle = useCallback(() => {
    if (isListeningRef.current) {
      stop();
      toast.show("Microphone deactivated", "info");
    } else {
      start();
    }
  }, [start, stop]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  return {
    isListening: isListeningRef.current,
    start,
    stop,
    toggle,
    transcript: transcriptRef.current,
  };
}

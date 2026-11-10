import { useEffect, useRef, useState } from "react";

interface Recognition {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult:
    | ((event: {
        resultIndex: number;
        results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
      }) => void)
    | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type VoiceWindow = Window & {
  SpeechRecognition?: new () => Recognition;
  webkitSpeechRecognition?: new () => Recognition;
};
function recognitionConstructor() {
  const browser = window as VoiceWindow;
  return browser.SpeechRecognition || browser.webkitSpeechRecognition;
}

export function useVoiceEnquiry() {
  const [language, setLanguage] = useState<"en" | "te">("te");
  const [preparing, setPreparing] = useState(false);
  const audio = useRef<AudioContext | null>(null);
  const source = useRef<AudioBufferSourceNode | null>(null);
  const generation = useRef(0);
  const synthesis = useRef<AbortController | null>(null);
  const teluguVoice = useRef<Promise<import("ninada").NinadaVoice> | null>(
    null,
  );
  function prepareAudio() {
    if (language !== "te" || !("AudioContext" in window)) return;
    try {
      audio.current ??= new AudioContext();
      void audio.current.resume().catch(() => {});
    } catch {
      /* Playback reports a useful error when requested. */
    }
  }
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [voiceError, setVoiceError] = useState("");
  const [readAloud, setReadAloud] = useState(true);
  const recognition = useRef<Recognition | null>(null);
  const utterance = useRef<SpeechSynthesisUtterance | null>(null);
  const recognitionAvailable = !!recognitionConstructor();
  const nativeSpeechAvailable =
    "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
  const speechAvailable =
    language === "te" ? "AudioContext" in window : nativeSpeechAvailable;

  function stopSpeaking() {
    generation.current += 1;
    synthesis.current?.abort();
    synthesis.current = null;
    if (source.current) {
      source.current.onended = null;
      source.current.stop();
      source.current = null;
    }
    setPreparing(false);
    if (utterance.current) {
      utterance.current.onend = null;
      utterance.current.onerror = null;
      utterance.current = null;
    }
    if (nativeSpeechAvailable) window.speechSynthesis.cancel();
    setSpeaking(false);
  }
  function cancelListening() {
    const active = recognition.current;
    recognition.current = null;
    if (active) {
      active.onresult = null;
      active.onerror = null;
      active.onend = null;
      active.abort();
    }
    setListening(false);
  }
  function cancel() {
    cancelListening();
    stopSpeaking();
    setTranscript("");
    setVoiceError("");
  }
  async function speak(text: string, replyLanguage: "en" | "te" = language) {
    stopSpeaking();
    if (!text.trim()) return;
    if (replyLanguage === "en" && !nativeSpeechAvailable) return;
    if (replyLanguage === "te" && !("AudioContext" in window)) return;
    cancelListening();
    setVoiceError("");
    if (replyLanguage === "te") {
      await speakTelugu(text);
      return;
    }
    const speech = new SpeechSynthesisUtterance(
      text
        .replace(/₹/g, " rupees ")
        .replace(/→/g, " to ")
        .replace(/[*#`]/g, ""),
    );
    speech.lang = "en-IN";
    speech.rate = 0.95;
    const voices = window.speechSynthesis.getVoices();
    const voice =
      voices.find((item) => item.lang === "en-IN") ||
      voices.find((item) => item.lang.startsWith("en"));
    if (voice) speech.voice = voice;
    speech.onend = () => {
      if (utterance.current === speech) {
        utterance.current = null;
        setSpeaking(false);
      }
    };
    speech.onerror = () => {
      if (utterance.current === speech) {
        utterance.current = null;
        setSpeaking(false);
        setVoiceError(
          "Audio playback failed. You can read the reply below or try Read reply again.",
        );
      }
    };
    utterance.current = speech;
    setSpeaking(true);
    try {
      window.speechSynthesis.speak(speech);
    } catch {
      utterance.current = null;
      setSpeaking(false);
      setVoiceError(
        "Audio playback is unavailable. Please read the reply below.",
      );
    }
  }
  async function speakTelugu(text: string) {
    const current = generation.current;
    const controller = new AbortController();
    synthesis.current = controller;
    setPreparing(true);
    try {
      audio.current ??= new AudioContext();
      await audio.current.resume();
      teluguVoice.current ??= import("../ninada")
        .then(({ createTeluguVoice }) => createTeluguVoice())
        .catch((error) => {
          teluguVoice.current = null;
          throw error;
        });
      const voice = await teluguVoice.current;
      if (generation.current !== current) return;
      const wav = await voice.speak(
        text
          .replace(/₹/g, " రూపాయలు ")
          .replace(/→/g, " నుంచి ")
          .replace(/[*#`]/g, ""),
        { lang: "te", voice: "female", signal: controller.signal },
      );
      if (generation.current !== current) return;
      const buffer = await audio.current.decodeAudioData(wav);
      if (generation.current !== current) return;
      const player = audio.current.createBufferSource();
      player.buffer = buffer;
      player.connect(audio.current.destination);
      player.onended = () => {
        if (generation.current === current) {
          setSpeaking(false);
          source.current = null;
        }
      };
      source.current = player;
      setPreparing(false);
      setSpeaking(true);
      player.start();
    } catch {
      if (generation.current === current) {
        setPreparing(false);
        setSpeaking(false);
        setVoiceError(
          "తెలుగు వాయిస్ లోడ్ కాలేదు. ఇంటర్నెట్ కనెక్షన్ తనిఖీ చేసి మళ్లీ ప్రయత్నించండి. Telugu audio unavailable; please read the reply below.",
        );
      }
    }
  }
  function toggleListening(onTranscript: (text: string) => void) {
    if (recognition.current) {
      recognition.current.stop();
      return;
    }
    stopSpeaking();
    const Constructor = recognitionConstructor();
    if (!Constructor) {
      setVoiceError(
        "Voice input is unavailable in this browser. Please type your enquiry below.",
      );
      return;
    }
    const active = new Constructor();
    recognition.current = active;
    prepareAudio();
    active.lang = language === "te" ? "te-IN" : "en-IN";
    active.continuous = false;
    active.interimResults = true;
    setTranscript("");
    setVoiceError("");
    let submitted = false;
    active.onresult = (event) => {
      if (recognition.current !== active || submitted) return;
      const result = event.results[event.resultIndex];
      if (!result) return;
      const text = result[0].transcript.trim();
      setTranscript(text);
      if (result.isFinal && text) {
        submitted = true;
        recognition.current = null;
        active.onresult = null;
        active.onerror = null;
        active.onend = null;
        active.abort();
        setListening(false);
        onTranscript(text);
      }
    };
    active.onerror = ({ error }) => {
      if (recognition.current !== active) return;
      setListening(false);
      const errors: Record<string, string> = {
        "not-allowed":
          "Microphone access was denied. Allow microphone access in your browser settings, then try again.",
        "service-not-allowed":
          "Speech recognition is disabled by your browser. Please type your enquiry.",
        "audio-capture":
          "No microphone was found. Connect a microphone and try again.",
        "no-speech":
          "No speech was detected. Tap the microphone and try again.",
        network:
          "The speech service could not connect. Check your connection or type your enquiry.",
      };
      if (error !== "aborted")
        setVoiceError(
          errors[error] ||
            "Voice input failed. Please try again or type your enquiry.",
        );
    };
    active.onend = () => {
      if (recognition.current === active) {
        recognition.current = null;
        setListening(false);
      }
    };
    try {
      active.start();
      setListening(true);
    } catch {
      recognition.current = null;
      setListening(false);
      setVoiceError(
        "Could not start the microphone. Check browser permissions and try again.",
      );
    }
  }
  useEffect(
    () => () => {
      generation.current += 1;
      synthesis.current?.abort();
      if (source.current) {
        source.current.onended = null;
        source.current.stop();
      }
      void audio.current?.close();
      void teluguVoice.current
        ?.then((voice) => voice.dispose())
        .catch(() => {});
      const active = recognition.current;
      if (active) {
        active.onresult = null;
        active.onerror = null;
        active.onend = null;
        active.abort();
      }
      if (utterance.current) {
        utterance.current.onend = null;
        utterance.current.onerror = null;
      }
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    },
    [],
  );
  return {
    language,
    setLanguage,
    preparing,
    prepareAudio,
    listening,
    speaking,
    transcript,
    voiceError,
    readAloud,
    recognitionAvailable,
    speechAvailable,
    toggleListening,
    speak,
    stopSpeaking,
    cancel,
    setReadAloud,
  };
}

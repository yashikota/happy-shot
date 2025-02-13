import {
  Camera as CameraIcon,
  FlipHorizontal,
  Maximize,
  Minimize,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import "../styles/camera.css";

interface WindowWithAudioContext extends Window {
  webkitAudioContext?: typeof AudioContext;
}

interface CameraProps {
  onPhotoCapture: (photoBlob: Blob) => void;
}

export const Camera = ({ onPhotoCapture }: CameraProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const [currentFacingMode, setCurrentFacingMode] = useState<
    "environment" | "user"
  >("environment");
  const [amountOfCameras, setAmountOfCameras] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const AudioContextClass =
      window.AudioContext ||
      (window as WindowWithAudioContext).webkitAudioContext;
    if (AudioContextClass) {
      audioContextRef.current = new AudioContextClass();
    }

    if (
      navigator.mediaDevices?.getUserMedia &&
      navigator.mediaDevices.enumerateDevices
    ) {
      navigator.mediaDevices
        .getUserMedia({ audio: false, video: true })
        .then((stream) => {
          for (const track of stream.getTracks()) {
            track.stop();
          }
          navigator.mediaDevices.enumerateDevices().then((devices) => {
            const videoDevices = devices.filter(
              (device) => device.kind === "videoinput",
            );
            setAmountOfCameras(videoDevices.length);
            initCameraStream();
          });
        })
        .catch((error) => {
          console.error("Camera permission denied:", error);
          alert(
            "Camera permission denied. Please refresh and give permission.",
          );
        });
    } else {
      alert(
        "Camera not supported by browser, or there is no camera detected/connected",
      );
    }
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  const playClickSound = () => {
    if (!audioContextRef.current) return;
    const duration = 0.1;
    const oscillator = audioContextRef.current.createOscillator();
    const gainNode = audioContextRef.current.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioContextRef.current.destination);
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(
      2000,
      audioContextRef.current.currentTime,
    );
    oscillator.frequency.exponentialRampToValueAtTime(
      20,
      audioContextRef.current.currentTime + duration,
    );
    gainNode.gain.setValueAtTime(0.3, audioContextRef.current.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContextRef.current.currentTime + duration,
    );
    oscillator.start(audioContextRef.current.currentTime);
    oscillator.stop(audioContextRef.current.currentTime + duration);
  };

  const initCameraStream = async () => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      for (const track of stream.getTracks()) {
        track.stop();
      }
    }
    const constraints = {
      audio: false,
      video: {
        width: { ideal: 1920 },
        height: { ideal: 1080 },
        facingMode: currentFacingMode,
      },
    };
    try {
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch (error) {
      console.error("Camera stream error:", error);
    }
  };

  const takeSnapshot = () => {
    if (!videoRef.current) return;
    const canvas = document.createElement("canvas");
    const video = videoRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) return;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) {
        onPhotoCapture(blob);
        playClickSound();
      }
    }, "image/jpeg");
  };

  const toggleCamera = () => {
    setCurrentFacingMode((prev) => {
      const next = prev === "environment" ? "user" : "environment";
      setTimeout(() => initCameraStream(), 0);
      return next;
    });
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  return (
    <div id="container">
      <div id="vid_container">
        <video id="video" ref={videoRef} autoPlay playsInline>
          <track kind="captions" src="" label="captions" default />
        </video>
        <div id="video_overlay" />
      </div>
      <div id="gui_controls">
        {amountOfCameras > 1 && (
          <button
            type="button"
            id="switchCameraButton"
            onClick={toggleCamera}
            aria-pressed={currentFacingMode === "user"}
          >
            <FlipHorizontal size={36} color="white" />
          </button>
        )}
        <button type="button" id="takePhotoButton" onClick={takeSnapshot}>
          <CameraIcon size={48} color="white" />
        </button>
        <button
          type="button"
          id="toggleFullScreenButton"
          onClick={toggleFullscreen}
          aria-pressed={isFullscreen}
        >
          {isFullscreen ? (
            <Minimize size={48} color="white" />
          ) : (
            <Maximize size={48} color="white" />
          )}
        </button>
      </div>
    </div>
  );
};

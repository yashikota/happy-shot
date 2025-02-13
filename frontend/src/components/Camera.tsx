import { Camera, Compass, Grid, Image, RefreshCw, Timer } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ulid } from "ulid";
import "../styles/camera.css";

interface WindowWithAudioContext extends Window {
  webkitAudioContext?: typeof AudioContext;
}

interface CameraProps {
  onPhotoCapture: (photoBlob: Blob) => void;
  lastPhotoUrl?: string;
}

interface VideoDevice {
  deviceId: string;
  label: string;
}

export const CameraComponent = ({
  onPhotoCapture,
  lastPhotoUrl,
}: CameraProps) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const navigate = useNavigate();
  const [currentFacingMode, setCurrentFacingMode] = useState<
    "environment" | "user"
  >("environment");
  const [amountOfCameras, setAmountOfCameras] = useState(0);
  const [showGrid, setShowGrid] = useState(false);
  const [showLevel, setShowLevel] = useState(false);
  const [timerDuration, setTimerDuration] = useState(0);
  const [isTimerRunning, setIsTimerRunning] = useState(false);
  const [timerCount, setTimerCount] = useState(0);
  const [deviceOrientation, setDeviceOrientation] = useState({
    beta: 0,
    gamma: 0,
  });
  const [recordDuration, setRecordDuration] = useState(3);
  const [videoDevices, setVideoDevices] = useState<VideoDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const isDev = import.meta.env.DEV;

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
            const vDevices = devices
              .filter((device) => device.kind === "videoinput")
              .map((device) => ({
                deviceId: device.deviceId,
                label: device.label || `Camera ${device.deviceId.slice(0, 4)}`,
              }));
            setVideoDevices(vDevices);
            setAmountOfCameras(vDevices.length);
            if (vDevices.length > 0) {
              setSelectedDeviceId(vDevices[0].deviceId);
              initCameraStream(vDevices[0].deviceId);
            }
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

    if (window.DeviceOrientationEvent) {
      window.addEventListener("deviceorientation", handleOrientation);
    }

    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      window.removeEventListener("deviceorientation", handleOrientation);
    };
  }, []);

  const handleOrientation = (event: DeviceOrientationEvent) => {
    setDeviceOrientation({
      beta: event.beta || 0,
      gamma: event.gamma || 0,
    });
  };

  const initCameraStream = async (deviceId?: string) => {
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      for (const track of stream.getTracks()) {
        track.stop();
      }
    }

    const constraints = {
      audio: false,
      video:
        isDev && deviceId
          ? { deviceId: { exact: deviceId } }
          : {
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
      }
    }, "image/jpeg");
  };

  const startTimer = () => {
    if (timerDuration > 0 && !isTimerRunning) {
      setIsTimerRunning(true);
      setTimerCount(timerDuration);
      const interval = setInterval(() => {
        setTimerCount((prev) => {
          if (prev <= 1) {
            clearInterval(interval);
            setIsTimerRunning(false);
            takeSnapshot();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      takeSnapshot();
    }
  };

  const toggleCamera = () => {
    setCurrentFacingMode((prev) => {
      const next = prev === "environment" ? "user" : "environment";
      setTimeout(() => initCameraStream(), 0);
      return next;
    });
  };

  const handleDeviceChange = (deviceId: string) => {
    setSelectedDeviceId(deviceId);
    initCameraStream(deviceId);
  };

  return (
    <div id="container">
      <div id="vid_container">
        <video id="video" ref={videoRef} autoPlay playsInline>
          <track kind="captions" src="" label="captions" default />
        </video>
        {showGrid && (
          <div className="grid-overlay">
            <div
              className="grid-line grid-line-vertical"
              style={{ left: "33.33%" }}
            />
            <div
              className="grid-line grid-line-vertical"
              style={{ left: "66.66%" }}
            />
            <div
              className="grid-line grid-line-horizontal"
              style={{ top: "33.33%" }}
            />
            <div
              className="grid-line grid-line-horizontal"
              style={{ top: "66.66%" }}
            />
          </div>
        )}
        {showLevel && (
          <div className="level-indicator">
            <div
              className="level-bubble"
              style={{
                left: `${Math.max(0, Math.min(100, 50 + deviceOrientation.gamma))}%`,
              }}
            />
          </div>
        )}
        {isTimerRunning && <div className="timer-display">{timerCount}</div>}
      </div>

      <div className="camera-settings">
        {isDev && videoDevices.length > 1 && (
          <select
            className="camera-select"
            value={selectedDeviceId}
            onChange={(e) => handleDeviceChange(e.target.value)}
          >
            {videoDevices.map((device) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label}
              </option>
            ))}
          </select>
        )}
        <div className="settings-buttons-row">
          <button
            type="button"
            className="settings-button"
            onClick={() => setTimerDuration((prev) => (prev + 3) % 12)}
          >
            <Timer size={20} />
            {timerDuration > 0 ? `${timerDuration}s` : "Off"}
          </button>
          <button
            type="button"
            className="settings-button"
            onClick={() => setShowGrid(!showGrid)}
          >
            <Grid size={20} />
            {showGrid ? "On" : "Off"}
          </button>
          <button
            type="button"
            className="settings-button"
            onClick={() => setShowLevel(!showLevel)}
          >
            <Compass size={20} />
            {showLevel ? "On" : "Off"}
          </button>
        </div>
      </div>

      <div id="gui_controls">
        <button
          type="button"
          id="switchCameraButton"
          onClick={toggleCamera}
          aria-pressed={currentFacingMode === "user"}
        >
          <RefreshCw size={32} color="white" />
        </button>
        <button type="button" id="takePhotoButton" onClick={startTimer}>
          <Camera size={40} color="white" />
        </button>
        <button
          type="button"
          id="galleryButton"
          onClick={() => navigate(`/${ulid()}`)}
        >
          {lastPhotoUrl ? (
            <img src={lastPhotoUrl} alt="Last capture" />
          ) : (
            <Image size={32} color="white" />
          )}
        </button>
      </div>
    </div>
  );
};

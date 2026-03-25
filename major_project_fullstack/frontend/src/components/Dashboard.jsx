import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import {
  fetchJobOutputUrl,
  fetchJobs,
  fetchLiveAlerts,
  fetchLiveStatus,
  fetchProfile,
  fetchServices,
  fetchSummary,
  fetchVideos,
  runAnalysis,
  uploadVideo
} from "../api";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "▦" },
  { id: "upload", label: "Upload Video", icon: "⤴" },
  { id: "live", label: "Live Monitoring", icon: "◉" },
  { id: "jobs", label: "Analysis Jobs", icon: "☰" },
  { id: "results", label: "Results Viewer", icon: "▣" },
  { id: "analytics", label: "Analytics", icon: "◒" },
  { id: "profile", label: "Profile", icon: "◎" }
];

const TITLES = {
  dashboard: "Operations Dashboard",
  upload: "Upload And Run Analysis",
  live: "Live Monitoring Center",
  jobs: "Job Tracking Console",
  results: "Results Viewer",
  analytics: "System Analytics",
  profile: "User Profile"
};

const VALIDATION_ROWS = [
  {
    service: "ANPR",
    dataset: "Car Number Plate Detection (YOLOv5 val split)",
    accuracy: "98.28% (mAP@0.5)",
    precision: "98.95%",
    recall: "97.76%"
  },
  {
    service: "Mask Detection",
    dataset: "Face Mask Dataset (Kaggle)",
    accuracy: "Pending benchmark",
    precision: "Pending benchmark",
    recall: "Pending benchmark"
  },
  {
    service: "Crowd Anomaly",
    dataset: "UCSD Ped2 / Avenue style benchmark",
    accuracy: "Pending formal benchmark",
    precision: "Pending formal benchmark",
    recall: "Pending formal benchmark"
  },
  {
    service: "Crowd Gathering",
    dataset: "Custom CCTV clips",
    accuracy: "Pending formal benchmark",
    precision: "Pending formal benchmark",
    recall: "Pending formal benchmark"
  }
];

function Dashboard({ token, profile, onLogout }) {
  const [summary, setSummary] = useState(null);
  const [services, setServices] = useState([]);
  const [videos, setVideos] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [activePage, setActivePage] = useState("dashboard");
  const [profileInfo, setProfileInfo] = useState(profile);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedVideoId, setSelectedVideoId] = useState("");
  const [selectedService, setSelectedService] = useState("ANPR");
  const [uploadProgress, setUploadProgress] = useState(0);

  const [resultJobId, setResultJobId] = useState("");
  const [resultVideoUrl, setResultVideoUrl] = useState("");
  const [resultLoading, setResultLoading] = useState(false);

  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState(null);
  const [isTransitionPending, startTransition] = useTransition();
  const [isUploading, setIsUploading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const [liveService, setLiveService] = useState("ANPR");
  const [liveInputMode, setLiveInputMode] = useState("camera");
  const [liveFileName, setLiveFileName] = useState("");
  const [liveCameraOn, setLiveCameraOn] = useState(false);
  const [liveSocketConnected, setLiveSocketConnected] = useState(false);
  const [liveStreaming, setLiveStreaming] = useState(false);
  const [liveRecording, setLiveRecording] = useState(false);
  const [liveRecordUrl, setLiveRecordUrl] = useState("");
  const [liveFramesSent, setLiveFramesSent] = useState(0);
  const [liveFramesDropped, setLiveFramesDropped] = useState(0);
  const [liveQueueDepth, setLiveQueueDepth] = useState(0);
  const [liveStats, setLiveStats] = useState(null);
  const [liveEvents, setLiveEvents] = useState([]);
  const [liveStatusData, setLiveStatusData] = useState(null);
  const [liveAlerts, setLiveAlerts] = useState([]);

  const resultUrlRef = useRef("");
  const liveRecordUrlRef = useRef("");
  const liveVideoRef = useRef(null);
  const liveCanvasRef = useRef(null);
  const liveSocketRef = useRef(null);
  const liveStreamRef = useRef(null);
  const liveFrameTimerRef = useRef(null);
  const liveRecorderRef = useRef(null);
  const liveRecorderChunksRef = useRef([]);
  const liveStreamingRef = useRef(false);
  const liveFileUrlRef = useRef("");
  const liveAlertCooldownRef = useRef(0);

  const formatDate = (value) => {
    if (!value) {
      return "-";
    }
    return new Date(value).toLocaleString();
  };

  const formatSize = (bytes) => {
    if (!bytes) {
      return "0 MB";
    }
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  };

  const formatDurationSeconds = (seconds) => {
    if (!Number.isFinite(seconds) || seconds <= 0) {
      return "-";
    }
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainder = Math.round(seconds % 60);
    return `${minutes}m ${remainder}s`;
  };

  const formatElapsed = (startedAt, completedAt) => {
    if (!startedAt) {
      return "-";
    }
    const start = new Date(startedAt).getTime();
    const end = completedAt ? new Date(completedAt).getTime() : Date.now();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) {
      return "-";
    }
    const totalSeconds = Math.round((end - start) / 1000);
    if (totalSeconds < 60) {
      return `${totalSeconds}s`;
    }
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    if (minutes < 60) {
      return `${minutes}m ${seconds}s`;
    }
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  const toMetricLabel = (key) =>
    key
      .replace(/([A-Z])/g, " $1")
      .replace(/_/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .replace(/^./, (char) => char.toUpperCase());

  const formatMetricValue = (value) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    if (typeof value === "number") {
      if (!Number.isFinite(value)) {
        return "-";
      }
      if (Number.isInteger(value)) {
        return `${value}`;
      }
      return value.toFixed(2);
    }
    if (typeof value === "boolean") {
      return value ? "Yes" : "No";
    }
    return String(value);
  };

  const truncateText = (value, max = 140) => {
    const text = String(value ?? "");
    if (text.length <= max) {
      return text;
    }
    return `${text.slice(0, max - 1)}…`;
  };

  const statusClass = (status) => {
    if (status === "COMPLETED") return "status-completed";
    if (status === "FAILED") return "status-failed";
    if (status === "RUNNING") return "status-running";
    return "status-queued";
  };

  const appendLiveEvent = (level, message) => {
    const line = {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      level,
      message,
      at: new Date().toLocaleTimeString()
    };
    setLiveEvents((prev) => [line, ...prev].slice(0, 8));
  };

  const maybeBrowserNotify = (title, body) => {
    if (typeof window === "undefined" || !("Notification" in window)) {
      return;
    }
    if (Notification.permission === "granted") {
      try {
        new Notification(title, { body });
      } catch {
        // Browser notification failures are non-blocking.
      }
    }
  };

  const handleLiveAlertNotification = (payload) => {
    const now = Date.now();
    if (now - liveAlertCooldownRef.current < 7000) {
      return;
    }
    liveAlertCooldownRef.current = now;

    const service = payload?.serviceType || liveService;
    const message = payload?.error || payload?.message || "Live alert detected";
    const severity = payload?.status === "FAILED" ? "error" : "warning";
    appendLiveEvent(severity, `[${service}] ${message}`);
    maybeBrowserNotify("IntelMon Live Alert", `${service}: ${message}`);
    loadLiveStatus(true);
  };

  const loadDashboardData = async (showErrors = true) => {
    try {
      const [summaryRes, servicesRes, videosRes, jobsRes, profileRes] = await Promise.all([
        fetchSummary(token),
        fetchServices(token),
        fetchVideos(token),
        fetchJobs(token),
        fetchProfile(token)
      ]);

      startTransition(() => {
        setSummary(summaryRes);
        setServices(servicesRes);
        setVideos(videosRes);
        setJobs(jobsRes);
        setProfileInfo((prev) => ({
          ...prev,
          fullName: profileRes.fullName || prev.fullName,
          email: profileRes.email || prev.email
        }));
        setSelectedVideoId((current) => {
          if (videosRes.length === 0) {
            return "";
          }
          if (current && videosRes.some((video) => String(video.id) === current)) {
            return current;
          }
          return String(videosRes[0].id);
        });
      });

      setLastRefresh(new Date().toISOString());
      if (showErrors) {
        setError("");
      }
    } catch (err) {
      if (showErrors) {
        setError(err.message);
      }
    }
  };

  const loadLiveStatus = async (silent = true) => {
    try {
      const [status, alerts] = await Promise.all([
        fetchLiveStatus(token),
        fetchLiveAlerts(token, 30)
      ]);
      setLiveStatusData(status);
      setLiveAlerts(Array.isArray(alerts) ? alerts : []);
    } catch (err) {
      if (!silent) {
        setError(err.message);
      }
    }
  };

  useEffect(() => {
    loadDashboardData(true);
    const interval = setInterval(() => {
      loadDashboardData(false);
    }, 8000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activePage !== "live") {
      return undefined;
    }
    loadLiveStatus(true);
    const interval = setInterval(() => loadLiveStatus(true), 6000);
    return () => clearInterval(interval);
  }, [activePage]);

  useEffect(() => {
    if (resultUrlRef.current) {
      URL.revokeObjectURL(resultUrlRef.current);
      resultUrlRef.current = "";
    }
    setResultVideoUrl("");

    if (!resultJobId) {
      return;
    }

    let cancelled = false;
    const loadResultVideo = async () => {
      try {
        setResultLoading(true);
        const objectUrl = await fetchJobOutputUrl(token, resultJobId);
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        resultUrlRef.current = objectUrl;
        setResultVideoUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setResultLoading(false);
        }
      }
    };

    loadResultVideo();
    return () => {
      cancelled = true;
    };
  }, [resultJobId, token]);

  const disconnectLiveSocket = () => {
    if (liveSocketRef.current) {
      try {
        liveSocketRef.current.close();
      } catch {
        // Ignore close race conditions.
      }
      liveSocketRef.current = null;
    }
    setLiveSocketConnected(false);
  };

  const stopLiveAnalysis = () => {
    if (liveFrameTimerRef.current) {
      clearInterval(liveFrameTimerRef.current);
      liveFrameTimerRef.current = null;
    }
    liveStreamingRef.current = false;
    setLiveStreaming(false);
  };

  const closeLiveCamera = () => {
    stopLiveAnalysis();
    if (liveRecorderRef.current && liveRecorderRef.current.state !== "inactive") {
      liveRecorderRef.current.stop();
    }
    if (liveStreamRef.current) {
      liveStreamRef.current.getTracks().forEach((track) => track.stop());
      liveStreamRef.current = null;
    }
    if (liveVideoRef.current) {
      liveVideoRef.current.pause();
      liveVideoRef.current.srcObject = null;
      liveVideoRef.current.removeAttribute("src");
      liveVideoRef.current.load();
    }
    if (liveFileUrlRef.current) {
      URL.revokeObjectURL(liveFileUrlRef.current);
      liveFileUrlRef.current = "";
    }
    setLiveFileName("");
    setLiveCameraOn(false);
  };

  useEffect(() => {
    return () => {
      if (resultUrlRef.current) {
        URL.revokeObjectURL(resultUrlRef.current);
      }
      if (liveRecordUrlRef.current) {
        URL.revokeObjectURL(liveRecordUrlRef.current);
      }
      stopLiveAnalysis();
      disconnectLiveSocket();
      closeLiveCamera();
    };
  }, []);

  const buildWsUrl = () => {
    const configured = import.meta.env.VITE_WS_URL || "ws://localhost:8080/ws/live";
    if (configured.startsWith("http://")) {
      return configured.replace("http://", "ws://");
    }
    if (configured.startsWith("https://")) {
      return configured.replace("https://", "wss://");
    }
    return configured;
  };

  const connectLiveSocket = async () => {
    if (liveSocketRef.current && liveSocketRef.current.readyState === WebSocket.OPEN) {
      return true;
    }

    if (liveSocketRef.current && liveSocketRef.current.readyState === WebSocket.CONNECTING) {
      return false;
    }

    return new Promise((resolve) => {
      const ws = new WebSocket(buildWsUrl());
      liveSocketRef.current = ws;

      ws.onopen = () => {
        setLiveSocketConnected(true);
        appendLiveEvent("info", "Live WebSocket connected.");
        resolve(true);
      };

      ws.onclose = () => {
        setLiveSocketConnected(false);
        stopLiveAnalysis();
        appendLiveEvent("warning", "Live WebSocket disconnected.");
      };

      ws.onerror = () => {
        setLiveSocketConnected(false);
        appendLiveEvent("error", "Live WebSocket connection error.");
        resolve(false);
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "result") {
            setLiveStats(payload);
            if (Number.isFinite(payload.queueDepth)) {
              setLiveQueueDepth(payload.queueDepth);
            }
            const hasAlert =
              Boolean(payload.alert) ||
              Number(payload.noMaskDetections || 0) > 0 ||
              String(payload.status || "").toUpperCase() === "FAILED";
            if (hasAlert) {
              handleLiveAlertNotification(payload);
            }
          } else if (payload.type === "queued") {
            // Frame accepted by backend queue.
          } else if (payload.type === "dropped") {
            setLiveFramesDropped((prev) => prev + 1);
          } else if (payload.type === "system") {
            appendLiveEvent(payload.level || "info", payload.message || "Live system event");
            if ((payload.level || "").toLowerCase() === "error") {
              maybeBrowserNotify("IntelMon Live Error", payload.message || "Live system error");
            }
          }
        } catch {
          appendLiveEvent("warning", "Received malformed live payload.");
        }
      };
    });
  };

  const openLiveCamera = async () => {
    if (liveStreamRef.current) {
      setLiveCameraOn(true);
      return true;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser does not support webcam access.");
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 960 },
          height: { ideal: 540 }
        },
        audio: false
      });
      liveStreamRef.current = stream;

      if (liveVideoRef.current) {
        liveVideoRef.current.srcObject = stream;
        await liveVideoRef.current.play().catch(() => {});
      }
      setLiveCameraOn(true);
      appendLiveEvent("info", "Webcam connected.");
      return true;
    } catch (err) {
      setError(err.message || "Unable to access webcam.");
      return false;
    }
  };

  const openLiveVideoFile = async (file) => {
    if (!file) {
      return false;
    }
    stopLiveAnalysis();

    if (liveStreamRef.current) {
      liveStreamRef.current.getTracks().forEach((track) => track.stop());
      liveStreamRef.current = null;
    }
    if (liveVideoRef.current) {
      liveVideoRef.current.srcObject = null;
    }
    if (liveFileUrlRef.current) {
      URL.revokeObjectURL(liveFileUrlRef.current);
      liveFileUrlRef.current = "";
    }

    const url = URL.createObjectURL(file);
    liveFileUrlRef.current = url;
    setLiveFileName(file.name);

    try {
      const video = liveVideoRef.current;
      if (!video) {
        throw new Error("Video element unavailable.");
      }
      video.src = url;
      video.loop = true;
      video.muted = true;
      await video.play().catch(() => {});
      setLiveCameraOn(true);
      appendLiveEvent("info", `Live file loaded: ${file.name}`);
      return true;
    } catch (err) {
      setError(err.message || "Unable to load selected video file.");
      return false;
    }
  };

  const ensureLiveSourceReady = async () => {
    if (liveInputMode === "file") {
      const video = liveVideoRef.current;
      if (!video) {
        setError("Live video preview is unavailable.");
        return false;
      }
      if (!video.src && !video.srcObject) {
        setError("Choose a video file for live monitoring.");
        return false;
      }
      await video.play().catch(() => {});
      setLiveCameraOn(true);
      return true;
    }
    return openLiveCamera();
  };

  const sendLiveFrame = () => {
    const ws = liveSocketRef.current;
    const video = liveVideoRef.current;
    const canvas = liveCanvasRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN || !video || !canvas) {
      setLiveFramesDropped((prev) => prev + 1);
      return;
    }

    if (video.videoWidth === 0 || video.videoHeight === 0) {
      return;
    }

    const targetWidth = 512;
    const targetHeight = Math.round((video.videoHeight / video.videoWidth) * targetWidth);
    canvas.width = targetWidth;
    canvas.height = targetHeight;

    const context = canvas.getContext("2d");
    if (!context) {
      setLiveFramesDropped((prev) => prev + 1);
      return;
    }

    context.drawImage(video, 0, 0, targetWidth, targetHeight);
    const frameData = canvas.toDataURL("image/jpeg", 0.58);

    try {
      ws.send(
        JSON.stringify({
          type: "frame",
          serviceType: liveService,
          frameData,
          clientTs: Date.now()
        })
      );
      setLiveFramesSent((prev) => prev + 1);
    } catch {
      setLiveFramesDropped((prev) => prev + 1);
    }
  };

  const startLiveAnalysis = async () => {
    setError("");
    const sourceReady = await ensureLiveSourceReady();
    if (!sourceReady) {
      return;
    }

    if (typeof window !== "undefined" && "Notification" in window && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }

    const socketReady = await connectLiveSocket();
    if (!socketReady) {
      setError("Unable to connect to live backend stream.");
      return;
    }

    if (liveFrameTimerRef.current) {
      clearInterval(liveFrameTimerRef.current);
    }

    liveFrameTimerRef.current = setInterval(sendLiveFrame, 700);
    liveStreamingRef.current = true;
    setLiveStreaming(true);
    setLiveFramesSent(0);
    setLiveFramesDropped(0);
    appendLiveEvent("info", `Live analysis started for ${liveService}.`);
  };

  const startLiveRecording = async () => {
    const cameraReady = await openLiveCamera();
    if (!cameraReady || !liveStreamRef.current) {
      return;
    }

    if (liveRecorderRef.current && liveRecorderRef.current.state !== "inactive") {
      return;
    }

    const supportedType =
      MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
        ? "video/webm;codecs=vp9"
        : "video/webm;codecs=vp8";

    try {
      liveRecorderChunksRef.current = [];
      const recorder = new MediaRecorder(liveStreamRef.current, { mimeType: supportedType });
      liveRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          liveRecorderChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(liveRecorderChunksRef.current, { type: "video/webm" });
        if (liveRecordUrlRef.current) {
          URL.revokeObjectURL(liveRecordUrlRef.current);
        }
        const url = URL.createObjectURL(blob);
        liveRecordUrlRef.current = url;
        setLiveRecordUrl(url);
        setLiveRecording(false);
        appendLiveEvent("info", "Recording saved locally.");
      };

      recorder.start(800);
      setLiveRecording(true);
      appendLiveEvent("info", "Live recording started.");
    } catch (err) {
      setError(err.message || "Unable to start recording.");
    }
  };

  const stopLiveRecording = () => {
    const recorder = liveRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  };

  const onUpload = async () => {
    if (!selectedFile) {
      setError("Please choose a video file first.");
      return;
    }

    setIsUploading(true);
    setError("");
    setFeedback("");

    const progressInterval = setInterval(() => {
      setUploadProgress((previous) => (previous < 90 ? previous + 10 : previous));
    }, 200);

    try {
      setUploadProgress(5);
      const uploaded = await uploadVideo(token, selectedFile);
      setUploadProgress(100);
      setFeedback(`Uploaded ${uploaded.originalFilename}`);
      setSelectedFile(null);
      await loadDashboardData(false);
      setSelectedVideoId(String(uploaded.id));
    } catch (err) {
      setError(err.message);
    } finally {
      clearInterval(progressInterval);
      setTimeout(() => setUploadProgress(0), 500);
      setIsUploading(false);
    }
  };

  const onRunAnalysis = async () => {
    if (!selectedVideoId || !selectedService) {
      setError("Select both video and service before running analysis.");
      return;
    }

    setIsRunning(true);
    setError("");
    setFeedback("");
    try {
      const job = await runAnalysis(token, {
        videoId: Number(selectedVideoId),
        serviceType: selectedService
      });
      setFeedback(`Job #${job.id} submitted for ${job.serviceType}`);
      await loadDashboardData(false);
      setActivePage("jobs");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const analytics = useMemo(() => {
    const queued = jobs.filter((job) => job.status === "QUEUED").length;
    const running = jobs.filter((job) => job.status === "RUNNING").length;
    const completed = jobs.filter((job) => job.status === "COMPLETED").length;
    const failed = jobs.filter((job) => job.status === "FAILED").length;
    const finished = completed + failed;
    const successRate = finished > 0 ? (completed / finished) * 100 : 100;

    const serviceUsage = jobs.reduce((map, job) => {
      map[job.serviceType] = (map[job.serviceType] || 0) + 1;
      return map;
    }, {});

    const trendMap = jobs.reduce((map, job) => {
      const key = new Date(job.createdAt).toLocaleDateString();
      map[key] = (map[key] || 0) + 1;
      return map;
    }, {});

    const trends = Object.entries(trendMap)
      .map(([date, count]) => ({ date, count }))
      .slice(-7);

    const completedJobs = jobs.filter((job) => job.status === "COMPLETED");

    return {
      queued,
      running,
      completed,
      failed,
      finished,
      successRate,
      serviceUsage,
      trends,
      completedJobs
    };
  }, [jobs]);

  const selectedResultJob = useMemo(
    () => jobs.find((job) => String(job.id) === String(resultJobId)),
    [jobs, resultJobId]
  );

  const parsedResultPayload = useMemo(() => {
    if (!selectedResultJob?.resultPayload) {
      return null;
    }
    try {
      return JSON.parse(selectedResultJob.resultPayload);
    } catch {
      return null;
    }
  }, [selectedResultJob]);

  const resultHighlights = useMemo(() => {
    if (!parsedResultPayload) {
      return [];
    }

    const service = selectedResultJob?.serviceType;
    const highlights = [];
    const addMetric = (label, value) => {
      if (value === null || value === undefined || value === "") {
        return;
      }
      highlights.push({ label, value: formatMetricValue(value) });
    };

    if (service === "CROWD_ANOMALY") {
      addMetric("Frames Processed", parsedResultPayload.framesProcessed);
      addMetric("Anomaly Frames", parsedResultPayload.anomalyFrames);
      addMetric("Anomaly Ratio", `${formatMetricValue(parsedResultPayload.anomalyRatioPct)}%`);
      addMetric("Peak Anomaly Confidence", `${formatMetricValue(parsedResultPayload.maxAnomalyConfidencePct)}%`);
      addMetric("Average Anomaly Confidence", `${formatMetricValue(parsedResultPayload.avgAnomalyConfidencePct)}%`);
      addMetric("Average Normal Confidence", `${formatMetricValue(parsedResultPayload.avgNormalConfidencePct)}%`);
      return highlights;
    }

    if (service === "ANPR") {
      addMetric("Detection Mode", parsedResultPayload.mode);
      addMetric("Total Detections", parsedResultPayload.totalDetections ?? parsedResultPayload.detections);
      addMetric("Frames Processed", parsedResultPayload.processedFrames ?? parsedResultPayload.frames);
      addMetric("Video Codec", parsedResultPayload.videoCodec);
      addMetric("Warning", parsedResultPayload.warning ? truncateText(parsedResultPayload.warning) : null);
      return highlights;
    }

    Object.entries(parsedResultPayload)
      .filter(([, value]) => value !== null && value !== undefined && value !== "")
      .slice(0, 8)
      .forEach(([key, value]) => addMetric(toMetricLabel(key), value));

    return highlights;
  }, [parsedResultPayload, selectedResultJob]);

  const renderDashboardPage = () => (
    <section className="page-grid">
      <div className="summary-grid">
        <article>
          <p>Total Videos</p>
          <strong>{summary?.totalVideos ?? videos.length}</strong>
          <span>stored assets</span>
        </article>
        <article>
          <p>Total Jobs</p>
          <strong>{summary?.totalJobs ?? jobs.length}</strong>
          <span>analysis requests</span>
        </article>
        <article>
          <p>Running</p>
          <strong>{summary?.runningJobs ?? analytics.running}</strong>
          <span>active pipelines</span>
        </article>
        <article>
          <p>Completed</p>
          <strong>{summary?.completedJobs ?? analytics.completed}</strong>
          <span>successful outputs</span>
        </article>
        <article>
          <p>Failed</p>
          <strong>{summary?.failedJobs ?? analytics.failed}</strong>
          <span>requires attention</span>
        </article>
      </div>

      <article className="panel panel-strong">
        <h3>Live System Status</h3>
        <div className="health-row">
          <span>Success Rate</span>
          <strong>{analytics.successRate.toFixed(1)}%</strong>
        </div>
        <div className="meter">
          <span style={{ width: `${Math.min(100, analytics.successRate)}%` }} />
        </div>
        <div className="health-grid">
          <p>Queued: {analytics.queued}</p>
          <p>Running: {analytics.running}</p>
          <p>Finished: {analytics.finished}</p>
        </div>
      </article>

      <article className="panel panel-strong">
        <h3>Recent Jobs</h3>
        <div className="mini-table">
          {jobs.slice(0, 6).map((job) => (
            <div key={job.id} className="mini-row">
              <span>#{job.id}</span>
              <span>{job.serviceType}</span>
              <span className={`status-pill ${statusClass(job.status)}`}>{job.status}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );

  const renderUploadPage = () => (
    <section className="page-grid two-col">
      <article className="panel panel-strong">
        <h3>Upload Video</h3>
        <input
          type="file"
          accept="video/*"
          onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
        />
        <p className="hint-text">Supports MP4, MOV, AVI, MKV, M4V, WEBM.</p>
        <p className="mono-text">{selectedFile ? selectedFile.name : "No file selected"}</p>
        <button onClick={onUpload} disabled={isUploading}>
          {isUploading ? "Uploading..." : "Upload Video"}
        </button>
        <div className="upload-progress">
          <div style={{ width: `${uploadProgress}%` }} />
        </div>
      </article>

      <article className="panel panel-strong">
        <h3>Run Analysis</h3>
        <label>
          Service
          <select value={selectedService} onChange={(event) => setSelectedService(event.target.value)}>
            {services.map((service) => (
              <option key={service.code} value={service.code}>
                {service.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Video
          <select value={selectedVideoId} onChange={(event) => setSelectedVideoId(event.target.value)}>
            <option value="">Select video</option>
            {videos.map((video) => (
              <option key={video.id} value={String(video.id)}>
                {video.originalFilename}
              </option>
            ))}
          </select>
        </label>
        <button onClick={onRunAnalysis} disabled={isRunning}>
          {isRunning ? "Submitting..." : "Run Selected Service"}
        </button>
      </article>

      <article className="panel full-width">
        <h3>Uploaded Videos</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Duration</th>
                <th>Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((video) => (
                <tr key={video.id}>
                  <td>{video.originalFilename}</td>
                  <td>{formatSize(video.sizeBytes)}</td>
                  <td>{formatDurationSeconds(video.durationSeconds)}</td>
                  <td>{formatDate(video.uploadedAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );

  const renderLivePage = () => {
    const frameWidth = Number(liveStats?.frameWidth) > 0 ? Number(liveStats?.frameWidth) : 640;
    const frameHeight = Number(liveStats?.frameHeight) > 0 ? Number(liveStats?.frameHeight) : 360;
    const liveBoxes = Array.isArray(liveStats?.boxes) ? liveStats.boxes : [];
    const liveHasAlert =
      Boolean(liveStats?.alert) ||
      Number(liveStats?.noMaskDetections || 0) > 0 ||
      String(liveStats?.status || "").toUpperCase() === "FAILED";
    const liveAlertText =
      liveStats?.error ||
      liveStats?.message ||
      (liveService === "MASK_DETECTION" ? "No-mask alert detected" : "Live alert detected");

    return (
      <section className="page-grid two-col">
        <article className="panel panel-strong">
          <h3>Webcam + Live Overlay</h3>
          <div className={`live-preview-wrap ${liveHasAlert ? "alert" : ""}`}>
            <video ref={liveVideoRef} className="live-preview" autoPlay muted playsInline />
            <canvas ref={liveCanvasRef} className="live-canvas" />
            <div className="live-box-layer">
              {liveBoxes.map((box, index) => {
                const bw = Number(box.w || 0);
                const bh = Number(box.h || 0);
                const bx = Number(box.x || 0);
                const by = Number(box.y || 0);
                const left = Math.max(0, (bx / frameWidth) * 100);
                const top = Math.max(0, (by / frameHeight) * 100);
                const width = Math.max(0.5, (bw / frameWidth) * 100);
                const height = Math.max(0.5, (bh / frameHeight) * 100);
                const label = box.label || "";
                const confidence = Number(box.confidencePct || 0);
                const isNoMask = String(label).toUpperCase() === "NO_MASK";
                return (
                  <div
                    key={`${index}-${bx}-${by}`}
                    className={`live-box ${isNoMask ? "danger" : ""}`}
                    style={{ left: `${left}%`, top: `${top}%`, width: `${width}%`, height: `${height}%` }}
                  >
                    {label ? (
                      <span className={`live-box-label ${isNoMask ? "danger" : ""}`}>
                        {label}{confidence > 0 ? ` ${confidence.toFixed(1)}%` : ""}
                      </span>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {liveHasAlert ? <div className="live-alert-banner">ALERT: {liveAlertText}</div> : null}
            <div className="live-overlay">
              <p>Service: {liveService}</p>
              <p>Status: {liveStats?.status || (liveStreaming ? "RUNNING" : "IDLE")}</p>
              <p>Detections: {formatMetricValue(liveStats?.detections)}</p>
              <p>No Mask: {formatMetricValue(liveStats?.noMaskDetections)}</p>
              <p>Confidence: {liveStats?.confidencePct ? `${formatMetricValue(liveStats?.confidencePct)}%` : "-"}</p>
              <p>Alert: {formatMetricValue(liveStats?.alert)}</p>
            </div>
          </div>

          <div className="live-actions">
            <button onClick={openLiveCamera} disabled={liveCameraOn || liveInputMode === "file"}>Enable Camera</button>
            <button className="secondary" onClick={closeLiveCamera}>Stop Camera</button>
            <button onClick={startLiveAnalysis} disabled={liveStreaming}>Start Live Analysis</button>
            <button className="secondary" onClick={stopLiveAnalysis} disabled={!liveStreaming}>Stop Live Analysis</button>
            <button onClick={startLiveRecording} disabled={liveRecording}>Start Recording</button>
            <button className="secondary" onClick={stopLiveRecording} disabled={!liveRecording}>Stop Recording</button>
          </div>

          {liveRecordUrl ? (
            <a className="download-link" href={liveRecordUrl} download="intelmon-live-recording.webm">
              Download Last Recording
            </a>
          ) : null}
        </article>

        <article className="panel panel-strong">
          <h3>Live Stream Controls</h3>
          <label>
            Source
            <select
              value={liveInputMode}
              onChange={(event) => {
                const mode = event.target.value;
                setLiveInputMode(mode);
                stopLiveAnalysis();
                if (mode === "camera") {
                  if (liveFileUrlRef.current) {
                    URL.revokeObjectURL(liveFileUrlRef.current);
                    liveFileUrlRef.current = "";
                  }
                  setLiveFileName("");
                  if (liveVideoRef.current) {
                    liveVideoRef.current.pause();
                    liveVideoRef.current.removeAttribute("src");
                    liveVideoRef.current.load();
                  }
                }
              }}
            >
              <option value="camera">Webcam</option>
              <option value="file">Video File</option>
            </select>
          </label>
          {liveInputMode === "file" ? (
            <>
              <input
                type="file"
                accept="video/*"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) {
                    openLiveVideoFile(file);
                  }
                }}
              />
              <p className="hint-text">{liveFileName ? `Loaded: ${liveFileName}` : "Select a video file to run live mask analysis."}</p>
            </>
          ) : null}

          <label>
            Service
            <select value={liveService} onChange={(event) => setLiveService(event.target.value)}>
              <option value="ANPR">ANPR</option>
              <option value="MASK_DETECTION">Mask Detection</option>
              <option value="CROWD_GATHERING">Crowd Detection</option>
            </select>
          </label>

          <div className="health-grid live-health-grid">
            <p>Socket: {liveSocketConnected ? "Connected" : "Disconnected"}</p>
            <p>Source: {liveInputMode === "file" ? "Video File" : "Webcam"}</p>
            <p>Source Ready: {liveCameraOn ? "Active" : "Inactive"}</p>
            <p>Streaming: {liveStreaming ? "ON" : "OFF"}</p>
            <p>Recording: {liveRecording ? "ON" : "OFF"}</p>
            <p>Frames Sent: {liveFramesSent}</p>
            <p>Dropped: {liveFramesDropped}</p>
            <p>Queue Depth: {liveQueueDepth}</p>
            <p>Backend Queue: {liveStatusData?.queueMode || "-"}</p>
            <p>Redis: {liveStatusData?.redisAvailable ? "Available" : "Unavailable"}</p>
          </div>

          <p className="hint-text">
            Real-time frames stream over WebSocket (`/ws/live`) and are processed through Redis/local queue workers.
          </p>

          <button className="secondary" onClick={() => loadLiveStatus(false)}>
            Refresh Live Backend Status
          </button>
        </article>

        <article className="panel full-width">
          <h3>Live Alert History (Stored)</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Service</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Message</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {liveAlerts.map((alertRow) => (
                  <tr key={alertRow.id}>
                    <td>{formatDate(alertRow.createdAt)}</td>
                    <td>{alertRow.serviceType}</td>
                    <td>{alertRow.severity || "-"}</td>
                    <td>{alertRow.status}</td>
                    <td>{alertRow.message || "-"}</td>
                    <td>{alertRow.confidencePct ? `${Number(alertRow.confidencePct).toFixed(1)}%` : "-"}</td>
                  </tr>
                ))}
                {liveAlerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="hint-text">No alerts stored yet.</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel full-width">
          <h3>Live Events</h3>
          <div className="live-log">
            {liveEvents.length === 0 ? <p className="hint-text">No live events yet.</p> : null}
            {liveEvents.map((event) => (
              <div key={event.id} className="live-log-row">
                <span className={`live-tag ${event.level}`}>{event.level.toUpperCase()}</span>
                <span className="mono-text">{event.at}</span>
                <span>{event.message}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    );
  };

  const renderJobsPage = () => (
    <section className="page-grid">
      <article className="panel full-width">
        <h3>Analysis Jobs</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Service</th>
                <th>Status</th>
                <th>Video</th>
                <th>Duration</th>
                <th>Created</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>#{job.id}</td>
                  <td>{job.serviceType}</td>
                  <td><span className={`status-pill ${statusClass(job.status)}`}>{job.status}</span></td>
                  <td>{job.videoName}</td>
                  <td>{job.durationSeconds ? `${job.durationSeconds.toFixed(1)}s` : formatElapsed(job.startedAt, job.completedAt)}</td>
                  <td>{formatDate(job.createdAt)}</td>
                  <td className="mono-text">{job.errorMessage || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );

  const renderResultsPage = () => (
    <section className="page-grid two-col">
      <article className="panel panel-strong">
        <h3>Select Completed Job</h3>
        <label>
          Completed Jobs
          <select value={resultJobId} onChange={(event) => setResultJobId(event.target.value)}>
            <option value="">Choose job</option>
            {analytics.completedJobs.map((job) => (
              <option key={job.id} value={String(job.id)}>
                #{job.id} - {job.serviceType} - {job.videoName}
              </option>
            ))}
          </select>
        </label>

        {selectedResultJob ? (
          <div className="details-list">
            <p><strong>Service:</strong> {selectedResultJob.serviceType}</p>
            <p><strong>Status:</strong> {selectedResultJob.status}</p>
            <p><strong>Video:</strong> {selectedResultJob.videoName}</p>
            <p><strong>Duration:</strong> {formatElapsed(selectedResultJob.startedAt, selectedResultJob.completedAt)}</p>
            <p><strong>Created:</strong> {formatDate(selectedResultJob.createdAt)}</p>
          </div>
        ) : (
          <p className="hint-text">Choose a completed job to preview output and detections.</p>
        )}
      </article>

      <article className="panel panel-strong">
        <h3>Output Preview</h3>
        {resultLoading ? <p className="hint-text">Loading result video...</p> : null}
        {!resultLoading && resultVideoUrl ? (
          <>
            <video className="result-video" controls src={resultVideoUrl} />
            <a className="download-link" href={resultVideoUrl} download={`analysis-job-${resultJobId}.mp4`}>
              Download Result Video
            </a>
          </>
        ) : (
          <p className="hint-text">No output loaded.</p>
        )}
        {selectedResultJob?.resultPayload && resultHighlights.length > 0 ? (
          <div className="result-metrics">
            {resultHighlights.map((metric) => (
              <div key={metric.label} className="metric-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
        ) : null}
        {selectedResultJob?.resultPayload ? (
          <details className="payload-details">
            <summary>Technical Payload</summary>
            <pre className="payload-box">
              {parsedResultPayload
                ? JSON.stringify(parsedResultPayload, null, 2)
                : selectedResultJob.resultPayload}
            </pre>
          </details>
        ) : (
          <p className="hint-text">Structured detection payload will appear here after completion.</p>
        )}
      </article>
    </section>
  );

  const renderAnalyticsPage = () => {
    const statusBars = [
      { label: "Completed", value: analytics.completed, className: "bar-success" },
      { label: "Failed", value: analytics.failed, className: "bar-danger" },
      { label: "Running", value: analytics.running, className: "bar-warning" },
      { label: "Queued", value: analytics.queued, className: "bar-info" }
    ];

    const serviceBars = Object.entries(analytics.serviceUsage);
    const maxStatus = Math.max(1, ...statusBars.map((item) => item.value));
    const maxService = Math.max(1, ...serviceBars.map(([, count]) => count));

    return (
      <section className="page-grid two-col">
        <article className="panel panel-strong">
          <h3>Success Vs Failure</h3>
          <p className="hint-text">Success Rate: {analytics.successRate.toFixed(1)}%</p>
          <div className="chart-list">
            {statusBars.map((item) => (
              <div key={item.label} className="chart-row">
                <span>{item.label}</span>
                <div className="chart-track">
                  <div className={item.className} style={{ width: `${(item.value / maxStatus) * 100}%` }} />
                </div>
                <strong>{item.value}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel-strong">
          <h3>Service Usage</h3>
          <div className="chart-list">
            {serviceBars.length === 0 ? <p className="hint-text">No usage yet.</p> : null}
            {serviceBars.map(([service, count]) => (
              <div key={service} className="chart-row">
                <span>{service}</span>
                <div className="chart-track">
                  <div className="bar-primary" style={{ width: `${(count / maxService) * 100}%` }} />
                </div>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel full-width">
          <h3>Processing Trends (Last 7 Entries)</h3>
          <div className="trend-grid">
            {analytics.trends.length === 0 ? <p className="hint-text">No trend data available yet.</p> : null}
            {analytics.trends.map((entry) => (
              <div key={`${entry.date}-${entry.count}`} className="trend-item">
                <span>{entry.date}</span>
                <strong>{entry.count}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel full-width">
          <h3>Model Validation Table</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Dataset Used</th>
                  <th>Accuracy</th>
                  <th>Precision</th>
                  <th>Recall</th>
                </tr>
              </thead>
              <tbody>
                {VALIDATION_ROWS.map((row) => (
                  <tr key={row.service}>
                    <td>{row.service}</td>
                    <td>{row.dataset}</td>
                    <td>{row.accuracy}</td>
                    <td>{row.precision}</td>
                    <td>{row.recall}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    );
  };

  const renderProfilePage = () => (
    <section className="page-grid">
      <article className="panel panel-strong profile-card">
        <h3>User Details</h3>
        <p><strong>Name:</strong> {profileInfo.fullName}</p>
        <p><strong>Email:</strong> {profileInfo.email}</p>
        <p><strong>Role:</strong> USER</p>
        <p><strong>Session:</strong> JWT Active</p>
        <p className="mono-text"><strong>Token Preview:</strong> {token.slice(0, 18)}...</p>
      </article>
    </section>
  );

  return (
    <div className="app-shell">
      <div className="noise" />

      <aside className={`side-nav ${sidebarCollapsed ? "collapsed" : ""}`}>
        <div className="brand-block">
          <p className="chip">IntelMon</p>
          <h2>{sidebarCollapsed ? "IntelMon" : "Intelligent Visual Monitoring"}</h2>
          {!sidebarCollapsed ? <p>Unified AI Command Suite</p> : null}
        </div>

        <button className="collapse-btn" onClick={() => setSidebarCollapsed((prev) => !prev)}>
          {sidebarCollapsed ? "Expand" : "Collapse"}
        </button>

        <nav className="nav-list">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={activePage === item.id ? "nav-btn active" : "nav-btn"}
              onClick={() => setActivePage(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              {!sidebarCollapsed ? <span>{item.label}</span> : null}
            </button>
          ))}
        </nav>

        <div className="side-footer">
          <p>{profileInfo.fullName}</p>
          <p className="small-text">{profileInfo.email}</p>
          <button className="secondary" onClick={onLogout}>Logout</button>
        </div>
      </aside>

      <main className="app-main">
        <header className="page-header">
          <div>
            <h1>{TITLES[activePage]}</h1>
            <p className="subtext">Last refresh: {lastRefresh ? formatDate(lastRefresh) : "-"}</p>
          </div>
          <button onClick={() => loadDashboardData(true)}>
            {isTransitionPending ? "Refreshing..." : "Refresh Data"}
          </button>
        </header>

        {error ? <p className="error-text">{error}</p> : null}
        {feedback ? <p className="success-text">{feedback}</p> : null}

        {activePage === "dashboard" ? renderDashboardPage() : null}
        {activePage === "upload" ? renderUploadPage() : null}
        {activePage === "live" ? renderLivePage() : null}
        {activePage === "jobs" ? renderJobsPage() : null}
        {activePage === "results" ? renderResultsPage() : null}
        {activePage === "analytics" ? renderAnalyticsPage() : null}
        {activePage === "profile" ? renderProfilePage() : null}
      </main>
    </div>
  );
}

export default Dashboard;

"use client";

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AlertCircle, CheckCircle2, Upload } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

interface VideoPreview {
  file: File;
  url: string;
}

interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  error?: string;
  result?: any;
}

export default function Home() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [videoPreview, setVideoPreview] = useState<VideoPreview | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [navigateId, setNavigateId] = useState("");
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    if (
      jobId &&
      (jobStatus?.status === "pending" || jobStatus?.status === "processing")
    ) {
      intervalId = setInterval(async () => {
        try {
          const response = await fetch(
            `https://happy-shot.yashikota.com/jobs/${jobId}`,
          );
          if (!response.ok) {
            throw new Error("ステータスの取得に失敗しました");
          }
          const status: JobStatus = await response.json();
          setJobStatus(status);

          if (status.status === "completed") {
            setSuccess(true);
            setTimeout(() => {
              router.push(`/${jobId}`);
            }, 1000);
          } else if (status.status === "failed") {
            setError(status.error || "処理中にエラーが発生しました");
          }
        } catch (err) {
          setError(err instanceof Error ? err.message : "エラーが発生しました");
        }
      }, 2000); // 2秒ごとにポーリング
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, jobStatus?.status, router]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file?.type.startsWith("video/")) {
      const url = URL.createObjectURL(file);
      setVideoPreview({ file, url });
      setError(null);
    } else {
      setError("動画ファイルのみアップロード可能です");
      setVideoPreview(null);
    }
  };

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!videoPreview) {
      setError("ファイルを選択してください");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);
    setJobId(null);
    setJobStatus(null);

    const formData = new FormData();
    formData.append("file", videoPreview.file);

    try {
      const response = await fetch("https://happy-shot.yashikota.com/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("アップロードに失敗しました");
      }

      const data = await response.json();
      setJobId(data.job_id);
      setJobStatus({
        job_id: data.job_id,
        status: data.status,
        created_at: new Date().toISOString(),
        completed_at: null,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setUploading(false);
    }
  }

  const getStatusMessage = () => {
    if (!jobStatus) return null;

    switch (jobStatus.status) {
      case "pending":
        return "処理待機中...";
      case "processing":
        return "動画を処理中...";
      case "completed":
        return "処理が完了しました";
      case "failed":
        return `エラーが発生しました: ${jobStatus.error || "不明なエラー"}`;
      default:
        return null;
    }
  };

  return (
    <>
      <Header />
      <main className="pt-20 px-4">
        <Card className="w-full max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle>動画アップロード</CardTitle>
            <CardDescription>
              アップロードする動画ファイルを選択してください
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid w-full gap-4">
                <div className="grid gap-2">
                  <label htmlFor="video" className="sr-only">
                    動画を選択
                  </label>
                  <div className="relative">
                    <input
                      id="video"
                      type="file"
                      name="video"
                      accept="video/*"
                      className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      onChange={handleFileChange}
                      disabled={uploading || !!jobId}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-32 flex flex-col items-center justify-center gap-2"
                      disabled={uploading || !!jobId}
                    >
                      <Upload className="h-8 w-8" />
                      <span>
                        クリックまたは
                        <br />
                        ドラッグ＆ドロップで動画を選択
                      </span>
                    </Button>
                  </div>
                </div>
                {videoPreview && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      ファイル名: {videoPreview.file.name}
                    </p>
                    <div className="relative rounded-lg overflow-hidden bg-black aspect-video">
                      <video
                        ref={videoRef}
                        src={videoPreview?.url || ""}
                        className="w-full h-full"
                        controls
                      />
                    </div>
                  </div>
                )}
                {(uploading || jobStatus?.status === "processing") && (
                  <div className="space-y-2">
                    <Progress value={progress} className="w-full" />
                    <p className="text-sm text-center text-muted-foreground">
                      {uploading ? "アップロード中..." : getStatusMessage()}
                    </p>
                  </div>
                )}
                {error && (
                  <div className="flex items-center gap-2 text-sm text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    <span>{error}</span>
                  </div>
                )}
                {success && (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>処理が完了しました</span>
                  </div>
                )}
                {!jobId && (
                  <Button type="submit" disabled={uploading || !videoPreview}>
                    {uploading ? "アップロード中..." : "アップロード"}
                  </Button>
                )}
                {jobId && !success && !error && (
                  <div className="text-sm text-center text-muted-foreground">
                    {getStatusMessage()}
                  </div>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="w-full max-w-2xl mx-auto mt-4">
          <CardHeader>
            <CardTitle>アルバム閲覧</CardTitle>
            <CardDescription>
              アルバムを閲覧するためのIDを入力してください
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mt-2 text-center">
              <div className="flex justify-center gap-2">
                <input
                  type="text"
                  placeholder="IDを入力"
                  value={navigateId}
                  onChange={(e) => setNavigateId(e.target.value)}
                  className="border border-gray-300 rounded px-2 py-1"
                />
                <Button
                  onClick={() => {
                    if (navigateId) router.push(`/${navigateId}`);
                  }}
                >
                  移動
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </>
  );
}

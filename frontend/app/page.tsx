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
import { useRef, useState } from "react";

interface VideoPreview {
  file: File;
  url: string;
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

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const formData = new FormData();
      formData.append("video", videoPreview.file);

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round(
            (event.loaded / event.total) * 100,
          );
          setProgress(percentComplete);
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText);
          setSuccess(true);
          setTimeout(() => {
            router.push(`/${response.id}`);
          }, 1000);
          resolve(response);
        } else {
          setError("アップロードに失敗しました");
          reject(new Error("Upload failed"));
        }
        setUploading(false);
      });

      xhr.addEventListener("error", () => {
        setError("エラーが発生しました");
        setUploading(false);
        reject(new Error("Network error"));
      });

      xhr.open("POST", "/api/upload");
      xhr.send(formData);
    }).catch((err) => {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
      setUploading(false);
      setProgress(0);
    });
  }

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
                      disabled={uploading}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full h-32 flex flex-col items-center justify-center gap-2"
                      disabled={uploading}
                    >
                      <Upload className="h-8 w-8" />
                      <span>クリックまたはドラッグ＆ドロップで動画を選択</span>
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
                      >
                        {videoPreview && (
                          <track
                            default
                            kind="captions"
                            src=""
                            label="captions"
                          />
                        )}
                      </video>
                    </div>
                  </div>
                )}
                {uploading && (
                  <div className="space-y-2">
                    <Progress value={progress} className="w-full" />
                    <p className="text-sm text-center text-muted-foreground">
                      アップロード中... {progress}%
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
                    <span>アップロードが完了しました</span>
                  </div>
                )}
                <Button type="submit" disabled={uploading || !videoPreview}>
                  {uploading ? "アップロード中..." : "アップロード"}
                </Button>
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

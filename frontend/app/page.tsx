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
import { toast } from "sonner";

interface VideoPreview {
  file: File;
  url: string;
}

export default function Home() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [videoPreview, setVideoPreview] = useState<VideoPreview | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [processId, setProcessId] = useState<string | null>(null);
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

  const uploadFileWithProgress = (formData: FormData): Promise<any> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", "https://happy-shot.yashikota.com/upload", true);

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText));
        } else {
          reject(new Error("アップロードに失敗しました"));
        }
      };

      xhr.onerror = () => reject(new Error("ネットワークエラー"));
      xhr.send(formData);
    });
  };

  useEffect(() => {
    if (processId) {
      setNavigateId(processId);
      setSuccess(true);
    }
  }, [processId]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!videoPreview) {
      setError("ファイルを選択してください");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setError(null);
    setSuccess(false);
    setProcessId(null);

    const formData = new FormData();
    formData.append("file", videoPreview.file);

    try {
      const data = await uploadFileWithProgress(formData);
      setProcessId(data.process_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setUploading(false);
    }
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
                {uploading && (
                  <div className="space-y-2">
                    <Progress value={uploadProgress} className="w-full" />
                    <p className="text-sm text-center text-muted-foreground">
                      アップロード処理中...
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
                <Button
                  type={processId ? "button" : "submit"}
                  disabled={uploading || (!videoPreview && !processId)}
                  onClick={() => {
                    if (processId) {
                      router.push(`/${processId}`);
                    }
                  }}
                >
                  {uploading
                    ? "処理中..."
                    : processId
                      ? "アルバムへ"
                      : "アップロード"}
                </Button>
                {processId && (
                  <div className="mt-4 p-4 bg-gray-100 rounded-lg text-center text-lg font-semibold text-gray-700 shadow-md space-x-4">
                    <span>ID: {processId}</span>
                    <Button
                      type="button" // added to prevent re-upload
                      variant="outline"
                      onClick={() => {
                        navigator.clipboard.writeText(processId);
                        toast("コピーしました");
                      }}
                    >
                      コピー
                    </Button>
                  </div>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="w-full max-w-2xl mx-auto my-4">
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

"use client";

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AlertCircle, CheckCircle2, Download, Loader2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ImageGallery } from "react-image-grid-gallery";

const baseUrl = "https://happy-shot.yashikota.com";

interface JobStatus {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  completed_at: string | null;
  error?: string;
  result?: any;
}

export default function GalleryPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [images, setImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const fetchJobStatus = async () => {
      try {
        const response = await fetch(`${baseUrl}/jobs/${id}`);
        if (!response.ok) {
          throw new Error("ジョブの取得に失敗しました");
        }
        const status: JobStatus = await response.json();
        setJobStatus(status);

        if (status.status === "completed") {
          // 処理完了時に画像を取得
          const imagesResponse = await fetch(`${baseUrl}/images?bucket=${id}`);
          if (!imagesResponse.ok) {
            throw new Error("画像の取得に失敗しました");
          }
          const data = await imagesResponse.json();
          setImages(data.images || []);
          setLoading(false);
        } else if (status.status === "failed") {
          setError(status.error || "処理中にエラーが発生しました");
          setLoading(false);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "エラーが発生しました");
        setLoading(false);
      }
    };

    if (id) {
      fetchJobStatus();

      // 処理中は定期的にステータスを確認
      if (
        jobStatus?.status === "pending" ||
        jobStatus?.status === "processing"
      ) {
        intervalId = setInterval(fetchJobStatus, 2000);
      }
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [id, jobStatus?.status]);

  const handleDownload = async () => {
    try {
      const response = await fetch(`${baseUrl}/download?bucket=${id}`);
      if (!response.ok) {
        throw new Error("ダウンロードに失敗しました");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("ダウンロード中にエラーが発生:", error);
      setError(
        error instanceof Error
          ? error.message
          : "ダウンロード中にエラーが発生しました",
      );
    }
  };

  const getStatusMessage = () => {
    if (!jobStatus) return "ステータスを取得中...";

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
        return "不明なステータス";
    }
  };

  return (
    <>
      <Header />
      <main className="pt-20 px-4">
        <Card className="w-full max-w-2xl mx-auto mb-8">
          <CardHeader>
            <CardTitle>処理状態</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {loading ? (
                <div className="flex items-center gap-2 text-blue-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>ステータスを取得中...</span>
                </div>
              ) : error ? (
                <div className="flex items-center gap-2 text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              ) : jobStatus?.status === "completed" ? (
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>{getStatusMessage()}</span>
                </div>
              ) : (
                <div className="space-y-2">
                  <Progress
                    value={jobStatus?.status === "processing" ? 50 : 0}
                    className="w-full"
                  />
                  <p className="text-sm text-center text-muted-foreground">
                    {getStatusMessage()}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {jobStatus?.status === "completed" && images.length > 0 && (
          <>
            <ImageGallery
              imagesInfoArray={images.map((url, index) => ({
                id: String(index + 1),
                src: url,
                alt: `Image ${index + 1}`,
              }))}
              columnCount={"auto"}
              gapSize={8}
            />
            <Button
              variant="default"
              size="icon"
              className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-lg hover:shadow-xl transition-shadow bg-blue-500 text-white hover:bg-blue-700"
              onClick={handleDownload}
            >
              <Download className="w-6 h-6" />
            </Button>
          </>
        )}

        {jobStatus?.status === "completed" && images.length === 0 && (
          <div className="text-center text-gray-500 min-h-[50vh] flex flex-col items-center justify-center gap-4">
            <p>画像が見つかりません</p>
            <Button variant="default" onClick={() => router.push("/")}>
              ホームに戻る
            </Button>
          </div>
        )}
      </main>
    </>
  );
}

"use client";

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ImageGallery } from "react-image-grid-gallery";

const baseUrl =
  "https://app-122ab23f-3126-4106-9d44-988a8bd962de.ingress.apprun.sakura.ne.jp";

export default function GalleryPage() {
  const params = useParams();
  const id = params.id as string;
  const [images, setImages] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      setLoading(true);
      fetch(`${baseUrl}/images?bucket=${id}`)
        .then((res) => res.json())
        .then((data) => {
          setImages(data.images || []);
          setLoading(false);
        })
        .catch((error) => {
          console.error("Error fetching images:", error);
          setLoading(false);
        });
    }
  }, [id]);

  const handleDownload = async () => {
    try {
      const response = await fetch(`${baseUrl}/download?bucket=${id}`);
      if (!response.ok) {
        throw new Error("Download failed");
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
      console.error("Error during download:", error);
    }
  };

  return (
    <>
      <Header />
      <main className="pt-20 px-4">
        {loading ? (
          <div className="flex justify-center items-center min-h-[50vh]">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500" />
          </div>
        ) : images.length > 0 ? (
          <ImageGallery
            imagesInfoArray={images.map((url, index) => ({
              id: String(index + 1),
              src: url,
              alt: `Image ${index + 1}`,
            }))}
            columnCount={"auto"}
            gapSize={8}
          />
        ) : (
          <div className="text-center text-gray-500 min-h-[50vh] flex items-center justify-center">
            No images found
          </div>
        )}
      </main>
      <Button
        variant="default"
        size="icon"
        className="fixed bottom-6 right-6 rounded-full w-14 h-14 shadow-lg hover:shadow-xl transition-shadow bg-blue-500 text-white hover:bg-blue-700"
        onClick={handleDownload}
      >
        <Download className="w-6 h-6" />
      </Button>
    </>
  );
}

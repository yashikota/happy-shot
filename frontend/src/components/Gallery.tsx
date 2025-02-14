import { Camera, FileDown } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "../styles/gallery.css";
import { Gallery, type Image } from "react-grid-gallery";
import Lightbox from "yet-another-react-lightbox";
import "yet-another-react-lightbox/styles.css";
import { CameraComponent } from "../components/Camera";

export const GalleryComponent = () => {
  const url = "http://localhost:5000";
  const { id: bucketName } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [images, setImages] = useState<Image[]>([]);
  const [index, setIndex] = useState(-1);
  const [showCamera, setShowCamera] = useState(false);

  useEffect(() => {
    if (!bucketName) return;
    fetch(`${url}/images?bucket=${bucketName}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.images && Array.isArray(data.images)) {
          const fetchedImages: Image[] = data.images.map((url: string) => ({
            src: url,
            width: 320,
            height: 213,
          }));
          setImages(fetchedImages);
        }
      })
      .catch((err) => console.error("Error fetching images:", err));
  }, [bucketName]);

  const handleClick = (index: number, _: Image) => setIndex(index);

  const handlePhotoCapture = (photoBlob: Blob) => {
    const imageUrl = URL.createObjectURL(photoBlob);

    const img = new Image();
    img.onload = () => {
      const newImage: Image = {
        src: imageUrl,
        width: 320,
        height: Math.round((320 * img.height) / img.width),
      };
      setImages((prev) => [newImage, ...prev]);
      setShowCamera(false);
    };
    img.src = imageUrl;
  };

  const slides = images.map(({ src, width, height }) => ({
    src,
    width,
    height,
  }));

  const handleDownload = () => {
    if (!bucketName) return;
    window.location.href = `${url}/download?bucket=${bucketName}`;
  };

  if (showCamera) {
    return (
      <div style={{ height: "100vh", background: "#000" }}>
        <CameraComponent onPhotoCapture={handlePhotoCapture} />
      </div>
    );
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => navigate("/")}
        style={{
          position: "fixed",
          bottom: "20px",
          right: "20px",
          zIndex: 1000,
          background: "#007bff",
          color: "white",
          border: "none",
          padding: "12px 24px",
          borderRadius: "50px",
          cursor: "pointer",
          boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
        }}
      >
        <Camera size={32} />
      </button>

      <button
        type="button"
        onClick={handleDownload}
        style={{
          position: "fixed",
          bottom: "20px",
          left: "20px",
          zIndex: 1000,
          background: "#28a745",
          color: "white",
          border: "none",
          padding: "12px 24px",
          borderRadius: "50px",
          cursor: "pointer",
          boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
        }}
      >
        <FileDown size={32} />
      </button>

      <Gallery
        images={images}
        onClick={handleClick}
        enableImageSelection={false}
      />
      <Lightbox
        slides={slides}
        open={index >= 0}
        index={index}
        close={() => setIndex(-1)}
      />
    </div>
  );
};

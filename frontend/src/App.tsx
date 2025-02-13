import { useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { CameraComponent } from "./components/Camera";
import { GalleryComponent } from "./components/Gallery";

export default function App() {
  const [lastPhotoUrl, setLastPhotoUrl] = useState<string>();

  const handlePhotoCapture = (blob: Blob) => {
    const url = URL.createObjectURL(blob);
    setLastPhotoUrl(url);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={
            <CameraComponent
              onPhotoCapture={handlePhotoCapture}
              lastPhotoUrl={lastPhotoUrl}
            />
          }
        />
        <Route path="/:id" element={<GalleryComponent />} />
      </Routes>
    </BrowserRouter>
  );
}

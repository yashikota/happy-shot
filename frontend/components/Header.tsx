import { Button } from "./ui/button";

export function Header() {
  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: "HappyShot",
          text: "目線ピッタリ、笑顔バッチリ。",
          url: window.location.href,
        });
      } catch (error) {
        console.error("Error sharing:", error);
      }
    } else {
      alert("Web Share API is not supported in your browser");
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-blue-100 shadow-md z-50 flex items-center px-4">
      <a href="/" className="flex items-center">
        <img
          src="https://raw.githubusercontent.com/microsoft/fluentui-emoji/main/assets/Beaming%20face%20with%20smiling%20eyes/3D/beaming_face_with_smiling_eyes_3d.png"
          alt="HappyShot"
          className="w-8 h-8 mr-2"
        />
        <h1 className="text-2xl font-bold">HappyShot</h1>
      </a>

      <Button
        variant="default"
        className="ml-auto text-white bg-blue-500 hover:bg-blue-700"
        onClick={handleShare}
      >
        写真を共有する
      </Button>
    </header>
  );
}

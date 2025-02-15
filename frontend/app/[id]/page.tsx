"use client"

import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import { useParams } from "next/navigation"
import { ImageGallery } from "react-image-grid-gallery";

const imagesArray: any = [
  {
    id: "1",
    src: "https://c2.staticflickr.com/9/8817/28973449265_07e3aa5d2e_b.jpg",
  },
  {
    id: "2",
    src: "https://c2.staticflickr.com/9/8356/28897120681_3b2c0f43e0_b.jpg",
  },
  {
    id: "3",
    src: "https://c4.staticflickr.com/9/8887/28897124891_98c4fdd82b_b.jpg",
  },
  {
    id: "4",
    src: "https://c7.staticflickr.com/9/8546/28354329294_bb45ba31fa_b.jpg",
  },
  {
    id: "5",
    src: "https://c6.staticflickr.com/9/8890/28897154101_a8f55be225_b.jpg",
  },
  {
    id: "6",
    src: "https://c5.staticflickr.com/9/8768/28941110956_b05ab588c1_b.jpg",
  },
  {
    id: "7",
    src: "https://c3.staticflickr.com/9/8583/28354353794_9f2d08d8c0_b.jpg",
  },
  {
    id: "8",
    src: "https://c7.staticflickr.com/9/8569/28941134686_d57273d933_b.jpg",
  },
  {
    id: "9",
    src: "https://c6.staticflickr.com/9/8342/28897193381_800db6419e_b.jpg",
  },
  {
    id: "10",
    src: "https://c2.staticflickr.com/9/8239/28897202241_1497bec71a_b.jpg",
  },
  {
    id: "11",
    src: "https://c7.staticflickr.com/9/8785/28687743710_3580fcb5f0_b.jpg",
  },
  {
    id: "12",
    src: "https://c6.staticflickr.com/9/8520/28357073053_cafcb3da6f_b.jpg",
  },
  {
    id: "13",
    src: "https://c8.staticflickr.com/9/8104/28973555735_ae7c208970_b.jpg",
  },
  {
    id: "14",
    src: "https://c4.staticflickr.com/9/8562/28897228731_ff4447ef5f_b.jpg",
  },
  {
    id: "15",
    src: "https://c2.staticflickr.com/8/7577/28973580825_d8f541ba3f_b.jpg",
  },
  {
    id: "16",
    src: "https://c7.staticflickr.com/9/8106/28941228886_86d1450016_b.jpg",
  },
  {
    id: "17",
    src: "https://c1.staticflickr.com/9/8330/28941240416_71d2a7af8e_b.jpg",
  },
  {
    id: "18",
    src: "https://c1.staticflickr.com/9/8707/28868704912_cba5c6600e_b.jpg",
  },
  {
    id: "19",
    src: "https://c2.staticflickr.com/9/8817/28973449265_07e3aa5d2e_b.jpg",
  },
  {
    id: "20",
    src: "https://c2.staticflickr.com/9/8356/28897120681_3b2c0f43e0_b.jpg",
  },
  {
    id: "21",
    src: "https://c4.staticflickr.com/9/8887/28897124891_98c4fdd82b_b.jpg",
  },
  {
    id: "22",
    src: "https://c7.staticflickr.com/9/8546/28354329294_bb45ba31fa_b.jpg",
  },
  {
    id: "23",
    src: "https://c6.staticflickr.com/9/8890/28897154101_a8f55be225_b.jpg",
  },
  {
    id: "24",
    src: "https://c5.staticflickr.com/9/8768/28941110956_b05ab588c1_b.jpg",
  },
  {
    id: "25",
    src: "https://c3.staticflickr.com/9/8583/28354353794_9f2d08d8c0_b.jpg",
  },
  {
    id: "26",
    src: "https://c7.staticflickr.com/9/8569/28941134686_d57273d933_b.jpg",
  },
  {
    id: "27",
    src: "https://c6.staticflickr.com/9/8342/28897193381_800db6419e_b.jpg",
  },
  {
    id: "28",
    src: "https://c2.staticflickr.com/9/8239/28897202241_1497bec71a_b.jpg",
  },
  {
    id: "29",
    src: "https://c7.staticflickr.com/9/8785/28687743710_3580fcb5f0_b.jpg",
  },
  {
    id: "30",
    src: "https://c6.staticflickr.com/9/8520/28357073053_cafcb3da6f_b.jpg",
  },
];

export default function GalleryPage() {
  const params = useParams()
  const id = params.id as string

  const handleDownload = async () => {
    console.log("Bulk download initiated");
  };

  return (
    <>
      <Header />
      <main className="pt-20 px-4">
        <ImageGallery
          imagesInfoArray={imagesArray}
          columnCount={"auto"}
          gapSize={8}
        />
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

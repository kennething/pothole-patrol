import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";

const FullscreenMap = dynamic(() => import("./components/Map"), {
  ssr: false,
  loading: () => <div className="flex h-screen w-screen items-center justify-center">Loading map...</div>
});

export default function Home() {
  return (
    <main>
      <FullscreenMap />
    </main>
  );
}

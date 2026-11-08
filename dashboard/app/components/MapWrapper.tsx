"use client";

import dynamic from "next/dynamic";

const Map = dynamic(() => import("./Map"), {
  ssr: false,
  loading: () => <div className="flex h-screen w-screen items-center justify-center">Loading map...</div>
});

export default function MapWrapper() {
  return <Map />;
}

"use client";

import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet";
import { fetchEndpoint } from "../utils/fetch";
import { MiniPothole } from "../utils/types";
import { useEffect, useState } from "react";
import L from "leaflet";

import PopupContent from "./PopupContent";
import MapFlyer from "./MapFlyer";

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png"
});

function MapEventHandler({ onBoundsChange }: { onBoundsChange: (topLeft: L.LatLng, bottomRight: L.LatLng) => void }) {
  const map = useMapEvents({
    moveend: () => {
      const bounds = map.getBounds();
      const topLeft = bounds.getNorthWest();
      const bottomRight = bounds.getSouthEast();
      onBoundsChange(topLeft, bottomRight);
    },
    locationfound: (event) => map.flyTo(event.latlng, 14, { animate: false })
  });

  useEffect(() => void map.locate(), [map]);

  return null;
}

export default function Map() {
  const [potholes, setPotholes] = useState<MiniPothole[]>([]);
  const [activePopupId, setActivePopupId] = useState<string>();

  const [flyCoords, setFlyCoords] = useState<[number, number]>();

  async function fetchPotholes(topLeft: L.LatLng, bottomRight: L.LatLng) {
    const [data, error] = await fetchEndpoint<MiniPothole[]>(`/pothole/area?nwlat=${topLeft.lat}&nwlng=${topLeft.lng}&selat=${bottomRight.lat}&selng=${bottomRight.lng}`);
    if (error) return console.error(error);
    setPotholes(data);
  }

  return (
    <div className="relative h-dvh w-dvw">
      <div className="absolute top-4 right-4 z-1000 h-1/2 w-80 overflow-y-scroll rounded-xl bg-neutral-100 shadow-lg">
        <div className="sticky top-0 z-50 flex items-center justify-between bg-neutral-100 p-4 shadow-sm">
          <p className="font-bold">Potholes in this area ({potholes.length})</p>
          <img className="size-12" src="/logo.svg" alt="" />
        </div>

        <ul>
          {potholes
            .toSorted((a, b) => b.overallScore - a.overallScore)
            .map((pothole) => (
              <li
                key={pothole.uuid}
                onClick={() => {
                  setFlyCoords([pothole.latitude, pothole.longitude]);
                  setActivePopupId(pothole.uuid);
                }}
                className="flex cursor-pointer flex-col gap-1 border-t border-neutral-300 p-4 transition-colors hover:bg-neutral-200"
              >
                <div className="flex items-center justify-between gap-2">
                  <h3 className="shrink-0 font-medium text-nowrap">Score: {pothole.overallScore}</h3>
                  <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-300">
                    <div
                      className={`absolute top-0 left-0 h-full ${pothole.overallScore > 30 ? (pothole.overallScore > 50 ? "bg-red-500" : "bg-yellow-500") : "bg-green-500"}`}
                      style={{ width: `${pothole.overallScore}%` }}
                    ></div>
                  </div>
                </div>
                <p className="text-sm">{pothole.address ? pothole.address : `${pothole.latitude.toFixed(4)}, ${pothole.longitude.toFixed(4)}`}</p>
                <p className="text-xs text-neutral-700">Detected {new Date(pothole.timestamp * 1000).toLocaleString()}</p>
              </li>
            ))}
        </ul>
      </div>

      <MapContainer center={[0, 0]} zoom={3} style={{ height: "100%", width: "100%" }}>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        <MapEventHandler onBoundsChange={fetchPotholes} />

        <MapFlyer coords={flyCoords} />

        {potholes.map((pothole) => (
          <Marker
            key={pothole.uuid}
            position={[pothole.latitude, pothole.longitude]}
            eventHandlers={{
              popupopen: () => setActivePopupId(pothole.uuid),
              popupclose: () => setActivePopupId(undefined)
            }}
          >
            <Popup autoPan={false}>
              <PopupContent pothole={pothole} isActive={activePopupId === pothole.uuid} />
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}

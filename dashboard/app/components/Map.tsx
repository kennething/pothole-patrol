"use client";

import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from "react-leaflet";
import { fetchEndpoint } from "../utils/fetch";
import { MiniPothole } from "../utils/types";
import { useEffect, useState } from "react";
import L from "leaflet";

import PopupContent from "./PopupContent";

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
    locationfound: (event) => map.flyTo(event.latlng, 14)
  });

  useEffect(() => void map.locate(), [map]);

  return null;
}

export default function Map() {
  const [potholes, setPotholes] = useState<MiniPothole[]>([]);
  const [activePopupId, setActivePopupId] = useState<string>();

  async function fetchPotholes(topLeft: L.LatLng, bottomRight: L.LatLng) {
    const [data, error] = await fetchEndpoint<MiniPothole[]>(`/pothole/area?nwlat=${topLeft.lat}&nwlng=${topLeft.lng}&selat=${bottomRight.lat}&selng=${bottomRight.lng}`);
    if (error) return console.error(error);
    setPotholes(data);
  }

  return (
    <div className="h-dvh w-dvw">
      <MapContainer center={[0, 0]} zoom={3} style={{ height: "100%", width: "100%" }}>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />

        <MapEventHandler onBoundsChange={fetchPotholes} />

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

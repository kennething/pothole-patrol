import { useMapEvents } from "react-leaflet";
import { useEffect } from "react";

export default function MapFlyer({ coords }: { coords?: [number, number] }) {
  const map = useMapEvents({});

  useEffect(() => {
    if (coords) {
      map.flyTo(coords, 17, {
        animate: true,
        duration: 1.5
      });
    }
  }, [coords, map]);

  return null;
}

import { useEffect, useState } from "react";
import { MiniPothole, Pothole } from "../utils/types";
import { fetchEndpoint } from "../utils/fetch";

export default function PopupContent({ pothole, isActive }: { pothole: MiniPothole; isActive: boolean }) {
  const [details, setDetails] = useState<Pothole>();
  const [isLoading, setLoading] = useState(false);

  useEffect(() => {
    if (!isActive || details) return;

    async function getDetails() {
      setLoading(true);

      console.log(pothole.uuid);
      const [data, error] = await fetchEndpoint<Pothole>(`/pothole/detail?uuid=${pothole.uuid}`);
      if (error) console.error("Failed to fetch details:", error);
      else setDetails(data);

      setLoading(false);
    }

    getDetails();
  }, [isActive, pothole.uuid, details]);

  return (
    <div className="flex min-w-50 flex-col items-center justify-center gap-2 p-2">
      <h3 className="text-lg font-bold">Overall Score: {pothole.overallScore}</h3>
      <div className="relative h-2 w-full overflow-hidden rounded-full bg-neutral-300">
        <div
          className={`absolute top-0 left-0 h-full ${pothole.overallScore > 30 ? (pothole.overallScore > 50 ? "bg-red-500" : "bg-yellow-500") : "bg-green-500"}`}
          style={{ width: `${pothole.overallScore}%` }}
        ></div>
      </div>
      <p className="text-sm">{pothole.address ? pothole.address : `${pothole.latitude.toFixed(4)}, ${pothole.longitude.toFixed(4)} (no address found)`}</p>
      <p className="text-xs text-neutral-700">Detected {new Date(pothole.timestamp * 1000).toLocaleString()}</p>

      <div className="mt-3">
        {isLoading ? (
          <p className="animate-pulse text-sm text-gray-500">Loading details...</p>
        ) : details ? (
          <div className="space-y-1">
            {/* <p className="text-sm font-medium">Transit Importance: {details.areaTransitRidership}</p> */}
            {/* <p className="text-sm font-medium">GDP: {details.areaGdp}</p> */}
            <p className="text-sm font-medium">Income: {details.areaIncome}</p>
            <p className="text-sm font-medium">Commercial: {details.areaCommercial}</p>
            <p className="text-sm font-medium">Traffic Density: {details.trafficDensity}</p>
            <p className="text-sm font-medium">Pothole Severity: {details.potholeSeverity}</p>
            <img className="mt-2" src={`data:image/jpeg;base64,${details.image}`} alt="" />
          </div>
        ) : (
          <p className="text-sm text-red-500">Failed to load additional data.</p>
        )}
      </div>
    </div>
  );
}

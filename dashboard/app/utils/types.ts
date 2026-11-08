export type MiniPothole = {
  uuid: string;
  timestamp: number;
  latitude: number;
  longitude: number;
  overallScore: number;
};

export type Pothole = MiniPothole & {
  address: string | null;
  areaTransitRidership: number;
  areaGdp: number;
  areaIncome: number;
  areaCommercial: number;
  trafficDensity: number;
  potholeSeverity: number;
  image: string;
};

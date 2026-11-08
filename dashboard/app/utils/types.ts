export type MiniPothole = {
  uuid: string;
  timestamp: number;
  latitude: number;
  longitude: number;
  address: string | null;
  overallScore: number;
};

export type Pothole = MiniPothole & {
  areaTransitRidership: number;
  areaGdp: number;
  areaIncome: number;
  areaCommercial: number;
  trafficDensity: number;
  potholeSeverity: number;
  image: string;
};

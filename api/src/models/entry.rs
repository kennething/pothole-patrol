use rocket::serde::Serialize;

#[derive(Serialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct Entry {
  uuid: String,
  timestamp: u32,
  latitude: f64,
  longitude: f64,
  overall_score: u32,
  area_transit_ridership: u32,
  area_gdp: u32,
  area_income: u32,
  area_commercial: u32,
  traffic_density: u32,
  pothole_severity: u32,
}
impl Entry {
  pub fn new(
    uuid: String,
    timestamp: u32,
    latitude: f64,
    longitude: f64,
    overall_score: u32,
    area_transit_ridership: u32,
    area_gdp: u32,
    area_income: u32,
    area_commercial: u32,
    traffic_density: u32,
    pothole_severity: u32
  ) -> Self {
    Self {
      uuid,
      timestamp,
      latitude,
      longitude,
      overall_score,
      area_transit_ridership,
      area_gdp,
      area_income,
      area_commercial,
      traffic_density,
      pothole_severity,
    }
  }
}

use rocket::serde::Serialize;

#[derive(Serialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct MinifiedEntry {
  pub uuid: String,
  pub timestamp: u32,
  pub latitude: f64,
  pub longitude: f64,
  pub overall_score: u32,
}

#[derive(Serialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct Entry {
  pub uuid: String,
  pub timestamp: u32,
  pub latitude: f64,
  pub longitude: f64,
  pub address: Option<String>,
  pub overall_score: u32,
  pub area_transit_ridership: u32,
  pub area_gdp: u32,
  pub area_income: u32,
  pub area_commercial: u32,
  pub traffic_density: u32,
  pub pothole_severity: u32,
  pub image: String,
}

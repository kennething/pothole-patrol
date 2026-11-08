use rocket::serde::Deserialize;
use std::error::Error;

// Define structs to match the Geocodio JSON response format
#[derive(Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
struct GeocodioResponse {
  results: Vec<GeocodioResult>,
}

#[derive(Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
struct GeocodioResult {
  formatted_address: String,
}

pub async fn get_address(latitude: f64, longitude: f64) -> Result<String,  Box<dyn Error + Send + Sync>> {
  let url: String = format!("https://api.geocod.io/v2.1/reverse?q={},{}&api_key={}", latitude, longitude, std::env::var("GEOCODIO_API_KEY").expect("GEOCODIO_API_KEY must be set in .env"));

  let response: GeocodioResponse = reqwest::get(&url).await?.json::<GeocodioResponse>().await?;

  if let Some(best_match) = response.results.first() {
    Ok(best_match.formatted_address.clone())
  } else {
    Err("No address found for these coordinates.".into())
  }
}

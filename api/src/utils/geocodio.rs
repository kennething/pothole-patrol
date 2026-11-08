use rocket::serde::Deserialize;
use std::error::Error;
use reqwest::Client;

#[derive(Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct BatchGeocodioResponse {
  pub results: Vec<BatchItem>,
}

#[derive(Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct BatchItem {
  pub response: GeocodioResponse,
}

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

pub async fn get_addresses(coordinates: &[(f64, f64)]) -> Result<Vec<Option<String>>, Box<dyn Error + Send + Sync>> {
  let url: String = format!("https://api.geocod.io/v2.1/reverse?api_key={}", std::env::var("GEOCODIO_API_KEY").expect("GEOCODIO_API_KEY must be set in .env"));

  let payload: Vec<String> = coordinates
    .iter()
    .map(|(lat, lon)| format!("{},{}", lat, lon))
    .collect();

  let client: Client = Client::new();
  let batch_response: BatchGeocodioResponse = client.post(&url).json(&payload).send().await?.json::<BatchGeocodioResponse>().await?;

  let addresses: Vec<Option<String>> = batch_response.results
    .into_iter()
    .map(|item| {
      item.response.results
        .into_iter()
        .next()
        .map(|best_match| best_match.formatted_address)
    })
    .collect();

  Ok(addresses)
}

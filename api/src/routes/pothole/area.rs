use rocket::{ http::Status, serde::json::Json };
use rocket_db_pools::Connection;
use sqlx::postgres::PgRow;

use crate::utils::db::{ Db, get_from_row };
use crate::utils::geocodio::get_addresses;
use crate::models::MinifiedEntry;

/// # Area
/// Gets all potholes in an area.
///
/// **Route**: /pothole/area?nwlat&nwlng&selat&selng
///
/// **Request method**: GET
///
/// **Output**:
/// ```ts
/// {
///   uuid: string;
///   timestamp: number;
///   latitude: number;
///   longitude: number;
///   overall_score: number;
/// }[]
/// ```
#[get("/area?<nwlat>&<nwlng>&<selat>&<selng>")]
pub async fn area(mut db: Connection<Db>, nwlat: f64, nwlng: f64, selat: f64, selng: f64) -> Result<Json<Vec<MinifiedEntry>>, Status> {
  let rows: Vec<PgRow> = sqlx
    ::query("SELECT uuid, timestamp, latitude, longitude, overall_score FROM entries WHERE latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4")
    .bind(selat)
    .bind(nwlat)
    .bind(nwlng)
    .bind(selng)
    .fetch_all(&mut **db).await
    .unwrap();

  let coordinates: Vec<(f64, f64)> = rows
    .iter()
    .clone()
    .into_iter()
    .map(|row: &PgRow| {
      let latitude: f64 = get_from_row(&row, "latitude");
      let longitude: f64 = get_from_row(&row, "longitude");
      (latitude, longitude)
    })
    .collect();
  let addresses: Vec<Option<String>> = get_addresses(&coordinates).await
    .ok()
    .unwrap_or_else(|| vec![None; coordinates.len()]);

  let entries: Vec<MinifiedEntry> = rows
    .into_iter()
    .zip(addresses.into_iter())
    .map(|(row, address)| {
      MinifiedEntry {
        uuid: get_from_row(&row, "uuid"),
        timestamp: get_from_row::<i32>(&row, "timestamp") as u32,
        latitude: get_from_row(&row, "latitude"),
        longitude: get_from_row(&row, "longitude"),
        address,
        overall_score: get_from_row::<i32>(&row, "overall_score") as u32,
      }
    })
    .collect();

  Ok(Json(entries))
}

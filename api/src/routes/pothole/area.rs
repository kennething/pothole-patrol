use rocket::{ http::Status, serde::json::Json };
use rocket_db_pools::Connection;
use sqlx::postgres::PgRow;

use crate::utils::db::{ Db, get_from_row };
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
  let entries: Vec<MinifiedEntry> = sqlx
    ::query("SELECT uuid, timestamp, latitude, longitude, overall_score FROM entries WHERE latitude BETWEEN $1 AND $2 AND longitude BETWEEN $3 AND $4")
    .bind(selat)
    .bind(nwlat)
    .bind(nwlng)
    .bind(selng)
    .fetch_all(&mut **db).await
    .and_then(|rows: Vec<PgRow>| {
      rows
        .into_iter()
        .map(|row: PgRow| {
          Ok(MinifiedEntry {
            uuid: get_from_row::<String>(&row, "uuid"),
            timestamp: get_from_row::<i32>(&row, "timestamp") as u32,
            latitude: get_from_row::<f64>(&row, "latitude"),
            longitude: get_from_row::<f64>(&row, "longitude"),
            overall_score: get_from_row::<i32>(&row, "overall_score") as u32,
          })
        })
        .collect()
    })
    .unwrap();

  Ok(Json(entries))
}

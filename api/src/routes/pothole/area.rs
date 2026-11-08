use rocket::{ http::Status, serde::json::Json };
use rocket_db_pools::Connection;
use sqlx::postgres::PgRow;

use crate::utils::db::{ Db, get_from_row };
use crate::models::Entry;

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
///   area_transit_ridership: number;
///   area_gdp: number;
///   area_income: number;
///   area_commercial: number;
///   traffic_density: number;
///   pothole_severity: number;
/// }[]
/// ```
#[get("/area?<nwlat>&<nwlng>&<selat>&<selng>")]
pub async fn area(mut db: Connection<Db>, nwlat: f64, nwlng: f64, selat: f64, selng: f64) -> Result<Json<Vec<Entry>>, Status> {
  let entries: Vec<Entry> = sqlx
    ::query("SELECT * FROM entries WHERE latitude BETWEEN $1 AND $2 AND (longitude >= $3 OR longitude <= $4)")
    .bind(nwlat)
    .bind(selat)
    .bind(nwlng)
    .bind(selng)
    .fetch_all(&mut **db).await
    .and_then(|rows: Vec<PgRow>| {
      rows
        .into_iter()
        .map(|row: PgRow| {
          let uuid: String = get_from_row(&row, "uuid");
          let timestamp: i64 = get_from_row(&row, "timestamp");
          let latitude: f64 = get_from_row(&row, "latitude");
          let longitude: f64 = get_from_row(&row, "longitude");
          let overall_score: i64 = get_from_row(&row, "overall_score");
          let area_transit_ridership: i64 = get_from_row(&row, "area_transit_ridership");
          let area_gdp: i64 = get_from_row(&row, "area_gdp");
          let area_income: i64 = get_from_row(&row, "area_income");
          let area_commercial: i64 = get_from_row(&row, "area_commercial");
          let traffic_density: i64 = get_from_row(&row, "traffic_density");
          let pothole_severity: i64 = get_from_row(&row, "pothole_severity");
          Ok(
            Entry::new(
              uuid,
              timestamp as u32,
              latitude,
              longitude,
              overall_score as u32,
              area_transit_ridership as u32,
              area_gdp as u32,
              area_income as u32,
              area_commercial as u32,
              traffic_density as u32,
              pothole_severity as u32
            )
          )
        })
        .collect()
    })
    .unwrap();

  Ok(Json(entries))
}

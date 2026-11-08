use rocket::{ http::Status, serde::json::Json };
use rocket_db_pools::Connection;
use sqlx::postgres::PgRow;

use crate::utils::db::{ Db, get_from_row };
use crate::utils::image::get_image_base64;
use crate::models::Entry;

/// # Detail
/// Gets extended details about a pothole given its UUID.
///
/// **Route**: /pothole/area?uuid
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
///   image: string; // base64 encoded image
/// }
/// ```
#[get("/detail?<uuid>")]
pub async fn detail(mut db: Connection<Db>, uuid: String) -> Result<Json<Entry>, Status> {
  let row: PgRow = sqlx::query("SELECT * FROM entries WHERE uuid = $1").bind(uuid).fetch_one(&mut **db).await.unwrap();

  let uuid: String = get_from_row(&row, "uuid");
  let image: String = get_image_base64(&uuid).await.map_err(|_| Status::NotFound)?;

  let entry: Entry = Entry {
    uuid,
    timestamp: get_from_row::<i64>(&row, "timestamp") as u32,
    latitude: get_from_row::<f64>(&row, "latitude"),
    longitude: get_from_row::<f64>(&row, "longitude"),
    overall_score: get_from_row::<i64>(&row, "overall_score") as u32,
    area_transit_ridership: get_from_row::<i64>(&row, "area_transit_ridership") as u32,
    area_gdp: get_from_row::<i64>(&row, "area_gdp") as u32,
    area_income: get_from_row::<i64>(&row, "area_income") as u32,
    area_commercial: get_from_row::<i64>(&row, "area_commercial") as u32,
    traffic_density: get_from_row::<i64>(&row, "traffic_density") as u32,
    pothole_severity: get_from_row::<i64>(&row, "pothole_severity") as u32,
    image,
  };

  Ok(Json(entry))
}

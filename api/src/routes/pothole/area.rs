use rocket::{ http::Status, serde::{ json::Json, Deserialize } };
use rocket_db_pools::Connection;
use crate::utils::db::Db;

#[derive(Deserialize)]
#[serde(crate = "rocket::serde", rename_all = "camelCase")]
pub struct AreaInput {
  /// GPS coordinate of the NE corner of the area.
  ///
  /// Format: `<latitude>, <longitude>`
  pub ne: String,
  /// GPS coordinate of the SW corner of the area.
  ///
  /// Format: `<latitude>, <longitude>`
  pub sw: String,
}

/// # Area
/// Gets all potholes in an area.
///
/// **Route**: /pothole/area
///
/// **Request method**: POST
///
/// **Input**:
/// ```ts
/// {
///   ne: `${number}, ${number}`;
///   sw: `${number}, ${number}`;
/// }
/// ```
///
/// **Output**:
/// ```ts
/// []
/// ```
#[post("/area", data = "<data>")]
pub async fn area(mut db: Connection<Db>, data: Json<AreaInput>) -> Result<Json<()>, Status> {
  // TODO: prolly make this GET
  Ok(Json(()))
}

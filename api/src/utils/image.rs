use base64::{ engine::general_purpose::STANDARD, Engine };
use std::{ path::PathBuf, error::Error };
use sqlx::PgPool;
use uuid::Uuid;
use tokio::fs;

const IMAGE_DIR: &str = "images";
const MAX_DISTANCE_METERS: f64 = 5.0;

pub async fn save_image(pool: &PgPool, uuid: &str, data: &[u8], latitude: f64, longitude: f64) -> Result<Option<PathBuf>, Box<dyn Error + Send + Sync>> {
  let uuid: Uuid = Uuid::parse_str(uuid)?;

  if !latitude.is_finite() || !longitude.is_finite() || !(-90.0..=90.0).contains(&latitude) || !(-180.0..=180.0).contains(&longitude) {
    return Err("Invalid coordinates".into());
  }

  let exists: bool = sqlx
    ::query_scalar(
      r#"
      SELECT EXISTS (
        SELECT 1
        FROM entries
        WHERE
          2 * 6371000 * ASIN(
            SQRT(
              LEAST(1.0, GREATEST(0.0,
                POWER(
                  SIN(RADIANS(latitude - $1) / 2),
                  2
                )
                +
                COS(RADIANS($1))
                * COS(RADIANS(latitude))
                * POWER(
                  SIN(RADIANS(longitude - $2) / 2),
                  2
                )
              ))
            )
          ) <= $3
      )
      "#
    )
    .bind(latitude)
    .bind(longitude)
    .bind(MAX_DISTANCE_METERS)
    .fetch_one(pool).await?;

  if exists {
    return Err("A pothole has already been reported in this area".into());
  }

  fs::create_dir_all(IMAGE_DIR).await?;

  let path: PathBuf = PathBuf::from(IMAGE_DIR).join(format!("{uuid}.jpg"));
  fs::write(&path, data).await?;

  Ok(Some(path))
}

pub async fn get_image_base64(uuid: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
  let uuid: Uuid = Uuid::parse_str(uuid)?;

  let path: PathBuf = PathBuf::from(IMAGE_DIR).join(format!("{uuid}.jpg"));
  let bytes: Vec<u8> = fs::read(path).await?;

  Ok(STANDARD.encode(bytes))
}

use base64::{ engine::general_purpose::STANDARD, Engine };
use std::{ path::PathBuf, error::Error };
use uuid::Uuid;
use tokio::fs;

const IMAGE_DIR: &str = "images";

pub async fn save_image(uuid: &str, data: &[u8]) -> Result<PathBuf, Box<dyn Error + Send + Sync>> {
  let uuid: Uuid = Uuid::parse_str(uuid)?;

  fs::create_dir_all(IMAGE_DIR).await?;

  let path: PathBuf = PathBuf::from(IMAGE_DIR).join(format!("{uuid}.jpg"));
  fs::write(&path, data).await?;

  Ok(path)
}

pub async fn get_image_base64(uuid: &str) -> Result<String, Box<dyn Error + Send + Sync>> {
  let uuid: Uuid = Uuid::parse_str(uuid)?;

  let path: PathBuf = PathBuf::from(IMAGE_DIR).join(format!("{uuid}.jpg"));
  let bytes: Vec<u8> = fs::read(path).await?;

  Ok(STANDARD.encode(bytes))
}

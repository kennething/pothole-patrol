use crate::result::{ processing_service_client::ProcessingServiceClient, ProcessingResult, StreamRequest };

use std::{ sync::Arc, error::Error, time::Duration };
use tonic::transport::{ Endpoint, Channel };
use rocket_db_pools::sqlx;
use sqlx::PgPool;

pub async fn subscribe(pool: PgPool, server_url: String, stream_id: String) {
  loop {
    if let Err(error) = receive_results(&pool, &server_url, &stream_id).await {
      eprintln!("grpc error: {error}");
    }

    tokio::time::sleep(Duration::from_secs(3)).await;
  }
}

async fn receive_results(pool: &PgPool, server_url: &str, stream_id: &str) -> Result<(), Box<dyn Error + Send + Sync>> {
  let channel: Channel = Endpoint::from_shared(server_url.to_owned())?.connect_timeout(Duration::from_secs(5)).connect().await?;

  let mut client = ProcessingServiceClient::new(channel);

  let response = client.stream_results(StreamRequest {
    stream_id: stream_id.to_owned(),
  }).await?;

  let mut stream = response.into_inner();

  while let Some(result) = stream.message().await? {
    if let Err(error) = save_result(pool, &result).await {
      eprintln!("Database insert failed: {error}");
    }
  }

  Ok(())
}

async fn save_result(pool: &PgPool, result: &ProcessingResult) -> Result<(), sqlx::Error> {
  sqlx
    ::query(
      r#"
        INSERT INTO results (
            uuid,
            timestamp,
            latitude,
            longitude,
            overall_score,
            area_transit_ridership,
            area_gdp,
            area_income,
            area_commercial,
            traffic_density,
            pothole_severity
        )
        VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10, $11
        )
        "#
    )
    .bind(&result.uuidv7)
    .bind(i64::try_from(result.timestamp).expect("timestamp overflow"))
    .bind(result.latitude)
    .bind(result.longitude)
    .bind(result.overall_score as i32)
    .bind(result.area_transit_ridership as i32)
    .bind(result.area_gdp as i32)
    .bind(result.area_income as i32)
    .bind(result.area_commercial as i32)
    .bind(result.traffic_density as i32)
    .bind(result.pothole_severity as i32)
    .execute(pool).await?;

  Ok(())
}

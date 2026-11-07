use rocket_db_pools::{ sqlx, Database };

#[derive(Database)]
#[database("sqlite_db")]
pub struct Db(sqlx::SqlitePool);

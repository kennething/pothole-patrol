use rocket_db_pools::{ sqlx, Database };

#[derive(Database)]
#[database("postgres")]
pub struct Db(pub sqlx::PgPool);

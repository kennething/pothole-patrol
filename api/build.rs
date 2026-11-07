use std::{ path, env, error };

fn main() -> Result<(), Box<dyn error::Error>> {
  let protoc: path::PathBuf = protoc_bin_vendored::protoc_bin_path()?;
  env::set_var("PROTOC", protoc);

  tonic_prost_build::compile_protos("../model/proto/result.proto")?;

  Ok(())
}

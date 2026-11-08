"""Package Dafny 4.11 Rust output without changing compiler-generated source."""
from pathlib import Path
import shutil

def package(work, count):
    root=work/'core-rust'
    (root/'Cargo.toml').write_text('''[package]
name = "agentc_core"
version = "0.1.0"
edition = "2021"

[lib]
path = "src/lib.rs"

[[bin]]
name = "agentc-core"
path = "src/main.rs"

[dependencies]
dafny_runtime = { path = "runtime" }
serde_json = "=1.0.145"
''')
    (root/'src/lib.rs').write_text('''//! Decimal-string boundary for the generated, verified integer core.
//! The adapter is tested separately; it is not part of the Dafny proof.
pub mod core;
use dafny_runtime::DafnyInt;

fn valid_integer(s: &str) -> bool {
    if s.is_empty() || s.len() > 4096 { return false; }
    let digits = s.strip_prefix('-').unwrap_or(s);
    !digits.is_empty() && digits.bytes().all(|b| b.is_ascii_digit())
        && (digits.len() == 1 || !digits.starts_with('0'))
}

pub fn run(values: &[String]) -> Result<String, String> {
    if values.len() != COUNT || !values.iter().all(|s| valid_integer(s)) {
        return Err("expected COUNT decimal integer strings (max 4096 characters each)".into());
    }
    let args: Vec<DafnyInt> = values.iter()
        .map(|s| DafnyInt::parse_bytes(s.as_bytes(), 10)).collect();
    Ok(core::_module::_default::Run(CALL).as_ref().to_string())
}
'''.replace('COUNT',str(count)).replace('CALL',', '.join(f'&args[{i}]' for i in range(count))))
    (root/'src/main.rs').write_text('''use std::io::{self, Read};
use serde_json::{json, Value};

fn execute() -> Result<String, String> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).map_err(|e| e.to_string())?;
    let value: Value = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    let array = value.as_array().ok_or("expected JSON array of decimal strings")?;
    let values: Vec<String> = array.iter().map(|v|
        v.as_str().map(String::from).ok_or("expected decimal strings, not JSON numbers")
    ).collect::<Result<_, _>>()?;
    agentc_core::run(&values)
}
fn main() {
    match execute() {
        Ok(value) => println!("{}", json!({"value": value})),
        Err(error) => {
            println!("{}", json!({"error": error}));
            std::process::exit(1);
        }
    }
}
''')
    lock=Path(__file__).with_name('rust_Cargo.lock')
    if lock.exists(): shutil.copy2(lock,root/'Cargo.lock')
    (work/'RUST.md').write_text('''# Generated Rust integer core

Build: `cargo build --locked --manifest-path core-rust/Cargo.toml`
Run: `cargo run --quiet --locked --manifest-path core-rust/Cargo.toml`
Pass a JSON array of decimal strings on stdin, for example `["123"]` for clamp.
Use `agentc_core::run(&[String, ...])` from Rust to get `Result<String, String>`.
The generated function is in `core-rust/src/core.rs`; do not edit it.

The Rust backend is experimental. Dafny source verification does not prove
compiler correctness, adapter correctness, or the surrounding app. Compile and
test the emitted project before use. The default Dafny runtime uses arbitrary-
precision integers; do not enable its `small-int` feature, which changes semantics.
Cargo and access to its dependency registry (or a populated cache) are required.
The test baseline uses Rust 1.90.0. Never coerce input through f64 or i64 first.
''')

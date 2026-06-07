//! `vx-time` -- out-of-process round-trip latency benchmarker for file-watching
//! toolchains.
//!
//! The `single` subcommand issues one clean filesystem write to a watched input
//! file and measures the wall-clock time until the toolchain's regenerated
//! output asset appears. CLI via clap; the wait is event-driven via `notify`,
//! blocking on the output's Close-Write filesystem event -- no polling.

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::mpsc;
use std::time::Instant;

use clap::{Parser, Subcommand};
use notify::event::{AccessKind, AccessMode};
use notify::{EventKind, RecursiveMode, Watcher};

#[derive(Parser)]
#[command(
    name = "vx-time",
    about = "Round-trip latency benchmarker for file-watching toolchains",
    version
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Measure a single trigger -> output-regenerated round-trip latency.
    Single {
        /// Watched file the toolchain observes; a trailing newline is appended to
        /// change its hash and force a rebuild, then it is saved (Close-Write).
        input: PathBuf,
        /// Generated asset to wait for the toolchain to (re)produce.
        output: PathBuf,
    },
}

/// Run one round-trip measurement and print the latency.
fn run_single(input: &Path, output: &Path) -> Result<(), String> {
    // Step 1: verify the input we trigger exists. `output` is the asset being
    // *generated*, so it is allowed to be absent until the toolchain emits it.
    if !input.exists() {
        return Err(format!("input does not exist: {}", input.display()));
    }
    // Remember the original length so we can truncate the appended newline back
    // off afterwards (trailing byte -> a cheap set_len, no rewrite).
    let orig_len = fs::metadata(input)
        .map_err(|e| format!("failed to stat input: {e}"))?
        .len();

    // Step 2: arm the watcher BEFORE the trigger so no event can be missed.
    // Watch the output's parent directory (non-recursively) -- this also covers
    // the case where the output file does not exist yet. Match events by file
    // name since only this one directory is watched.
    let watch_dir = output.parent().filter(|p| !p.as_os_str().is_empty());
    let watch_dir = match watch_dir {
        Some(p) => p.to_path_buf(),
        None => Path::new(".").to_path_buf(),
    };
    let watch_dir = fs::canonicalize(&watch_dir)
        .map_err(|e| format!("failed to resolve output directory: {e}"))?;
    let target_name = output
        .file_name()
        .ok_or_else(|| format!("output has no file name: {}", output.display()))?
        .to_owned();

    let (tx, rx) = mpsc::channel();
    let mut watcher = notify::recommended_watcher(move |res| {
        let _ = tx.send(res);
    })
    .map_err(|e| format!("failed to create watcher: {e}"))?;
    watcher
        .watch(&watch_dir, RecursiveMode::NonRecursive)
        .map_err(|e| format!("failed to watch output directory: {e}"))?;

    // Step 3: start the monotonic clock immediately before the trigger.
    let start = Instant::now();

    // Step 4: trigger -- append a single newline (changing the file's hash so a
    // hash-filtering toolchain rebuilds), flush, and drop the handle so the OS
    // emits a clean Close-Write notification right away.
    {
        let mut f = OpenOptions::new()
            .append(true)
            .open(input)
            .map_err(|e| format!("failed to open input for appending: {e}"))?;
        f.write_all(b"\n")
            .map_err(|e| format!("failed to append to input: {e}"))?;
        f.flush()
            .map_err(|e| format!("failed to flush input: {e}"))?;
    } // handle closed here

    // Step 5: block on filesystem events until the output file emits a
    // Close-Write -- the toolchain finishing its generated asset. No polling.
    loop {
        match rx.recv() {
            Ok(Ok(event)) => {
                let is_close_write = matches!(
                    event.kind,
                    EventKind::Access(AccessKind::Close(AccessMode::Write))
                );
                if is_close_write
                    && event
                        .paths
                        .iter()
                        .any(|p| p.file_name() == Some(target_name.as_os_str()))
                {
                    break;
                }
            }
            Ok(Err(_)) => {} // watcher error event; keep waiting
            Err(_) => return Err("watch channel closed before output was written".into()),
        }
    }

    // Step 6 & 7: stop the clock and report round-trip latency in ms (3 dp).
    let elapsed = start.elapsed();
    let ms = elapsed.as_secs_f64() * 1000.0;
    println!("⏱️ True Round-Trip Latency: {ms:.3} ms");

    // Restore input by truncating the appended newline (after the clock stops,
    // so it never counts toward the measured latency).
    OpenOptions::new()
        .write(true)
        .open(input)
        .and_then(|f| f.set_len(orig_len))
        .map_err(|e| format!("failed to restore input length: {e}"))?;

    Ok(())
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let result = match cli.command {
        Command::Single { input, output } => run_single(&input, &output),
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

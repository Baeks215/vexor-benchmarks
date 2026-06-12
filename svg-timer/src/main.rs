//! `svg-timer` -- out-of-process round-trip latency benchmarker for file-watching
//! toolchains.
//!
//! The `single` subcommand issues one clean filesystem write to a watched input
//! file and measures the wall-clock time until the toolchain's regenerated
//! output asset appears; `multi` repeats that as N alternating add/remove passes
//! and prints the latencies as CSV. CLI via clap; the wait is event-driven via
//! `notify`, blocking on the output's Close-Write filesystem event -- no polling.

use std::ffi::OsString;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::ExitCode;
use std::sync::mpsc::{self, Receiver};
use std::time::Instant;

use clap::{Parser, Subcommand};
use notify::event::{AccessKind, AccessMode};
use notify::{EventKind, RecommendedWatcher, RecursiveMode, Watcher};

/// Result delivered by the notify watcher over the channel.
type WatchEvent = notify::Result<notify::Event>;

#[derive(Parser)]
#[command(
    name = "svg-timer",
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
    /// Measure N alternating add/remove passes; print latencies as CSV ms.
    Multi {
        /// Number of passes to run (each pass = one input mutation + one rebuild).
        n: usize,
        /// Watched file the toolchain observes (newline appended/removed per pass).
        input: PathBuf,
        /// Generated asset to wait for the toolchain to (re)produce.
        output: PathBuf,
    },
}

/// Arm a notify watcher on the output's parent directory and return the live
/// watcher (kept alive by the caller), the event channel, and the output's file
/// name for matching events. Watching the directory also covers the case where
/// the output does not exist yet.
fn setup_watch(output: &Path) -> Result<(RecommendedWatcher, Receiver<WatchEvent>, OsString), String> {
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

    Ok((watcher, rx, target_name))
}

/// Discard any events already queued, so a stale event from a prior pass cannot
/// prematurely satisfy the next wait.
fn drain(rx: &Receiver<WatchEvent>) {
    while rx.try_recv().is_ok() {}
}

/// Block until the output file emits a Close-Write event. No polling.
fn wait_for_output(rx: &Receiver<WatchEvent>, target_name: &OsString) -> Result<(), String> {
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
                    return Ok(());
                }
            }
            Ok(Err(_)) => {} // watcher error event; keep waiting
            Err(_) => return Err("watch channel closed before output was written".into()),
        }
    }
}

/// Measure one round-trip: drain stale events, start the clock, run `mutate` to
/// trigger the toolchain, then wait for the output's Close-Write. Returns ms.
fn measure(
    rx: &Receiver<WatchEvent>,
    target_name: &OsString,
    mutate: impl FnOnce() -> Result<(), String>,
) -> Result<f64, String> {
    drain(rx);
    let start = Instant::now();
    mutate()?;
    wait_for_output(rx, target_name)?;
    Ok(start.elapsed().as_secs_f64() * 1000.0)
}

/// Append a single newline to `input` (Close-Write trigger; changes the hash).
fn append_newline(input: &Path) -> Result<(), String> {
    let mut f = OpenOptions::new()
        .append(true)
        .open(input)
        .map_err(|e| format!("failed to open input for appending: {e}"))?;
    f.write_all(b"\n")
        .map_err(|e| format!("failed to append to input: {e}"))?;
    f.flush()
        .map_err(|e| format!("failed to flush input: {e}"))?;
    Ok(())
}

/// Truncate `input` back to `len` (Close-Write trigger; removes the newline).
fn truncate_to(input: &Path, len: u64) -> Result<(), String> {
    OpenOptions::new()
        .write(true)
        .open(input)
        .and_then(|f| f.set_len(len))
        .map_err(|e| format!("failed to truncate input: {e}"))
}

/// Run one round-trip measurement and print the latency.
fn run_single(input: &Path, output: &Path) -> Result<(), String> {
    if !input.exists() {
        return Err(format!("input does not exist: {}", input.display()));
    }
    // Remember the original length so we can truncate the appended newline back
    // off afterwards (trailing byte -> a cheap set_len, no rewrite).
    let orig_len = fs::metadata(input)
        .map_err(|e| format!("failed to stat input: {e}"))?
        .len();

    // Arm the watcher BEFORE the trigger so no event can be missed.
    let (_watcher, rx, target_name) = setup_watch(output)?;

    let ms = measure(&rx, &target_name, || append_newline(input))?;
    println!("⏱️ True Round-Trip Latency: {ms:.3} ms");

    // Restore input by truncating the appended newline (after the clock stops,
    // so it never counts toward the measured latency).
    truncate_to(input, orig_len)?;

    Ok(())
}

/// Run N alternating add/remove passes, timing each, and print the latencies as
/// a single comma-separated line of milliseconds (3 dp), in run order.
fn run_multi(n: usize, input: &Path, output: &Path) -> Result<(), String> {
    if !input.exists() {
        return Err(format!("input does not exist: {}", input.display()));
    }
    let orig_len = fs::metadata(input)
        .map_err(|e| format!("failed to stat input: {e}"))?
        .len();

    // Arm the watcher once for the whole run.
    let (_watcher, rx, target_name) = setup_watch(output)?;

    // Each pass toggles the input: even passes append a newline
    // (orig_len -> orig_len+1), odd passes truncate it back (orig_len+1 -> orig_len).
    let mut results = Vec::with_capacity(n);
    for i in 0..n {
        let ms = if i % 2 == 0 {
            measure(&rx, &target_name, || append_newline(input))?
        } else {
            measure(&rx, &target_name, || truncate_to(input, orig_len))?
        };
        results.push(ms);
    }

    let line = results
        .iter()
        .map(|ms| format!("{ms:.3}"))
        .collect::<Vec<_>>()
        .join(",");
    println!("{line}");

    Ok(())
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let result = match cli.command {
        Command::Single { input, output } => run_single(&input, &output),
        Command::Multi { n, input, output } => run_multi(n, &input, &output),
    };

    match result {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("error: {e}");
            ExitCode::FAILURE
        }
    }
}

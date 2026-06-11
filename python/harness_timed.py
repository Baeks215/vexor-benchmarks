import argparse
import os
import time
import traceback
import tracemalloc

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DEBOUNCE_SECONDS = 0.3

GLOBAL_CONTEXT = {"__name__": "__main__"}


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024


def run_once(design_path):
    with open(design_path) as f:
        src = f.read()

    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        exec(src, GLOBAL_CONTEXT)
    except Exception:
        traceback.print_exc()
    finally:
        elapsed = time.perf_counter() - t0
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

    stats = snapshot.statistics("lineno")
    count = sum(s.count for s in stats)
    nbytes = sum(s.size for s in stats)

    print(
        f"Completed: {os.path.basename(design_path)} "
        f"({elapsed * 1000:.1f} ms, {count} allocations, {fmt_bytes(nbytes)})"
    )


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, target):
        self.target = os.path.abspath(target)
        self.last_run = 0.0

    def on_modified(self, event):
        if event.is_directory:
            return
        if os.path.abspath(event.src_path) != self.target:
            return
        now = time.perf_counter()
        if now - self.last_run < DEBOUNCE_SECONDS:
            return
        self.last_run = now
        run_once(self.target)


def main():
    parser = argparse.ArgumentParser(description="Watch a design script and re-run it on change, reporting time and memory.")
    parser.add_argument("input", help="path to the design script to watch and run")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    GLOBAL_CONTEXT["__file__"] = input_path

    os.chdir(os.path.dirname(input_path))
    print(f"[harness] watching {input_path}")
    run_once(input_path)

    handler = ReloadHandler(input_path)
    observer = Observer()
    observer.schedule(handler, os.path.dirname(input_path), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

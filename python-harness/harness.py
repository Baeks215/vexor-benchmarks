import os
import time
import traceback
import tracemalloc

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

HARNESS_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT = os.path.join(HARNESS_DIR, "design", "snake.py")

DEBOUNCE_SECONDS = 0.3


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024


def run_once(path):
    with open(path) as f:
        src = f.read()
    code = compile(src, path, "exec")

    script_dir = os.path.dirname(path)
    cwd = os.getcwd()
    os.chdir(script_dir)

    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        exec(code, {"__name__": "__main__", "__file__": path})
    except Exception:
        traceback.print_exc()
    finally:
        elapsed = time.perf_counter() - t0
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        os.chdir(cwd)

    stats = snapshot.statistics("lineno")
    count = sum(s.count for s in stats)
    nbytes = sum(s.size for s in stats)

    print(
        f"[harness] {os.path.basename(path)}: "
        f"{elapsed * 1000:.1f} ms, {count} allocations, {fmt_bytes(nbytes)}"
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
    print(f"[harness] watching {INPUT}")
    run_once(INPUT)

    handler = ReloadHandler(INPUT)
    observer = Observer()
    observer.schedule(handler, os.path.dirname(INPUT), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()

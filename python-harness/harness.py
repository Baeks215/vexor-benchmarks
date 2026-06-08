import argparse
import os
import time
import traceback

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

DEBOUNCE_SECONDS = 0

GLOBAL_CONTEXT = {"__name__": "__main__"}


def run_once(design_path):
    with open(design_path) as f:
        src = f.read()
    try:
        exec(src, GLOBAL_CONTEXT)
    except Exception:
        traceback.print_exc()
    print(f"Completed: {os.path.basename(design_path)}")


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
    parser = argparse.ArgumentParser(description="Watch a design script and re-run it on change.")
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

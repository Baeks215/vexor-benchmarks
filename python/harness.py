import argparse
import os
import time
import traceback

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

GLOBAL_CONTEXT = {"__name__": "__main__"}


def execute(design_path):
    with open(design_path) as f:
        src = f.read()
    try:
        # Dynamically execute code from design_path
        exec(src, GLOBAL_CONTEXT)
    except Exception:
        traceback.print_exc()

    print(f"Executed: {os.path.basename(design_path)}")


class ReloadHandler(FileSystemEventHandler):
    def __init__(self, target):
        self.target = os.path.abspath(target)

    def on_modified(self, event):
        if event.is_directory:
            return
        if os.path.abspath(event.src_path) != self.target:
            return
        # re-execute
        execute(self.target)


def main():
    parser = argparse.ArgumentParser(
        description="Watch a design script and re-run it when it changes."
    )
    parser.add_argument("input", help="path to the design script")
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)

    # Initial execution
    execute(input_path)

    print(f"[harness] watching {input_path}")

    # Watch
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

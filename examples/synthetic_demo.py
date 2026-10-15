"""Compatibility entry point; installed users can run `photo-locate demo`."""
import sys
from photo_location_workflow.cli import main

if __name__ == '__main__':
    raise SystemExit(main(['demo', *sys.argv[1:]]))

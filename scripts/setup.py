#!/usr/bin/env python3
"""Version-neutral CodePug configuration entry point.

The tested password-hash implementation remains in setup_v06 for backwards
compatibility. This entry point is the public command for v0.7 and beyond.
"""
from setup_v06 import main

if __name__ == "__main__":
    main()

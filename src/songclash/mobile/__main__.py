"""Allows ``python -m songclash.mobile`` to preview the Android UI on a desktop."""

from songclash.mobile.app import main

if __name__ == "__main__":
    main().main_loop()

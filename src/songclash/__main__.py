"""Allows ``python -m songclash``. Briefcase also starts the Android app this way."""

import sys

if __name__ == "__main__":
    if hasattr(sys, "getandroidapilevel"):
        from songclash.mobile.app import main as mobile_main

        mobile_main().main_loop()
    else:
        from songclash.app import main

        main()

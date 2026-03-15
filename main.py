import sys
import os
from streamlit.web import cli as stcli


def main():
    """
    Main entry point for the WhatYouSaid application.
    This script launches the Streamlit interface.
    """
    # Path to the actual streamlit application file
    app_path = os.path.join(os.path.dirname(__file__), "frontend", "streamlit_app.py")

    # Configure arguments for streamlit
    # This is equivalent to running: streamlit run frontend/streamlit_app.py
    sys.argv = [
        "streamlit",
        "run",
        "--server.runOnSave=true",
        app_path,
    ]

    # Execute streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()

import sys
import argparse
from whisperdesktop.application_controller import ApplicationController
from whisperdesktop.utils.logger import Logger
import logging


def main():
    parser = argparse.ArgumentParser(description="WhisperDesktop - Real-time Speech Transcription")
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--config', type=str, default=None, help='Path to custom config file (not yet supported)')
    args = parser.parse_args()

    # Configure logging level
    logger = Logger()
    if args.debug:
        logger.logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled.")
    else:
        logger.logger.setLevel(logging.INFO)

    # Note: --config is parsed but not yet wired to ApplicationController or ConfigurationManager
    # Future: Pass args.config to ApplicationController or ConfigurationManager when supported
    try:
        app = ApplicationController()
        return app.run()
    except Exception as e:
        logger.error(f"Error in main: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
"""API server entry point."""

import sys
import uvicorn

# No longer need sys.path manipulation with proper package structure


def run():
    """Run the API server."""
    from .api import app
    uvicorn.run(app, host='0.0.0.0', port=5002)


if __name__ == '__main__':
    run()
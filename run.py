"""Start Atlas with proper signal handling and port reuse.

Fixes the Windows zombie socket problem where port 8888 stays
LISTENING after the server is killed, blocking restarts.

Usage: python run.py
"""

import socket
import sys
import signal

import uvicorn
from uvicorn.config import Config
from uvicorn.server import Server

from app.config import ATLAS_HOST, ATLAS_PORT


class ReuseAddrServer(Server):
    """Uvicorn server that sets SO_REUSEADDR on Windows."""

    def _log_started_message(self, listeners):
        # Just call parent
        super()._log_started_message(listeners)

    async def startup(self, sockets=None):
        if sockets is None:
            # Create our own socket with SO_REUSEADDR before uvicorn does
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.config.host, self.config.port))
            sock.set_inheritable(True)
            sockets = [sock]
        await super().startup(sockets=sockets)


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    config = Config(
        "app.main:app",
        host=ATLAS_HOST,
        port=ATLAS_PORT,
        timeout_graceful_shutdown=5,
    )
    server = ReuseAddrServer(config=config)
    server.run()


if __name__ == "__main__":
    main()

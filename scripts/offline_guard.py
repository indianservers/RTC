"""Fail closed on Python socket egress, including DNS and already-created sockets."""

import os
import socket
import sys


def enforce_offline():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    def audit(event, args):
        if event in {
            "socket.connect",
            "socket.connect_ex",
            "socket.getaddrinfo",
            "socket.sendto",
        }:
            raise RuntimeError("Offline smoke test blocked network: " + event)

    sys.addaudithook(audit)

    def blocked(*args, **kwargs):
        raise RuntimeError("Offline smoke test blocked network")

    socket.create_connection = blocked

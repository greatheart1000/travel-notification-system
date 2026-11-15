from __future__ import annotations

import urllib.request

import pytest

from tests.conftest import RealNetworkBlocked


def test_real_network_is_blocked_for_urllib() -> None:
    with pytest.raises(RealNetworkBlocked):
        urllib.request.urlopen("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test")


def test_real_network_is_blocked_for_raw_socket() -> None:
    import socket

    with pytest.raises(RealNetworkBlocked):
        socket.create_connection(("qyapi.weixin.qq.com", 443), timeout=1)

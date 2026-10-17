"""Opt-in private-LAN pairing. Secrets and device sessions only live in memory."""

from collections import deque
from http.cookies import CookieError, SimpleCookie
import io
import ipaddress
import secrets
import socket
import threading
import time

PRIVATE_NETWORKS = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))


class PairingThrottled(ValueError):
    pass


def lan_address(value=None):
    if value is None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Select a route without sending a packet.
                sock.connect(('192.0.2.1', 9))
                value = sock.getsockname()[0]
        except OSError as exc:
            raise ValueError('Cannot find a LAN address. Connect to Wi-Fi or pass --lan-address.') from exc
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError as exc:
        raise ValueError('Use a private IPv4 LAN address.') from exc
    if not any(address in network for network in PRIVATE_NETWORKS):
        raise ValueError('LAN mode requires an RFC1918 private IPv4 address, not a public or wildcard address.')
    return str(address)


def matches(value, secret):
    return isinstance(value, str) and value.isascii() and secrets.compare_digest(value, secret)


class Pairing:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.lock = threading.RLock()
        self.admin_secret = secrets.token_urlsafe(32)
        self.sessions = {}
        self.failures = {}
        self.global_failures = deque(maxlen=100)
        self.rotate()

    def rotate(self):
        self.code = f'{secrets.randbelow(100_000_000):08d}'
        self.phone_secret = secrets.token_urlsafe(32)

    def role(self, cookie, port):
        try:
            parsed = SimpleCookie(cookie or '')
            item = parsed.get(f'plw_{port}')
        except CookieError:
            return None
        if not item:
            return None
        with self.lock:
            entry = self.sessions.get(item.value)
            if not entry:
                return None
            if entry['expires'] <= self.clock():
                self.sessions.pop(item.value, None)
                return None
            return entry['role']

    def exchange(self, body, peer):
        with self.lock:
            now = self.clock()
            self.failures = {key: deque((t for t in items if t > now - 300), maxlen=10)
                             for key, items in self.failures.items() if items and items[-1] > now - 300}
            self.global_failures = deque((t for t in self.global_failures if t > now - 300), maxlen=100)
            attempts = self.failures.setdefault(peer, deque(maxlen=10))
            if len(attempts) >= 10 or len(self.global_failures) >= 100:
                raise PairingThrottled('Too many pairing attempts. Wait five minutes and try again. / 请五分钟后再试。')
            role = 'admin' if matches(body.get('admin'), self.admin_secret) else (
                'phone' if matches(body.get('code'), self.code) or matches(body.get('pair'), self.phone_secret) else None)
            if not role:
                attempts.append(now)
                self.global_failures.append(now)
                raise ValueError('Connection code is incorrect or expired. / 连接码错误或已失效。')
            self.sessions = {key: entry for key, entry in self.sessions.items() if entry['expires'] > now}
            if len(self.sessions) >= 64:
                raise ValueError('Too many paired devices. Disconnect unused devices first.')
            session = secrets.token_urlsafe(32)
            self.sessions[session] = {'role': role, 'expires': now + 12 * 3600}
            self.failures.pop(peer, None)
            return session

    def disconnect(self, cookie, port):
        try:
            parsed = SimpleCookie(cookie or '')
            item = parsed.get(f'plw_{port}')
        except CookieError:
            return
        with self.lock:
            if item:
                self.sessions.pop(item.value, None)

    def revoke_phones(self):
        with self.lock:
            self.sessions = {key: entry for key, entry in self.sessions.items() if entry['role'] == 'admin'}
            self.rotate()

    def state(self, url, admin):
        with self.lock:
            value = {'enabled': True, 'admin': admin}
            if admin:
                value.update(url=url, link=url + '/#pair=' + self.phone_secret, code=self.code,
                             devices=sum(e['role'] == 'phone' and e['expires'] > self.clock() for e in self.sessions.values()))
                try:
                    import qrcode  # noqa: F401
                    value['qr_available'] = True
                except ImportError:
                    value['qr_available'] = False
            return value

    def qr(self, url):
        try:
            import qrcode
        except ImportError as exc:
            raise ValueError('Install the mobile extra for QR codes; the connection code still works.') from exc
        with self.lock:
            output = io.BytesIO()
            qrcode.make(url + '/#pair=' + self.phone_secret).save(output, format='PNG')
            return output.getvalue()


def session_cookie(value, port, clear=False):
    return f'plw_{port}={value}; Path=/; Max-Age={0 if clear else 43200}; HttpOnly; SameSite=Strict'

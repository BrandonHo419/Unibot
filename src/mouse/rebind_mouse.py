import json
import random
import threading
import time

import websocket

from .base_mouse import BaseMouse


class RebindMouse(BaseMouse):
    """Send relative mouse movement and clicks through a Rebind Lua server."""

    label = "Rebind"

    def __init__(self, config):
        self.url = config.rebind_url
        self.ws = None
        self.connected = False
        self._closed = False
        self._send_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._pong_event = threading.Event()
        self._receiver_thread = None

        super().__init__(config)

        try:
            self._connect()
        except Exception:
            self.close()
            raise

    def _connect(self):
        """Open the WebSocket and verify the Lua protocol with ping/pong."""
        self._disconnect()
        self._pong_event.clear()

        ws = websocket.create_connection(
            self.url,
            timeout=self.cfg.rebind_connect_timeout,
            enable_multithread=True,
        )
        ws.settimeout(0.5)

        with self._state_lock:
            self.ws = ws
            self.connected = True

        self._receiver_thread = threading.Thread(
            target=self._receiver_loop,
            args=(ws,),
            name="RebindReceiver",
            daemon=True,
        )
        self._receiver_thread.start()

        self._send_message({"t": "ping"})
        if not self._pong_event.wait(self.cfg.rebind_ping_timeout):
            self._disconnect()
            raise TimeoutError(
                f"Rebind did not return pong within "
                f"{self.cfg.rebind_ping_timeout:g} seconds"
            )

        print(f"Rebind connected ({self.url})")

    def _receiver_loop(self, ws):
        """Receive pong frames and detect when this socket disconnects."""
        try:
            while not self._closed:
                try:
                    raw_message = ws.recv()
                    if raw_message is None or raw_message == "":
                        break

                    try:
                        message = json.loads(raw_message)
                    except (json.JSONDecodeError, TypeError):
                        continue

                    if isinstance(message, dict) and message.get("t") == "pong":
                        self._pong_event.set()
                except websocket.WebSocketTimeoutException:
                    continue
                except websocket.WebSocketConnectionClosedException:
                    break
                except Exception as error:
                    if not self._closed and self.cfg.debug:
                        print(
                            f"({self.label}) Receiver stopped: "
                            f"{type(error).__name__}: {error}"
                        )
                    break
        finally:
            # An older receiver must not clear a newer replacement socket.
            with self._state_lock:
                if self.ws is ws:
                    self.ws = None
                    self.connected = False

    def _send_message(self, message):
        payload = json.dumps(message, separators=(",", ":"))

        with self._send_lock:
            with self._state_lock:
                ws = self.ws
                connected = self.connected

            if not connected or ws is None:
                raise ConnectionError("Rebind WebSocket is not connected")

            try:
                ws.send(payload)
            except Exception:
                with self._state_lock:
                    if self.ws is ws:
                        self.ws = None
                        self.connected = False
                raise

    def _ensure_connected(self):
        if self._closed:
            raise ConnectionError("Rebind mouse has been closed")

        if self.connected and self.ws is not None:
            return

        while not self._closed:
            try:
                self._connect()
                return
            except Exception as error:
                print(f"Rebind reconnect failed: {type(error).__name__}: {error}")
                time.sleep(self.cfg.rebind_reconnect_delay)

        raise ConnectionError("Rebind mouse has been closed")

    def send_click(self, delay_before_click=0):
        time.sleep(delay_before_click)
        self._ensure_connected()

        hold_ms = random.randint(40, 80)
        self._send_message({
            "t": "hid.press",
            "code": "Mouse1",
            "hold_ms": hold_ms,
        })

        if self.cfg.debug:
            print(f"({self.label}) Sent: Click(hold_ms={hold_ms})")

        time.sleep(random.randint(25, 34) / 1000)

    def send_move(self, x, y):
        if x == 0 and y == 0:
            return

        self._ensure_connected()
        self._send_message({
            "t": "hid.move",
            "dx": int(x),
            "dy": int(y),
        })

        if self.cfg.debug:
            print(f"({self.label}) Sent: Move({x}, {y})")

    def _disconnect(self):
        with self._state_lock:
            ws = self.ws
            self.ws = None
            self.connected = False

        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    def close(self):
        if self._closed:
            return

        self._closed = True
        super().close()
        self._disconnect()

        receiver = self._receiver_thread
        if receiver is not None and receiver is not threading.current_thread():
            receiver.join(timeout=1.0)
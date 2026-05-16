import asyncio
import websockets
import json
import threading

class BrowserMonitor:
    def __init__(self, config):
        cfg = config.get("browser_monitor", {})
        self.host = cfg.get("host", "127.0.0.1")
        self.port = cfg.get("port", 8765)
        
        self.browser_violation = False
        self.violation_count = 0
        self.lock = threading.Lock()
        
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._start_server, daemon=True)
        
    def start(self):
        self.thread.start()
        
    def get_results(self):
        with self.lock:
            return {
                "browser_violation": self.browser_violation,
                "violation_count": self.violation_count
            }
            
    # After reading the anomaly, we can reset it if we want it to act as an event, 
    # but temporal engine will just sample the current state.
    def reset_violation(self):
        with self.lock:
            self.browser_violation = False

    async def _handler(self, websocket):
        try:
            async for message in websocket:
                data = json.loads(message)
                event_type = data.get("type")
                
                with self.lock:
                    if event_type in ["blur", "hidden", "fullscreen_exit"]:
                        self.browser_violation = True
                        self.violation_count += 1
                    elif event_type in ["focus", "visible", "fullscreen_enter"]:
                        self.browser_violation = False
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[Browser Monitor] Error: {e}")

    async def _main(self):
        async with websockets.serve(self._handler, self.host, self.port):
            await asyncio.Future()  # run forever

    def _start_server(self):
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._main())
        except Exception as e:
            print(f"[Browser Monitor] Server stopped: {e}")

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread.is_alive():
            self.thread.join()

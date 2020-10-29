import asyncio
import aiohttp
import json
import threading
import websockets
from IPython.display import display, HTML
import ipywidgets as widgets

class NotebookChat(object):
    
    def __init__(self, host="localhost", port=8080, tls=False):
        self.host = host
        self.port = port
        self.http_proto = "https" if tls else "http"
        self.ws_proto = "wss" if tls else "ws"
        self.websocket = None
        self.send_queue = []
        self.running = True
        self.out = widgets.Output()
        self.text = widgets.Text()
        self.button = widgets.Button(description="Send")
        self.button.on_click(self._send_message)
        self.thread = None
        
    def _run_thread(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._run())
        loop.close()
        
    async def _run(self):
        url = await self._connect()
        if url:
            async with websockets.connect(url) as websocket:
                self._display("Connected")   
                self.websocket = websocket
                await asyncio.gather(self._read_messages(), self._send_messages())
        
    async def _connect(self):
        try:
            async with aiohttp.ClientSession() as session:
                proto = "http"
                async with session.post(f"{self.http_proto}://{self.host}:{self.port}/connector/websocket") as resp:
                    data = json.loads(await resp.text())
                    return f"{self.ws_proto}://{self.host}:{self.port}/connector/websocket/{data['socket']}"
        except aiohttp.client_exceptions.ClientConnectorError:
            self.stop() 
                        
    async def _read_messages(self):      
        while self.running:
            try:
                self._display(await self.websocket.recv(), "Opsdroid")
            except(asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                self.stop() 
    
    async def _send_messages(self):
        while self.running:
            try:
                message = self.send_queue.pop()
                await self.websocket.send(message)
                self._display(message, "User")
            except IndexError:
                await asyncio.sleep(0.2)

    def _send_message(self, b):
        if self.text.value:
            self.send_queue.append(self.text.value)
            self.text.value = ""
        
    def _display(self, message, user="System"):
        self.out.append_display_data(HTML(f"<strong>{user}:</strong> {message}"))
        
    def start(self):
        self.running = True
        self.button.disabled = False
        self.text.disabled = False
        display(self.out, widgets.HBox([self.text, self.button]))
        self.thread = threading.Thread(target=self._run_thread)
        self.thread.start()
        
    def stop(self):
        self.out.clear_output()
        self._display("Connection closed")    
        self.running = False
        self.websocket = None
        self.send_queue = []
        self.button.disabled = True
        self.text.disabled = True
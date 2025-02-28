#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple, Union

import evdev
import websockets

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("input-overlay-server")

# Constants for event types
class EventType(str, Enum):
    KEY_PRESSED = "key_pressed"
    KEY_RELEASED = "key_released"
    KEY_TYPED = "key_typed"
    MOUSE_MOVED = "mouse_moved"
    MOUSE_PRESSED = "mouse_pressed"
    MOUSE_RELEASED = "mouse_released"
    MOUSE_CLICKED = "mouse_clicked"
    MOUSE_DRAGGED = "mouse_dragged"
    MOUSE_WHEEL = "mouse_wheel"

class MouseDirection(int, Enum):
    VERTICAL = 3
    HORIZONTAL = 4

# Dataclasses for events
@dataclass
class BaseEvent:
    event_type: str

@dataclass
class KeyboardEvent(BaseEvent):
    keycode: int

@dataclass
class MouseButtonEvent(BaseEvent):
    button: int
    mask: int

@dataclass
class MouseMovementEvent(BaseEvent):
    x: int
    y: int

@dataclass
class MouseWheelEvent(BaseEvent):
    direction: int
    rotation: int

# Type alias for all possible event types
InputEvent = Union[KeyboardEvent, MouseButtonEvent, MouseMovementEvent, MouseWheelEvent]

# Keycode mapping from evdev to libuiohook
# This is a partial mapping - extend as needed
EVDEV_TO_LIBUIOHOOK = {
    # Function keys
    evdev.ecodes.KEY_ESC: 0x0001,    # VC_ESCAPE
    evdev.ecodes.KEY_F1: 0x003b,     # VC_F1
    evdev.ecodes.KEY_F2: 0x003c,     # VC_F2
    evdev.ecodes.KEY_F3: 0x003d,     # VC_F3
    evdev.ecodes.KEY_F4: 0x003e,     # VC_F4
    evdev.ecodes.KEY_F5: 0x003f,     # VC_F5
    evdev.ecodes.KEY_F6: 0x0040,     # VC_F6
    evdev.ecodes.KEY_F7: 0x0041,     # VC_F7
    evdev.ecodes.KEY_F8: 0x0042,     # VC_F8
    evdev.ecodes.KEY_F9: 0x0043,     # VC_F9
    evdev.ecodes.KEY_F10: 0x0044,    # VC_F10
    evdev.ecodes.KEY_F11: 0x0057,    # VC_F11
    evdev.ecodes.KEY_F12: 0x0058,    # VC_F12
    
    # Number row
    evdev.ecodes.KEY_GRAVE: 0x0029,  # VC_BACKQUOTE
    evdev.ecodes.KEY_1: 0x0002,      # VC_1
    evdev.ecodes.KEY_2: 0x0003,      # VC_2
    evdev.ecodes.KEY_3: 0x0004,      # VC_3
    evdev.ecodes.KEY_4: 0x0005,      # VC_4
    evdev.ecodes.KEY_5: 0x0006,      # VC_5
    evdev.ecodes.KEY_6: 0x0007,      # VC_6
    evdev.ecodes.KEY_7: 0x0008,      # VC_7
    evdev.ecodes.KEY_8: 0x0009,      # VC_8
    evdev.ecodes.KEY_9: 0x000a,      # VC_9
    evdev.ecodes.KEY_0: 0x000b,      # VC_0
    evdev.ecodes.KEY_MINUS: 0x000c,  # VC_MINUS
    evdev.ecodes.KEY_EQUAL: 0x000d,  # VC_EQUALS
    evdev.ecodes.KEY_BACKSPACE: 0x000e, # VC_BACKSPACE
    
    # Top row
    evdev.ecodes.KEY_TAB: 0x000f,    # VC_TAB
    evdev.ecodes.KEY_Q: 0x0010,      # VC_Q
    evdev.ecodes.KEY_W: 0x0011,      # VC_W
    evdev.ecodes.KEY_E: 0x0012,      # VC_E
    evdev.ecodes.KEY_R: 0x0013,      # VC_R
    evdev.ecodes.KEY_T: 0x0014,      # VC_T
    evdev.ecodes.KEY_Y: 0x0015,      # VC_Y
    evdev.ecodes.KEY_U: 0x0016,      # VC_U
    evdev.ecodes.KEY_I: 0x0017,      # VC_I
    evdev.ecodes.KEY_O: 0x0018,      # VC_O
    evdev.ecodes.KEY_P: 0x0019,      # VC_P
    evdev.ecodes.KEY_LEFTBRACE: 0x001a,  # VC_OPEN_BRACKET
    evdev.ecodes.KEY_RIGHTBRACE: 0x001b, # VC_CLOSE_BRACKET
    evdev.ecodes.KEY_BACKSLASH: 0x002b,  # VC_BACK_SLASH
    
    # Home row
    evdev.ecodes.KEY_CAPSLOCK: 0x003a,   # VC_CAPS_LOCK
    evdev.ecodes.KEY_A: 0x001e,      # VC_A
    evdev.ecodes.KEY_S: 0x001f,      # VC_S
    evdev.ecodes.KEY_D: 0x0020,      # VC_D
    evdev.ecodes.KEY_F: 0x0021,      # VC_F
    evdev.ecodes.KEY_G: 0x0022,      # VC_G
    evdev.ecodes.KEY_H: 0x0023,      # VC_H
    evdev.ecodes.KEY_J: 0x0024,      # VC_J
    evdev.ecodes.KEY_K: 0x0025,      # VC_K
    evdev.ecodes.KEY_L: 0x0026,      # VC_L
    evdev.ecodes.KEY_SEMICOLON: 0x0027,  # VC_SEMICOLON
    evdev.ecodes.KEY_APOSTROPHE: 0x0028, # VC_QUOTE
    evdev.ecodes.KEY_ENTER: 0x001c,  # VC_ENTER
    
    # Bottom row
    evdev.ecodes.KEY_LEFTSHIFT: 0x002a,  # VC_SHIFT_L
    evdev.ecodes.KEY_Z: 0x002c,      # VC_Z
    evdev.ecodes.KEY_X: 0x002d,      # VC_X
    evdev.ecodes.KEY_C: 0x002e,      # VC_C
    evdev.ecodes.KEY_V: 0x002f,      # VC_V
    evdev.ecodes.KEY_B: 0x0030,      # VC_B
    evdev.ecodes.KEY_N: 0x0031,      # VC_N
    evdev.ecodes.KEY_M: 0x0032,      # VC_M
    evdev.ecodes.KEY_COMMA: 0x0033,  # VC_COMMA
    evdev.ecodes.KEY_DOT: 0x0034,    # VC_PERIOD
    evdev.ecodes.KEY_SLASH: 0x0035,  # VC_SLASH
    evdev.ecodes.KEY_RIGHTSHIFT: 0x0036, # VC_SHIFT_R
    
    # Modifier keys
    evdev.ecodes.KEY_LEFTCTRL: 0x001d,   # VC_CONTROL_L
    evdev.ecodes.KEY_LEFTMETA: 0x0e5b,   # VC_META_L
    evdev.ecodes.KEY_LEFTALT: 0x0038,    # VC_ALT_L
    evdev.ecodes.KEY_SPACE: 0x0039,      # VC_SPACE
    evdev.ecodes.KEY_RIGHTALT: 0x0e38,   # VC_ALT_R
    evdev.ecodes.KEY_RIGHTMETA: 0x0e5c,  # VC_META_R
    evdev.ecodes.KEY_COMPOSE: 0x0e5d,    # VC_CONTEXT_MENU
    evdev.ecodes.KEY_RIGHTCTRL: 0x0e1d,  # VC_CONTROL_R
    
    # Navigation cluster
    evdev.ecodes.KEY_PRINT: 0x0e37,      # VC_PRINTSCREEN
    evdev.ecodes.KEY_SCROLLLOCK: 0x0046, # VC_SCROLL_LOCK
    evdev.ecodes.KEY_PAUSE: 0x0e45,      # VC_PAUSE
    evdev.ecodes.KEY_INSERT: 0x0e52,     # VC_INSERT
    evdev.ecodes.KEY_HOME: 0x0e47,       # VC_HOME
    evdev.ecodes.KEY_PAGEUP: 0x0e49,     # VC_PAGE_UP
    evdev.ecodes.KEY_DELETE: 0x0e53,     # VC_DELETE
    evdev.ecodes.KEY_END: 0x0e4f,        # VC_END
    evdev.ecodes.KEY_PAGEDOWN: 0x0e51,   # VC_PAGE_DOWN
    
    # Arrow keys
    evdev.ecodes.KEY_UP: 0x0e48,         # VC_UP
    evdev.ecodes.KEY_LEFT: 0x0e4b,       # VC_LEFT
    evdev.ecodes.KEY_RIGHT: 0x0e4d,      # VC_RIGHT
    evdev.ecodes.KEY_DOWN: 0x0e50,       # VC_DOWN
    
    # Numpad
    evdev.ecodes.KEY_NUMLOCK: 0x0045,    # VC_NUM_LOCK
    evdev.ecodes.KEY_KPSLASH: 0x0e35,    # VC_KP_DIVIDE
    evdev.ecodes.KEY_KPASTERISK: 0x0037, # VC_KP_MULTIPLY
    evdev.ecodes.KEY_KPMINUS: 0x004a,    # VC_KP_SUBTRACT
    evdev.ecodes.KEY_KPPLUS: 0x004e,     # VC_KP_ADD
    evdev.ecodes.KEY_KPENTER: 0x0e1c,    # VC_KP_ENTER
    evdev.ecodes.KEY_KP1: 0x004f,        # VC_KP_1
    evdev.ecodes.KEY_KP2: 0x0050,        # VC_KP_2
    evdev.ecodes.KEY_KP3: 0x0051,        # VC_KP_3
    evdev.ecodes.KEY_KP4: 0x004b,        # VC_KP_4
    evdev.ecodes.KEY_KP5: 0x004c,        # VC_KP_5
    evdev.ecodes.KEY_KP6: 0x004d,        # VC_KP_6
    evdev.ecodes.KEY_KP7: 0x0047,        # VC_KP_7
    evdev.ecodes.KEY_KP8: 0x0048,        # VC_KP_8
    evdev.ecodes.KEY_KP9: 0x0049,        # VC_KP_9
    evdev.ecodes.KEY_KP0: 0x0052,        # VC_KP_0
    evdev.ecodes.KEY_KPDOT: 0x0053,      # VC_KP_SEPARATOR
}

# Mouse button codes
BTN_LEFT = 0x110
BTN_RIGHT = 0x111
BTN_MIDDLE = 0x112
BTN_SIDE = 0x113
BTN_EXTRA = 0x114

# Mouse button masks
MOUSE_BUTTON_MASKS = {
    BTN_LEFT: 1 << 8,     # VC_BUTTON1
    BTN_RIGHT: 1 << 9,    # VC_BUTTON2
    BTN_MIDDLE: 1 << 10,  # VC_BUTTON3
    BTN_SIDE: 1 << 11,    # VC_BUTTON4
    BTN_EXTRA: 1 << 12,   # VC_BUTTON5
}

class InputServer:
    def __init__(self, host: str = "localhost", port: int = 16899):
        self.host = host
        self.port = port
        self.clients = set()
        self.devices = {}
        self.mouse_button_state = 0  # Current state of mouse buttons
        self.mouse_x = 0             # Current mouse X position
        self.mouse_y = 0             # Current mouse Y position
        self.running = False
        self.current_keyboard_state = set()  # Track pressed keys
    
    async def start(self):
        """Start the WebSocket server and listen for evdev events"""
        self.running = True
        
        # Find keyboard and mouse devices
        await self.find_devices()
        
        if not self.devices:
            logger.error("No input devices found")
            return
        
        # Start WebSocket server
        websocket_server = websockets.serve(self.handle_client, self.host, self.port)
        
        # Create task for each device
        device_tasks = [self.monitor_device(device) for device in self.devices.values()]
        
        # Run everything concurrently
        await asyncio.gather(
            websocket_server,
            *device_tasks
        )
    
    async def find_devices(self):
        """Find keyboard and mouse devices"""
        self.devices = {}
        
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        logger.info(f"Found {len(devices)} input devices")
        
        for device in devices:
            capabilities = device.capabilities()
            
            # Check if device has key events (keyboard/mouse buttons)
            if evdev.ecodes.EV_KEY in capabilities:
                keys = capabilities[evdev.ecodes.EV_KEY]
                
                # Check if device has mouse buttons
                if BTN_LEFT in keys:
                    logger.info(f"Found mouse: {device.name} at {device.path}")
                    self.devices[device.path] = device
                # Check if device has keyboard keys
                elif evdev.ecodes.KEY_A in keys:
                    logger.info(f"Found keyboard: {device.name} at {device.path}")
                    self.devices[device.path] = device
            
            # Check if device has relative events (mouse movement)
            if evdev.ecodes.EV_REL in capabilities:
                logger.info(f"Found mouse (movement): {device.name} at {device.path}")
                self.devices[device.path] = device
    
    async def handle_client(self, websocket):
        """Handle WebSocket client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        
        try:
            # Keep the connection open
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast_event(self, event: InputEvent):
        """Send event to all connected clients"""
        if not self.clients:
            return
            
        # Convert dataclass to dict and then to JSON
        message = json.dumps(asdict(event))
        
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected_clients
    
    async def monitor_device(self, device):
        """Monitor an input device for events"""
        try:
            logger.info(f"Monitoring device: {device.name}")
            async for event in device.async_read_loop():
                if not self.running:
                    break
                
                await self.process_event(event, device)
        except Exception as e:
            logger.error(f"Error monitoring device {device.name}: {e}")
    
    async def process_event(self, event, device):
        """Process an input event from evdev"""
        if event.type == evdev.ecodes.EV_KEY:
            # Keyboard or mouse button event
            code = event.code
            value = event.value  # 0=released, 1=pressed, 2=repeat
            
            # Check if it's a mouse button
            if code in MOUSE_BUTTON_MASKS:
                await self.handle_mouse_button(code, value)
            # Check if it's a keyboard key
            elif code in EVDEV_TO_LIBUIOHOOK:
                await self.handle_keyboard_key(code, value)
        
        elif event.type == evdev.ecodes.EV_REL:
            # Mouse movement or wheel event
            if event.code == evdev.ecodes.REL_X:
                # Mouse X movement
                self.mouse_x += event.value
                await self.broadcast_event(MouseMovementEvent(
                    event_type=EventType.MOUSE_MOVED,
                    x=self.mouse_x,
                    y=self.mouse_y
                ))
            
            elif event.code == evdev.ecodes.REL_Y:
                # Mouse Y movement
                self.mouse_y += event.value
                await self.broadcast_event(MouseMovementEvent(
                    event_type=EventType.MOUSE_MOVED,
                    x=self.mouse_x,
                    y=self.mouse_y
                ))
            
            elif event.code == evdev.ecodes.REL_WHEEL:
                # Vertical mouse wheel
                direction = MouseDirection.VERTICAL
                rotation = 1 if event.value > 0 else -1
                await self.broadcast_event(MouseWheelEvent(
                    event_type=EventType.MOUSE_WHEEL,
                    direction=direction,
                    rotation=rotation
                ))
            
            elif event.code == evdev.ecodes.REL_HWHEEL:
                # Horizontal mouse wheel
                direction = MouseDirection.HORIZONTAL
                rotation = 1 if event.value > 0 else -1
                await self.broadcast_event(MouseWheelEvent(
                    event_type=EventType.MOUSE_WHEEL,
                    direction=direction,
                    rotation=rotation
                ))
    
    async def handle_mouse_button(self, code, value):
        """Handle mouse button events"""
        button_id = code - BTN_LEFT  # Convert to 0-based index
        mask = MOUSE_BUTTON_MASKS[code]
        
        if value == 1:  # Pressed
            self.mouse_button_state |= mask
            await self.broadcast_event(MouseButtonEvent(
                event_type=EventType.MOUSE_PRESSED,
                button=button_id,
                mask=self.mouse_button_state
            ))
        
        elif value == 0:  # Released
            self.mouse_button_state &= ~mask
            await self.broadcast_event(MouseButtonEvent(
                event_type=EventType.MOUSE_RELEASED,
                button=button_id,
                mask=self.mouse_button_state
            ))
    
    async def handle_keyboard_key(self, code, value):
        """Handle keyboard key events"""
        libuiohook_code = EVDEV_TO_LIBUIOHOOK[code]
        
        if value == 1:  # Pressed
            self.current_keyboard_state.add(libuiohook_code)
            await self.broadcast_event(KeyboardEvent(
                event_type=EventType.KEY_PRESSED,
                keycode=libuiohook_code
            ))
        
        elif value == 0:  # Released
            if libuiohook_code in self.current_keyboard_state:
                self.current_keyboard_state.remove(libuiohook_code)
            
            await self.broadcast_event(KeyboardEvent(
                event_type=EventType.KEY_RELEASED,
                keycode=libuiohook_code
            ))
        
        elif value == 2:  # Repeat
            # Some applications may want to know about key repeats
            # You can uncomment this if needed
            # await self.broadcast_event(KeyboardEvent(
            #     event_type=EventType.KEY_TYPED,
            #     keycode=libuiohook_code
            # ))
            pass
    
    def stop(self):
        """Stop the server"""
        self.running = False
        for device in self.devices.values():
            device.close()


async def main():
    """Main entry point for the application"""
    
    # Check if running as root
    if os.geteuid() != 0:
        print("This script needs to be run with root privileges to access input devices.")
        print("Try running with 'sudo python3 input_server.py'")
        sys.exit(1)
    
    server = InputServer()
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())
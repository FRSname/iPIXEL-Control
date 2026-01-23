import asyncio
import time
from enum import Enum
from typing import Optional, Callable, Awaitable, List, Dict
from utils.logger import get_logger

# Import Bluetooth libraries
try:
    from pypixelcolor import Client
    from bleak import BleakScanner
    HAS_BLE = True
except ImportError:
    HAS_BLE = False

logger = get_logger()


class ConnectionState(Enum):
    """Connection states"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ConnectionManager:
    """Manages Bluetooth connection with health monitoring and auto-reconnect"""
    
    def __init__(self, 
                 on_state_change: Optional[Callable[[ConnectionState], None]] = None,
                 on_reconnect_attempt: Optional[Callable[[int], None]] = None,
                 reconnect_callback: Optional[Callable[[], Awaitable[bool]]] = None):
        """
        Initialize connection manager
        
        Args:
            on_state_change: Callback when connection state changes
            on_reconnect_attempt: Callback when reconnection attempt starts (attempt number)
            reconnect_callback: Async callback to perform actual reconnection
        """
        self.state = ConnectionState.DISCONNECTED
        self.device_address: Optional[str] = None
        self.client = None
        
        # Callbacks
        self.on_state_change = on_state_change
        self.on_reconnect_attempt = on_reconnect_attempt
        self.reconnect_callback = reconnect_callback
        
        # Health monitoring
        self.monitoring = False
        self.health_check_interval = 5  # seconds
        self.health_check_task: Optional[asyncio.Task] = None
        
        # Reconnection settings
        self.auto_reconnect_enabled = True
        self.max_reconnect_attempts = 5
        self.reconnect_backoff_base = 2  # seconds
        self.reconnecting = False
        self.reconnect_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.connection_count = 0
        self.reconnection_count = 0
        self.last_connected_time: Optional[float] = None
        self.last_disconnected_time: Optional[float] = None
        
        if not HAS_BLE:
            logger.error("Required Bluetooth libraries (pypixelcolor, bleak) not installed")
            
        logger.info("ConnectionManager initialized")

    async def scan_devices(self, timeout: float = 5.0) -> Dict[str, str]:
        """
        Scan for iPixel LED devices
        
        Returns:
            Dictionary mapping display name to device address
        """
        if not HAS_BLE:
            logger.error("Cannot scan: BLE libraries not installed")
            return {}
            
        logger.info(f"Scanning for devices (timeout={timeout}s)...")
        try:
            devices = await BleakScanner.discover(timeout=timeout)
            ipixel_devices = {}
            for device in devices:
                if device.name and ("LED" in device.name or "BLE" in device.name or "iPixel" in device.name):
                    ipixel_devices[f"{device.name} ({device.address})"] = device.address
            logger.info(f"Scan complete. Found {len(ipixel_devices)} candidate devices.")
            return ipixel_devices
        except Exception as e:
            logger.error(f"Device scan failed: {e}")
            raise

    async def connect(self, address: str) -> bool:
        """
        Connect to a device by address
        
        Args:
            address: Bluetooth device address
            
        Returns:
            True if successful, False otherwise
        """
        if not HAS_BLE:
            logger.error("Cannot connect: BLE libraries not installed")
            return False
            
        self.device_address = address
        self.set_state(ConnectionState.CONNECTING)
        
        try:
            logger.info(f"Connecting to {address}...")
            # Create client
            client = Client(address)
            
            # Perform connection if method exists
            if hasattr(client, 'connect') and callable(client.connect):
                # Check if it's sync or async
                if asyncio.iscoroutinefunction(client.connect):
                    await client.connect()
                else:
                    client.connect()
            
            # Success
            self.set_connection(client, address)
            return True
            
        except Exception as e:
            logger.error(f"Connection to {address} failed: {e}")
            self.set_state(ConnectionState.FAILED)
            raise

    async def disconnect(self) -> bool:
        """Disconnect from current device"""
        if not self.client:
            return True
            
        logger.info(f"Disconnecting from {self.device_address}...")
        try:
            # Stop monitoring first
            if self.monitoring:
                await self.stop_monitoring()
                
            # Perform disconnection if method exists
            if hasattr(self.client, 'disconnect') and callable(self.client.disconnect):
                if asyncio.iscoroutinefunction(self.client.disconnect):
                    await self.client.disconnect()
                else:
                    self.client.disconnect()
            
            self.clear_connection()
            return True
        except Exception as e:
            logger.error(f"Disconnection failed: {e}")
            return False

    
    def set_state(self, new_state: ConnectionState):
        """Update connection state and notify callback"""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            logger.info(f"Connection state: {old_state.value} -> {new_state.value}")
            
            if self.on_state_change:
                self.on_state_change(new_state)
    
    def set_connection(self, client, device_address: str):
        """Set the active connection"""
        self.client = client
        self.device_address = device_address
        self.set_state(ConnectionState.CONNECTED)
        self.connection_count += 1
        self.last_connected_time = time.time()
        logger.info(f"Connection established to {device_address}")
    
    def clear_connection(self):
        """Clear the connection"""
        self.client = None
        self.set_state(ConnectionState.DISCONNECTED)
        self.last_disconnected_time = time.time()
        logger.info("Connection cleared")
    
    async def health_check(self) -> bool:
        """
        Check if connection is healthy
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self.client or self.state != ConnectionState.CONNECTED:
            return False
        
        try:
            # Try to check if client is still connected
            if hasattr(self.client, 'is_connected'):
                if asyncio.iscoroutinefunction(self.client.is_connected):
                    is_connected = await self.client.is_connected()
                else:
                    is_connected = self.client.is_connected()
                return is_connected
            else:
                # Fallback: assume connected if we have a client
                return True
                
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def start_monitoring(self):
        """Start connection health monitoring"""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.health_check_task = asyncio.create_task(self._monitor_loop())
        logger.info("Connection monitoring started")
    
    async def stop_monitoring(self):
        """Stop connection health monitoring"""
        self.monitoring = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
        
        logger.info("Connection monitoring stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        try:
            while self.monitoring:
                if self.state == ConnectionState.CONNECTED:
                    is_healthy = await self.health_check()
                    
                    if not is_healthy:
                        logger.warning("Connection lost - health check failed")
                        self.clear_connection()
                        
                        # Trigger auto-reconnect if enabled
                        if self.auto_reconnect_enabled and not self.reconnecting:
                            asyncio.create_task(self.auto_reconnect())
                
                await asyncio.sleep(self.health_check_interval)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
    
    async def auto_reconnect(self):
        """Attempt to automatically reconnect with exponential backoff"""
        if self.reconnecting:
            logger.warning("Reconnection already in progress")
            return
        
        if not self.device_address:
            logger.warning("Cannot reconnect: no device address stored")
            return
        
        self.reconnecting = True
        self.set_state(ConnectionState.RECONNECTING)
        
        attempt = 0
        while attempt < self.max_reconnect_attempts:
            attempt += 1
            
            # Calculate backoff delay
            delay = min(self.reconnect_backoff_base ** attempt, 32)  # Max 32 seconds
            
            logger.info(f"Reconnection attempt {attempt}/{self.max_reconnect_attempts} in {delay}s")
            
            if self.on_reconnect_attempt:
                self.on_reconnect_attempt(attempt)
            
            await asyncio.sleep(delay)
            
            # Attempt reconnection
            try:
                if self.reconnect_callback:
                    success = await self.reconnect_callback()
                    
                    if success:
                        logger.info(f"Reconnection successful on attempt {attempt}")
                        self.reconnection_count += 1
                        self.reconnecting = False
                        return
                else:
                    logger.warning("No reconnect_callback provided")
                    break
                    
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt} failed: {e}")
        
        # All attempts failed
        logger.error(f"Reconnection failed after {self.max_reconnect_attempts} attempts")
        self.set_state(ConnectionState.FAILED)
        self.reconnecting = False
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        uptime = None
        if self.last_connected_time and self.state == ConnectionState.CONNECTED:
            uptime = time.time() - self.last_connected_time
        
        return {
            "state": self.state.value,
            "device_address": self.device_address,
            "connection_count": self.connection_count,
            "reconnection_count": self.reconnection_count,
            "uptime_seconds": uptime,
            "monitoring": self.monitoring,
        }

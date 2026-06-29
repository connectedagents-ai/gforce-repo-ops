"""
Gripper Hardware Controller
-------------------------------
Abstracts GPIO/hardware control for the OpenClaw gripper.
Supports real hardware (RPi.GPIO) and mock mode for testing.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any


class GripperState:
    """Runtime state of the gripper."""

    def __init__(self) -> None:
        self.position: int = 100  # Start open
        self.force: int = 50
        self.state: str = "open"
        self.temperature_c: float | None = None
        self.last_updated: float = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "position": self.position,
            "force": self.force,
            "temperature_c": self.temperature_c,
            "timestamp": self.last_updated,
        }


class GripperController:
    """
    Controls the OpenClaw gripper hardware.

    On Raspberry Pi: uses RPi.GPIO for servo control.
    In mock mode: simulates responses (for dev/testing).

    Wiring (default):
      - Servo signal → GPIO 18 (PWM)
      - Force sensor → GPIO 24 (analog via MCP3008 SPI)
      - Temperature → I2C (optional)
    """

    SERVO_PIN = 18
    FORCE_SENSOR_PIN = 24

    def __init__(self, mock: bool = False, max_force: int = 80) -> None:
        self.mock = mock
        self.max_force = max_force
        self._state = GripperState()
        self._gpio: Any = None
        self._pwm: Any = None

    async def initialize(self) -> None:
        if self.mock:
            print("🔧 Gripper: MOCK mode — no hardware access")
            return

        try:
            import RPi.GPIO as GPIO  # type: ignore[import-not-found]
            self._gpio = GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.SERVO_PIN, GPIO.OUT)
            self._pwm = GPIO.PWM(self.SERVO_PIN, 50)  # 50Hz servo
            self._pwm.start(0)
            print(f"🔧 Gripper: GPIO initialized (pin {self.SERVO_PIN})")
        except ImportError:
            print("⚠️  RPi.GPIO not available — falling back to mock mode")
            self.mock = True

    async def shutdown(self) -> None:
        if self._pwm:
            self._pwm.stop()
        if self._gpio:
            self._gpio.cleanup()

    def _position_to_duty_cycle(self, position: int) -> float:
        """Convert 0-100 position to servo duty cycle (2.5-12.5%)."""
        return 2.5 + (position / 100.0) * 10.0

    async def _move_servo(self, position: int) -> None:
        """Send PWM signal to servo. Async to not block."""
        if self.mock:
            await asyncio.sleep(0.2)  # Simulate movement time
            return

        duty = self._position_to_duty_cycle(position)
        if self._pwm:
            self._pwm.ChangeDutyCycle(duty)
            await asyncio.sleep(0.5)  # Wait for servo to reach position
            self._pwm.ChangeDutyCycle(0)  # Stop signal to reduce heat

    def _read_temperature(self) -> float | None:
        """Read temperature from I2C sensor (optional)."""
        if self.mock:
            return 24.5  # Mock temperature
        try:
            # Placeholder for real I2C temperature read
            # e.g., using Adafruit CircuitPython library
            return None
        except Exception:
            return None

    async def get_state(self) -> GripperState:
        self._state.temperature_c = self._read_temperature()
        self._state.last_updated = time.time()
        return self._state

    async def open(self) -> GripperState:
        await self._move_servo(100)
        self._state.position = 100
        self._state.state = "open"
        self._state.last_updated = time.time()
        return self._state

    async def close(self, force: int = 50) -> GripperState:
        # Close: move to position 0
        # Real implementation would use force feedback to stop at contact
        await self._move_servo(0)
        self._state.position = 0
        self._state.force = force
        self._state.state = "closed"
        self._state.last_updated = time.time()
        return self._state

    async def move_to(self, position: int) -> GripperState:
        await self._move_servo(position)
        self._state.position = position
        self._state.state = "open" if position > 10 else "closed"
        self._state.last_updated = time.time()
        return self._state

    async def set_force(self, force: int) -> None:
        self._state.force = force

    async def emergency_stop(self) -> None:
        """Immediately stop all movement and release force."""
        if self._pwm:
            self._pwm.ChangeDutyCycle(0)
        # Move to safe open position
        await self.open()
        self._state.state = "emergency_stopped"

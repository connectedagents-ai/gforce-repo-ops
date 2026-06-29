"""
Safety Middleware for Gripper Control
----------------------------------------
Enforces safety constraints on all gripper commands.
Prevents dangerous operations before they reach hardware.
"""

from __future__ import annotations

from fastapi import HTTPException


class SafetyMiddleware:
    """Validates all gripper commands against safety limits."""

    def __init__(self, max_force: int = 80) -> None:
        self.max_force = max_force
        self._emergency_stopped = False

    def validate_force(self, force: int) -> int:
        """Clamp force to safety maximum."""
        if force < 1:
            raise HTTPException(
                status_code=400,
                detail="Force must be at least 1%",
            )
        if force > 100:
            raise HTTPException(
                status_code=400,
                detail="Force cannot exceed 100%",
            )
        if force > self.max_force:
            # Clamp to max instead of rejecting — log warning
            print(f"⚠️  Safety: Force {force}% clamped to max {self.max_force}%")
            return self.max_force
        return force

    def validate_open(self) -> None:
        """Validate an open command."""
        if self._emergency_stopped:
            raise HTTPException(
                status_code=503,
                detail="Emergency stop active. Restart the service to resume.",
            )

    def validate_move(self, position: int) -> None:
        """Validate a move command."""
        if self._emergency_stopped:
            raise HTTPException(
                status_code=503,
                detail="Emergency stop active. Restart the service to resume.",
            )
        if not 0 <= position <= 100:
            raise HTTPException(
                status_code=400,
                detail=f"Position {position}% out of range (0-100)",
            )

    def trigger_emergency_stop(self) -> None:
        """Latch the emergency stop."""
        self._emergency_stopped = True
        print("🛑 EMERGENCY STOP triggered")

    def reset_emergency_stop(self) -> None:
        """Reset the emergency stop latch (requires manual operator confirmation)."""
        self._emergency_stopped = False
        print("✅ Emergency stop cleared")

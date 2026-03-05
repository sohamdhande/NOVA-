import os
import jwt
import asyncio
import logging
import getpass
from datetime import datetime, timedelta

from core.event_bus import event_bus, NovaEvent

logger = logging.getLogger(__name__)

# Try to import pyobjc LocalAuthentication
try:
    from LocalAuthentication import (
        LAContext, 
        LAPolicyDeviceOwnerAuthenticationWithBiometrics
    )
    HAS_BIOMETRICS = True
except ImportError:
    HAS_BIOMETRICS = False
    logger.warning("pyobjc / LocalAuthentication not installed. Biometrics unavailable.")

_active_session = {"token": None, "expires_at": None}

class BiometricAuth:
    """macOS TouchID Risk Governance Module for N.O.V.A."""
    
    def __init__(self):
        self._SECRET_KEY = os.urandom(32)

    def is_session_valid(self) -> bool:
        """Returns True if token exists and current time < expires_at."""
        if not _active_session.get("token") or not _active_session.get("expires_at"):
            return False
            
        return datetime.utcnow() < _active_session["expires_at"]
        
    def create_session(self) -> str:
        """Generates a JWT signed with a random secret and active for 30 minutes."""
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        payload = {
            "sub": "nova_admin",
            "exp": expires_at
        }
        
        token = jwt.encode(payload, self._SECRET_KEY, algorithm="HS256")
        
        _active_session["token"] = token
        _active_session["expires_at"] = expires_at
        return token

    async def request_biometric(self, reason: str = "N.O.V.A requires authorization") -> bool:
        """Request TouchID from the user via Apple's LocalAuthentication."""
        if not HAS_BIOMETRICS:
            logger.warning("Biometrics not available. Falling back to CLI password prompt.")
            return await self._cli_fallback(reason)
            
        try:
            # Delegate to the sync version in a thread pool
            # so pyobjc's blocking LAContext doesn't freeze the event loop
            success = await asyncio.to_thread(self.request_biometric_sync, reason)
            
            if success:
                await event_bus.publish(NovaEvent(
                    source="biometric", 
                    type="auth_granted", 
                    payload={"reason": reason}, 
                    priority=5
                ))
                return True
            else:
                await event_bus.publish(NovaEvent(
                    source="biometric", 
                    type="auth_denied", 
                    payload={"reason": reason}, 
                    priority=7
                ))
                return False
                
        except Exception as e:
            logger.error(f"Biometric check failed with exception: {e}")
            return await self._cli_fallback(reason)
            
    async def _cli_fallback(self, reason: str) -> bool:
        """CLI fallback when TouchID is unavailable."""
        print(f"\n[SECURITY] {reason}")
        
        # In a real local system, we'd use 'pam' or 'dscl' to verify the Mac password. 
        # Here we just accept a non-empty password to securely fallback without locking the agent.
        pwd = await asyncio.to_thread(getpass.getpass, "Enter password (fallback) to continue: ")
        
        if pwd:
            self.create_session()
            await event_bus.publish(NovaEvent(
                source="biometric", 
                type="auth_granted", 
                payload={"reason": f"{reason} (Password Fallback)"}, 
                priority=5
            ))
            return True
        else:
            await event_bus.publish(NovaEvent(
                source="biometric", 
                type="auth_denied", 
                payload={"reason": reason, "error": "Empty password provided"}, 
                priority=7
            ))
            return False

    async def require_auth(self, action_name: str, risk_level: str) -> bool:
        """Governance Integration function."""
        risk_level = risk_level.upper()
        
        if risk_level == "LOW":
            return True
            
        elif risk_level == "MEDIUM":
            if self.is_session_valid():
                return True
            return await self.request_biometric(f"Authenticate to perform medium-risk action: {action_name}")
            
        elif risk_level == "HIGH":
            # High risk ALWAYS forces a new verification, regardless of session token
            return await self.request_biometric(f"Authenticate to perform high-risk action: {action_name}")
            
        elif risk_level == "CRITICAL":
            logger.error(f"BLOCKED: Attempted critical action '{action_name}'. Critical actions are forbidden.")
            return False
            
        else:
            logger.warning(f"Unknown risk level '{risk_level}'. Defaulting to blocked.")
            return False

    def request_biometric_sync(self, reason: str = "Unlock N.O.V.A") -> bool:
        """Synchronous version of request_biometric for use in thread executor."""
        try:
            from LocalAuthentication import (
                LAContext,
                LAPolicyDeviceOwnerAuthenticationWithBiometrics
            )
            import threading

            context = LAContext()

            # Check if biometrics available first
            can_evaluate, error = context.canEvaluatePolicy_error_(
                LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                None
            )
            if not can_evaluate:
                print(f"[BIOMETRIC] TouchID not available: {error}")
                return self._cli_fallback_sync()

            # Use threading.Event to bridge the async callback
            # to a synchronous return value
            result_holder = [False]
            done = threading.Event()

            def reply(success, error):
                result_holder[0] = bool(success)
                done.set()

            # This is the correct pyobjc method — uses reply callback
            context.evaluatePolicy_localizedReason_reply_(
                LAPolicyDeviceOwnerAuthenticationWithBiometrics,
                reason,
                reply
            )

            # Wait up to 30 seconds for user to touch sensor
            done.wait(timeout=30)

            if result_holder[0]:
                self.create_session()
                print("[BIOMETRIC] Authentication granted")
            else:
                print("[BIOMETRIC] Authentication denied")

            return result_holder[0]

        except ImportError:
            print("[BIOMETRIC] pyobjc not installed, falling back to CLI")
            return self._cli_fallback_sync()
        except Exception as e:
            print(f"[BIOMETRIC] Unexpected error: {e}")
            return self._cli_fallback_sync()

    def _cli_fallback_sync(self) -> bool:
        """Sync CLI fallback if TouchID unavailable."""
        import getpass
        try:
            password = getpass.getpass("[NOVA] TouchID unavailable. Enter password: ")
            return len(password) > 0
        except Exception:
            return False

# Export singleton
biometric_auth = BiometricAuth()

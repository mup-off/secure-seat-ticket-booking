"""Two-step verification with time-based one-time passwords (plan, Phase 2: Spoofing).

Works with Google Authenticator, Microsoft Authenticator, Authy and similar apps.
"""
import hmac
import time

import pyotp

STEP_SECONDS = 30


def new_secret():
    return pyotp.random_base32()


def provisioning_uri(secret, email):
    return pyotp.TOTP(secret, interval=STEP_SECONDS).provisioning_uri(name=email, issuer_name="SecureSeat")


def current_counter(now=None):
    return int((time.time() if now is None else now) // STEP_SECONDS)


def code_for_counter(secret, counter):
    return pyotp.TOTP(secret, interval=STEP_SECONDS).generate_otp(counter)


def verify(secret, code, last_counter=0, now=None):
    """Checks the code for the current 30-second step and one step either side
    (clock drift). Returns the matching step number, or None. Steps at or below
    last_counter are refused, so the same code can't be used twice."""
    if not secret or not isinstance(code, str):
        return None
    code = code.replace(" ", "")
    if len(code) != 6 or not code.isdigit():
        return None
    now_counter = current_counter(now)
    for counter in (now_counter - 1, now_counter, now_counter + 1):
        if counter <= last_counter:
            continue
        if hmac.compare_digest(code_for_counter(secret, counter), code):
            return counter
    return None

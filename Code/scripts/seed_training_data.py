"""
Seeds realistic scam and legitimate messages into ScamShield through the
live API, then moderates the numbers (escalate the scam ones, clear the
legitimate ones) — so scripts/train_model.py has enough confirmed labels
to actually train on, without you having to report and moderate dozens of
messages by hand through the app and dashboard first.

Run this with the backend already running, from your project root:

    python scripts/seed_training_data.py

Two honesty notes:

1. This is synthetic seed data, not real reports from real victims. It's
   enough to get the training pipeline and (eventually) the scoring
   integration working end to end — it is NOT a substitute for real
   confirmed reports accumulating over time in an actual deployment.

2. Some of the "legitimate" messages here deliberately reuse words that
   overlap with the existing rule-based scam categories — a real delivery
   OTP, a school "prize giving" ceremony, a real network-provider top-up
   confirmation. Those are the boundary cases that matter most: they're
   exactly the kind of message a keyword-only system risks getting wrong,
   and what a trained model needs to see labeled correctly to learn the
   difference rather than just re-deriving the keyword rules.

One of the "scam" categories below is the network-impersonation / fake
USSD-code pattern that started this whole conversation about adding ML —
seeded here deliberately, since it's the clearest example of a scam that
slips straight past the current keyword categories.
"""

from __future__ import annotations

import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote

API_BASE_URL = os.environ.get("SCAMSHIELD_API_BASE_URL", "http://localhost:8000")
MODERATOR_KEY = os.environ.get("MODERATOR_API_KEY", "change-me-dev-key")

DEVICE_IDS = [f"seed-device-{i:02d}" for i in range(1, 9)]

# Six scam numbers, four message variants each — deliberately spanning
# different tactics rather than four rewordings of the same trick.
SCAM_NUMBER_MESSAGES = {
    "+260970000001": [  # lottery / prize
        "Congratulations! You have won K10,000 in the MTN promo. Send your PIN to 0977000000 to claim your prize now.",
        "You are today's lucky winner of our cash prize draw! Reply with your account number within 24 hours to claim.",
        "URGENT: Your prize of K10,000 expires today. Click http://bit.ly/claim-prize now to claim your winnings.",
        "Jackpot alert! You've been selected for a free gift worth K5,000, claim before midnight or lose it.",
    ],
    "+260970000002": [  # mobile money / payment pressure
        "Your mobile money account will be suspended. Send a small reactivation fee via mobile money to keep your account active.",
        "Dear customer, your account requires urgent verification. Pay a processing fee now or lose access to your funds.",
        "We noticed unusual activity on your account. Transfer the security deposit immediately to avoid suspension.",
        "Your transaction is on hold. Send the release fee now via western union to unlock your funds today.",
    ],
    "+260970000003": [  # sensitive-info phishing
        "Your bank requires you to verify your account. Reply with your card number and CVV immediately to avoid a freeze.",
        "Security alert: confirm your identity by sending your one time password now to prevent unauthorized access.",
        "Your account access will be revoked. Send your password and PIN today to keep it active.",
        "Verify your account now: reply with your account number and OTP or your card will be blocked.",
    ],
    "+260970000004": [  # network impersonation / fake USSD — the motivating example
        "Dial *123# now to activate your free 5GB data bundle from your network provider before midnight.",
        "Your network has selected you for a free airtime bonus. Dial *456# immediately to receive K50 free airtime.",
        "Free bundle alert: dial *789*1# now, offer ends today, don't miss this network promotion.",
        "Special customer offer: dial *111*7# to double your airtime instantly, valid for today only.",
    ],
    "+260970000005": [  # deliberate evasive spelling — tests the char n-grams specifically
        "C0ngratulations! U h4ve w0n a cash prize. Send ur P1N t0day t0 claim, offer end$ s00n!!!",
        "Winner winner!! Send ur pin nw 2 claim ur prize b4 it expires 2day",
        "u r selected 4 free cash gift, snd acc0unt number nw 2 claim b4 deadline",
        "CONGRATS!! U WON!! sen pinn nw 2 clam ur prizee b4 tyme runs out",
    ],
    "+260970000006": [  # stacked signals — multiple tactics in one message
        "URGENT winner notification! Congratulations, you've won a cash prize. Send your PIN and account number via mobile money within 24 hours or forfeit your prize.",
        "Final notice: your account will be suspended today. Verify immediately by sending your OTP, or pay the reactivation fee now.",
        "Act now! Claim your free jackpot gift by sending your card number and CVV before the offer expires tonight.",
        "Congratulations winner! Dial *123# and send your PIN now to claim your urgent cash prize before it expires.",
    ],
}

# Six legitimate numbers — several deliberately chosen as boundary cases
# that share vocabulary with the scam categories above.
CLEAN_NUMBER_MESSAGES = {
    "+260971111001": [  # casual conversation
        "Hey, are we still meeting for lunch tomorrow at 1pm?",
        "Running about 10 minutes late, see you soon!",
        "Thanks for the help earlier, really appreciate it.",
        "Can you send me that document when you get a chance?",
    ],
    "+260971111002": [  # delivery / appointment reminders
        "Your parcel is out for delivery and will arrive between 2pm and 4pm today.",
        "Reminder: your dentist appointment is scheduled for Friday at 9am.",
        "Your order #4521 has been shipped and is expected to arrive within 3 business days.",
        "Your table for 4 is confirmed for 7:30pm tonight, see you then.",
    ],
    "+260971111003": [  # real bank/OTP messages — boundary case
        "Your one-time PIN for login is 483920. Do not share this code with anyone. Valid for 5 minutes.",
        "Your account balance as of today is K2,450.00. Thank you for banking with us.",
        "This is a reminder that your loan repayment of K500 is due on the 15th.",
        "Your OTP for this transaction is 917244. Never share this code, even with bank staff.",
    ],
    "+260971111004": [  # legitimate "prize" / event language — boundary case
        "Reminder: the school prize giving ceremony starts at 10am this Saturday in the main hall.",
        "Congratulations on completing the training program! Your certificate is ready for collection.",
        "The staff raffle winner will be announced at Friday's meeting, good luck to everyone!",
        "Well done on your exam results — congratulations from the whole department.",
    ],
    "+260971111005": [  # real network-provider messages — boundary case
        "Thank you for topping up K50 airtime. Your new balance is K73.20.",
        "Data bundle purchase successful: 1GB added to your account, valid for 30 days.",
        "Your network subscription has been renewed successfully. Enjoy uninterrupted service.",
        "You have used 80% of your monthly data bundle. Top up anytime via the app.",
    ],
    "+260971111006": [  # family / personal
        "Mom, I landed safely, will call you once I'm settled in.",
        "Don't forget to pick up bread on your way home, thanks!",
        "Happy birthday! Hope you have a wonderful day, see you at dinner.",
        "The kids are asking when you'll be back, let me know your ETA.",
    ],
}


def post_json(path: str, payload: dict, headers: dict | None = None) -> dict:
    url = f"{API_BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{e.code} error calling {path}: {body}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Could not reach the API at {API_BASE_URL}{path}. "
            f"Is the backend running? ({e})"
        ) from e


def check_backend_is_up() -> None:
    try:
        with urllib.request.urlopen(f"{API_BASE_URL}/health", timeout=5):
            pass
    except Exception as e:
        print(
            f"Could not reach {API_BASE_URL}/health — start the backend first "
            f"(uvicorn app.main:app --reload) and try again.\n({e})"
        )
        sys.exit(1)


def submit_reports(number_messages: dict[str, list[str]], label: str) -> None:
    for number, messages in number_messages.items():
        for message in messages:
            device_id = random.choice(DEVICE_IDS)
            result = post_json("/reports", {"device_id": device_id, "number": number, "message": message})
            print(f"  [{label}] {number}: score {result['message_score']:>3} -> status {result['status']}")
            time.sleep(0.05)  # light throttling, not load-testing the API


def moderate(number: str, action: str) -> None:
    encoded_number = quote(number, safe="")
    post_json(
        f"/numbers/{encoded_number}/moderate",
        {"action": action},
        headers={"X-Moderator-Key": MODERATOR_KEY},
    )


def main() -> None:
    check_backend_is_up()

    print(f"Seeding against {API_BASE_URL}\n")

    print("Submitting scam reports...")
    submit_reports(SCAM_NUMBER_MESSAGES, "scam")

    print("\nSubmitting legitimate reports...")
    submit_reports(CLEAN_NUMBER_MESSAGES, "clean")

    print("\nConfirming scam numbers as escalated...")
    for number in SCAM_NUMBER_MESSAGES:
        try:
            moderate(number, "escalate")
            print(f"  {number}: escalated")
        except RuntimeError as e:
            print(f"  {number}: FAILED — {e}")
            if "401" in str(e):
                print(
                    "  (401 usually means MODERATOR_API_KEY doesn't match your backend's "
                    "MODERATOR_API_KEY — set the env var before running this script.)"
                )
                sys.exit(1)

    print("\nDismissing legitimate numbers as cleared...")
    for number in CLEAN_NUMBER_MESSAGES:
        try:
            moderate(number, "clear")
            print(f"  {number}: cleared")
        except RuntimeError as e:
            print(f"  {number}: FAILED — {e}")

    total_scam = sum(len(m) for m in SCAM_NUMBER_MESSAGES.values())
    total_clean = sum(len(m) for m in CLEAN_NUMBER_MESSAGES.values())
    print(
        f"\nDone. Seeded {total_scam} scam examples across {len(SCAM_NUMBER_MESSAGES)} numbers "
        f"and {total_clean} legitimate examples across {len(CLEAN_NUMBER_MESSAGES)} numbers.\n"
        f"Run scripts/train_model.py next."
    )


if __name__ == "__main__":
    main()

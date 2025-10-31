# ============================================================
# Air India IVR Backend (Real Calls via Twilio + FastAPI)
# ============================================================

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os

# ============================================================
# Configuration
# ============================================================

# Use environment variables (never hardcode credentials)
TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_PHONE_NUMBER = ""

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI(title="Air India Real IVR", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# IVR Menu Structure
# ============================================================

MENU_STRUCTURE = {
    "main": {
        "prompt": (
            "Welcome to Air India Airlines. "
            "Press 1 for Booking Enquiry. "
            "Press 2 for Flight Status. "
            "Press 3 for Baggage Information. "
            "Press 4 for Refunds. "
            "Press 5 for Flight Cancellation. "
            "Press 6 for Loyalty Program. "
            "Press 7 for Web Check-in. "
            "Press 8 for Special Assistance. "
            "Press 9 to speak with an agent."
        ),
        "options": {
            "1": {"action": "goto_menu", "target": "booking", "message": "Booking Enquiry selected."},
            "2": {"action": "goto_menu", "target": "flight_status", "message": "Flight Status selected."},
            "3": {"action": "end_call", "message": "Baggage Information: Please visit airindia.com/baggage."},
            "4": {"action": "end_call", "message": "Refund policy: Refunds are processed within 7 business days."},
            "5": {"action": "end_call", "message": "Flight cancellation: Please visit airindia.com/manage-booking."},
            "6": {"action": "end_call", "message": "Loyalty program: Join Flying Returns on our website."},
            "7": {"action": "end_call", "message": "Web check-in: Available 48 hours before departure."},
            "8": {"action": "end_call", "message": "Special assistance: Our team will contact you soon."},
            "9": {"action": "transfer_agent", "message": "Transferring to agent."}
        }
    },
    "booking": {
        "prompt": "Press 1 for Domestic Flights. Press 2 for International Flights. Press 0 to go back.",
        "options": {
            "1": {"action": "end_call", "message": "Domestic booking selected. We'll call you back."},
            "2": {"action": "end_call", "message": "International booking. Visit airindia.com."},
            "0": {"action": "goto_menu", "target": "main", "message": "Going back to main menu."}
        }
    },
    "flight_status": {
        "prompt": "Please enter your 6-digit PNR number followed by the pound key.",
        "options": {
            "#": {"action": "lookup_pnr", "message": "Looking up your PNR..."}
        }
    }
}

# ============================================================
# Routes
# ============================================================

@app.get("/")
def health():
    return {"status": "Air India IVR ready", "twilio_number": TWILIO_PHONE_NUMBER}

@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """
    Main Twilio webhook for handling real voice calls.
    Set this as the Voice Webhook URL in your Twilio console.
    """
    form = await request.form()
    digits = form.get("Digits")
    call_sid = form.get("CallSid")

    resp = VoiceResponse()

    # No input yet — play the main menu
    if not digits:
        gather = Gather(input="dtmf", num_digits=1, action="/twilio/voice", method="POST")
        gather.say(MENU_STRUCTURE["main"]["prompt"])
        resp.append(gather)
        resp.redirect("/twilio/voice")  # if user doesn't input anything
        return Response(content=str(resp), media_type="application/xml")

    # Handle input
    main_menu = MENU_STRUCTURE["main"]
    if digits not in main_menu["options"]:
        resp.say("Invalid input. Please try again.")
        resp.redirect("/twilio/voice")
        return Response(content=str(resp), media_type="application/xml")

    option = main_menu["options"][digits]
    action = option["action"]
    message = option["message"]

    if action == "end_call":
        resp.say(message)
        resp.hangup()

    elif action == "transfer_agent":
        resp.say("Please wait while we connect you to an agent.")
        # Replace with real agent number
        resp.dial("+911234567890")

    elif action == "goto_menu":
        # Handle submenus dynamically
        submenu = MENU_STRUCTURE[option["target"]]
        gather = Gather(input="dtmf", num_digits=1, action="/twilio/submenu", method="POST")
        gather.say(submenu["prompt"])
        resp.append(gather)
        resp.redirect("/twilio/submenu")

    else:
        resp.say("Thank you for calling Air India.")
        resp.hangup()

    return Response(content=str(resp), media_type="application/xml")

from fastapi import Body

@app.post("/call/start")
def start_real_call(payload: dict = Body(...)):
    """
    Initiates a real outbound call from Twilio to a phone number,
    connecting them to your IVR system (/twilio/voice).
    """
    to_number = payload.get("to")
    if not to_number:
        return {"error": "Missing 'to' number"}

    try:
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url="https://spindly-monster-7vj45qp4rqjxhrgp9-8080.app.github.dev/twilio/voice"
        )
        return {
            "status": call.status,
            "sid": call.sid,
            "to": to_number,
            "from": TWILIO_PHONE_NUMBER
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/twilio/submenu")
async def twilio_submenu(request: Request):
    """Handles submenu (booking, flight status, etc.)"""
    form = await request.form()
    digits = form.get("Digits")

    resp = VoiceResponse()

    if not digits:
        resp.say("No input detected. Returning to main menu.")
        resp.redirect("/twilio/voice")
        return Response(content=str(resp), media_type="application/xml")

    # Example: handle booking submenu
    if digits == "1":
        resp.say("You selected Domestic booking. We'll call you back. Goodbye.")
        resp.hangup()
    elif digits == "2":
        resp.say("You selected International booking. Please visit airindia.com. Goodbye.")
        resp.hangup()
    elif digits == "0":
        resp.redirect("/twilio/voice")
    else:
        resp.say("Invalid input. Please try again.")
        resp.redirect("/twilio/submenu")

    return Response(content=str(resp), media_type="application/xml")

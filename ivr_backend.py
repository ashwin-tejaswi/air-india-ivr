# ============================================================
# Indian Railways IVR Backend (FastAPI + Twilio Integration)
# ============================================================

from fastapi import FastAPI, Request, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os

# ============================================================
# Configuration
# ============================================================

# 🔹 Replace this with your actual ngrok or deployed URL (no trailing slash)
NGROK_URL = ""

TWILIO_ACCOUNT_SID = ""
TWILIO_AUTH_TOKEN =""
TWILIO_PHONE_NUMBER = ""
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

app = FastAPI(title="Indian Railways IVR", version="2.0.0")

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
            "Welcome to Indian Railways Booking Assistance. "
            "Press 1 for Ticket Booking. "
            "Press 2 for PNR Status Enquiry. "
            "Press 3 for Train Schedule. "
            "Press 4 for Fare Enquiry. "
            "Press 5 for Ticket Cancellation. "
            "Press 6 for Refund Information. "
            "Press 7 for Tatkal Booking Information. "
            "Press 8 for Special Assistance. "
            "Press 9 to speak with a customer care agent."
        ),
        "options": {
            "1": {"action": "goto_menu", "target": "booking", "message": "Ticket Booking selected."},
            "2": {"action": "goto_menu", "target": "pnr_status", "message": "PNR Status Enquiry selected."},
            "3": {"action": "end_call", "message": "For Train Schedule, please visit IRCTC dot co dot in or use the Rail Connect App."},
            "4": {"action": "end_call", "message": "For fare enquiry, please visit IRCTC dot co dot in or use the IRCTC app."},
            "5": {"action": "end_call", "message": "Ticket cancellation can be done on IRCTC under My Bookings."},
            "6": {"action": "end_call", "message": "Refunds are processed within five to seven working days."},
            "7": {"action": "end_call", "message": "Tatkal booking opens one day in advance at ten A M for A C and eleven A M for non A C classes."},
            "8": {"action": "end_call", "message": "For special assistance, our representative will reach out to you shortly."},
            "9": {"action": "transfer_agent", "message": "Transferring your call to an agent."}
        }
    },
    "booking": {
        "prompt": (
            "Press 1 for General Quota Booking. "
            "Press 2 for Tatkal Booking. "
            "Press 3 for Ladies Quota Booking. "
            "Press 0 to return to the main menu."
        ),
        "options": {
            "1": {"action": "end_call", "message": "General quota booking selected. Our agent will call you shortly."},
            "2": {"action": "end_call", "message": "Tatkal booking selected. Please ensure you have valid ID proof ready."},
            "3": {"action": "end_call", "message": "Ladies quota booking selected. Our team will assist you soon."},
            "0": {"action": "goto_menu", "target": "main", "message": "Returning to main menu."}
        }
    },
    "pnr_status": {
        "prompt": "Please enter your 10-digit PNR number followed by the pound key.",
        "options": {
            "#": {"action": "lookup_pnr", "message": "Checking your PNR status. Please wait."}
        }
    }
}

# ============================================================
# Routes
# ============================================================

@app.get("/")
def health():
    """Health check endpoint"""
    return {
        "status": "Indian Railways IVR running",
        "twilio_number": TWILIO_PHONE_NUMBER,
        "ngrok_url": NGROK_URL
    }

# -------------------------------
# Main Twilio Webhook for Calls
# -------------------------------
@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """Handles the initial IVR menu"""
    form = await request.form()
    digits = form.get("Digits")
    call_sid = form.get("CallSid")

    print(f"📞 Incoming request to /twilio/voice — Call SID: {call_sid}, Digits: {digits}")

    resp = VoiceResponse()

    # Step 1: No input yet — start menu
    if not digits:
        gather = Gather(
            input="dtmf",
            num_digits=1,
            action=f"",
            method="POST"
        )
        gather.say(MENU_STRUCTURE["main"]["prompt"])
        resp.append(gather)
        resp.redirect(f"")
        return Response(content=str(resp), media_type="application/xml")

    main_menu = MENU_STRUCTURE["main"]

    # Step 2: Process menu input
    if digits not in main_menu["options"]:
        resp.say("Invalid input. Please try again.")
        resp.redirect(f"{NGROK_URL}/twilio/voice")
        return Response(content=str(resp), media_type="application/xml")

    option = main_menu["options"][digits]
    action = option["action"]
    message = option["message"]

    if action == "end_call":
        resp.say(message)
        resp.hangup()

    elif action == "transfer_agent":
        resp.say("Please hold while we connect you to an available customer service representative.")
        resp.dial("+911234567890")  # 🔹 Replace with your agent number

    elif action == "goto_menu":
        submenu = MENU_STRUCTURE[option["target"]]
        gather = Gather(
            input="dtmf",
            num_digits=1,
            action=f"{NGROK_URL}/twilio/submenu?menu={option['target']}",
            method="POST"
        )
        gather.say(submenu["prompt"])
        resp.append(gather)
        resp.redirect(f"{NGROK_URL}/twilio/submenu?menu={option['target']}")

    else:
        resp.say("Thank you for calling Indian Railways.")
        resp.hangup()

    return Response(content=str(resp), media_type="application/xml")

# -------------------------------
# Submenus (Booking, PNR Status)
# -------------------------------
@app.post("/twilio/submenu")
async def twilio_submenu(request: Request, menu: str = "booking"):
    """Handles submenu interactions"""
    form = await request.form()
    digits = form.get("Digits")
    print(f"📞 Submenu request for {menu}, Digits: {digits}")

    resp = VoiceResponse()
    submenu = MENU_STRUCTURE.get(menu)

    if not digits:
        resp.say("No input detected. Returning to main menu.")
        resp.redirect(f"{NGROK_URL}/twilio/voice")
        return Response(content=str(resp), media_type="application/xml")

    # Handle booking submenu
    if menu == "booking":
        if digits == "1":
            resp.say("General quota booking selected. Our team will reach out to assist you. Goodbye.")
            resp.hangup()
        elif digits == "2":
            resp.say("Tatkal booking selected. Please ensure valid ID proof is available. Goodbye.")
            resp.hangup()
        elif digits == "3":
            resp.say("Ladies quota booking selected. Our team will contact you soon. Goodbye.")
            resp.hangup()
        elif digits == "0":
            resp.redirect(f"{NGROK_URL}/twilio/voice")
        else:
            resp.say("Invalid input. Please try again.")
            resp.redirect(f"{NGROK_URL}/twilio/submenu?menu=booking")

    elif menu == "pnr_status":
        if digits == "#":
            resp.say("Your PNR 1234567890 is confirmed. The train is running on time. Thank you for calling Indian Railways.")
            resp.hangup()
        else:
            resp.say(f"You entered {digits}. Continue entering your PNR, followed by the pound key.")
            resp.redirect(f"{NGROK_URL}/twilio/submenu?menu=pnr_status")

    return Response(content=str(resp), media_type="application/xml")

# -------------------------------
# Outbound Call API
# -------------------------------
@app.post("/call/start")
def start_real_call(payload: dict = Body(...)):
    """Initiates an outbound call via Twilio"""
    to_number = payload.get("to")
    if not to_number:
        return {"error": "Missing 'to' number"}

    try:
        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{NGROK_URL}/twilio/voice"
        )
        print(f"📞 Outbound call started — SID: {call.sid}, To: {to_number}")
        return {
            "status": call.status,
            "sid": call.sid,
            "to": to_number,
            "from": TWILIO_PHONE_NUMBER
        }
    except Exception as e:
        print("❌ Twilio call error:", e)
        return {"error": str(e)}

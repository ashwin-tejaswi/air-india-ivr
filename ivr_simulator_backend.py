# ============================================================
# Air India IVR Simulator Backend (FastAPI + Twilio Integration)
# ============================================================

from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import random
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

# ========s====================================================
# Initialize App
# ============================================================

app = FastAPI(title="Air India IVR Backend with Twilio", version="2.0.0")

# Enable CORS for frontend or test clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Twilio Configuration
# ============================================================

# Replace with your Twilio credentials from https://www.twilio.com/console
TWILIO_ACCOUNT_SID = "YOUR_TWILIO_ACCOUNT_SID"
TWILIO_AUTH_TOKEN = "YOUR_TWILIO_AUTH_TOKEN"
TWILIO_PHONE_NUMBER = "+1XXXXXXXXXX"  # e.g. "+14155552671"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ============================================================
# Data Models
# ============================================================

class CallStart(BaseModel):
    caller_number: str
    call_id: Optional[str] = None

class DTMFInput(BaseModel):
    call_id: str
    digit: str

class CallLog(BaseModel):
    call_id: str
    caller_number: str
    start_time: str
    end_time: Optional[str] = None
    duration: Optional[int] = None
    menu_path: List[str] = []
    inputs: List[str] = []

# ============================================================
# Storage
# ============================================================

active_calls = {}
call_history = []

# ============================================================
# Menu Structure
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
        "prompt": "Please enter your 6-digit PNR number followed by hash (#).",
        "options": {
            "#": {"action": "lookup_pnr", "message": "Looking up your PNR..."}
        }
    }
}

# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "IVR Backend with Twilio running",
        "active_calls": len(active_calls),
        "total_calls": len(call_history)
    }

# -------------------------------
# 1️⃣ Start Simulated IVR Call
# -------------------------------
@app.post("/ivr/start")
def start_call(call_data: CallStart):
    call_id = f"CALL_{random.randint(100000, 999999)}"
    active_calls[call_id] = {
        "call_id": call_id,
        "caller_number": call_data.caller_number,
        "start_time": datetime.now().isoformat(),
        "current_menu": "main",
        "menu_path": ["main"],
        "inputs": [],
        "pnr_buffer": ""
    }
    print(f"\n📞 New simulated call started: {call_id} from {call_data.caller_number}")
    return {
        "call_id": call_id,
        "status": "connected",
        "prompt": MENU_STRUCTURE["main"]["prompt"]
    }

# -------------------------------
# 2️⃣ DTMF Handler (Simulated)
# -------------------------------
@app.post("/ivr/dtmf")
def handle_dtmf(input_data: DTMFInput):
    call_id = input_data.call_id
    digit = input_data.digit
    if call_id not in active_calls:
        raise HTTPException(status_code=404, detail="Call not found")

    call = active_calls[call_id]
    current_menu = call["current_menu"]
    call["inputs"].append(digit)
    menu = MENU_STRUCTURE.get(current_menu)

    # Handle PNR collection
    if current_menu == "flight_status" and digit != "#":
        call["pnr_buffer"] += digit
        if len(call["pnr_buffer"]) < 6:
            return {
                "status": "collecting",
                "prompt": f"You entered {digit}. Continue entering PNR.",
                "collected": call["pnr_buffer"]
            }

    if digit not in menu["options"]:
        return {
            "status": "invalid",
            "prompt": "Invalid option. Please try again.",
            "valid_options": list(menu["options"].keys())
        }

    option = menu["options"][digit]
    action = option["action"]
    message = option["message"]
    response = {"status": "processed", "message": message}

    if action == "goto_menu":
        target = option["target"]
        call["current_menu"] = target
        call["menu_path"].append(target)
        response["prompt"] = MENU_STRUCTURE[target]["prompt"]

    elif action == "end_call":
        call["end_time"] = datetime.now().isoformat()
        call_history.append(call.copy())
        del active_calls[call_id]
        response["status"] = "call_ended"
        response["call_action"] = "hangup"

    elif action == "transfer_agent":
        call["end_time"] = datetime.now().isoformat()
        call_history.append(call.copy())
        del active_calls[call_id]
        response["status"] = "transferring"
        response["call_action"] = "transfer"

    elif action == "lookup_pnr":
        pnr = call["pnr_buffer"]
        if len(pnr) == 6:
            response["status"] = "pnr_found"
            response["pnr_info"] = {
                "pnr": pnr,
                "flight": "AI101",
                "status": "Confirmed",
                "route": "Mumbai to Delhi"
            }
            response["message"] = f"Your PNR {pnr} is confirmed. Flight AI101 from Mumbai to Delhi."
        else:
            response["status"] = "invalid_pnr"
            response["message"] = "Invalid PNR. Please try again."
            call["pnr_buffer"] = ""

    print(f"✅ Action: {action} — {message}")
    return response

# -------------------------------
# 3️⃣ Twilio Webhook (Real Call Handling)
# -------------------------------
@app.post("/twilio/voice")
async def twilio_voice(request: Request):
    """
    Twilio webhook for handling real IVR calls.
    Set this URL as Voice Webhook in your Twilio phone number settings.
    """
    form = await request.form()
    digits = form.get("Digits")
    call_sid = form.get("CallSid")

    resp = VoiceResponse()

    # New call — no digits yet
    if not digits:
        gather = Gather(
            input="dtmf",
            num_digits=1,
            action="/twilio/voice",
            method="POST"
        )
        gather.say(MENU_STRUCTURE["main"]["prompt"])
        resp.append(gather)
        resp.redirect("/twilio/voice")
        return Response(content=str(resp), media_type="application/xml")

    # Handle digit input
    if digits in MENU_STRUCTURE["main"]["options"]:
        opt = MENU_STRUCTURE["main"]["options"][digits]
        action = opt["action"]
        message = opt["message"]

        if action == "end_call":
            resp.say(message)
            resp.hangup()
        elif action == "transfer_agent":
            resp.say("Please wait while we connect you to an agent.")
            # Replace with real agent number if needed
            resp.dial("+911234567890")
        elif action == "goto_menu":
            resp.say(MENU_STRUCTURE[opt["target"]]["prompt"])
            resp.hangup()
        else:
            resp.say("Thank you for calling Air India.")
            resp.hangup()
    else:
        resp.say("Invalid input. Please try again.")
        resp.redirect("/twilio/voice")

    return Response(content=str(resp), media_type="application/xml")

# -------------------------------
# 4️⃣ End Call
# -------------------------------
@app.post("/ivr/end")
def end_call(call_id: str):
    if call_id in active_calls:
        call = active_calls.pop(call_id)
        call["end_time"] = datetime.now().isoformat()
        call_history.append(call)
        return {"status": "ended", "call_id": call_id}
    return {"status": "not_found", "call_id": call_id}




# ivr_simulator_backend.py



# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from typing import Optional, List
# from datetime import datetime
# import random

# app = FastAPI(title="IVR Simulator Backend", version="1.0.0")

# # Enable CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ==================== DATA MODELS ====================

# class CallStart(BaseModel):
#     caller_number: str
#     call_id: Optional[str] = None

# class DTMFInput(BaseModel):
#     call_id: str
#     digit: str


# class CallLog(BaseModel):
#     call_id: str
#     caller_number: str
#     start_time: str
#     end_time: Optional[str] = None
#     duration: Optional[int] = None
#     menu_path: List[str] = []
#     inputs: List[str] = []

# # ==================== IN-MEMORY STORAGE ====================

# # Active calls
# active_calls = {}

# # Call history
# call_history = []

# # Menu definitions
# MENU_STRUCTURE = {
#     "main": {
#         "prompt": "Welcome to Air India Airlines. Press 1 for Booking Enquiry. Press 2 for Flight Status. Press 9 to speak with an agent.",
#         "options": {
#             "1": {"action": "goto_menu", "target": "booking", "message": "You selected Booking Enquiry."},
#             "2": {"action": "goto_menu", "target": "flight_status", "message": "You selected Flight Status."},
#             "9": {"action": "transfer_agent", "message": "Transferring to agent."}
#         }
#     },
#     "booking": {
#         "prompt": "Press 1 for Domestic Flights. Press 2 for International Flights. Press 0 to go back.",
#         "options": {
#             "1": {"action": "end_call", "message": "Domestic booking selected. We'll call you back."},
#             "2": {"action": "end_call", "message": "International booking. Visit airindia.com."},
#             "0": {"action": "goto_menu", "target": "main", "message": "Going back to main menu."}
#         }
#     },
#     "flight_status": {
#         "prompt": "Please enter your 6-digit PNR number followed by hash.",
#         "options": {
#             "#": {"action": "lookup_pnr", "message": "Looking up your PNR..."}
#         }
#     }
# }

# # ==================== ENDPOINTS ====================

# @app.get("/")
# def root():
#     """Health check"""
#     return {
#         "status": "IVR Simulator Running",
#         "active_calls": len(active_calls),
#         "total_calls": len(call_history)
#     }

# @app.post("/ivr/start")
# def start_call(call_data: CallStart):
#     """
#     Simulate incoming call
    
#     This would be triggered by ACS/Twilio in real system
#     Here we simulate it with web interface
#     """
    
#     call_id = f"CALL_{random.randint(100000, 999999)}"
    
#     # Create call session
#     active_calls[call_id] = {
#         "call_id": call_id,
#         "caller_number": call_data.caller_number,
#         "start_time": datetime.now().isoformat(),
#         "current_menu": "main",
#         "menu_path": ["main"],
#         "inputs": [],
#         "pnr_buffer": ""
#     }
    
#     print(f"\n📞 NEW CALL: {call_id} from {call_data.caller_number}")
    
#     # Return welcome message
#     return {
#         "call_id": call_id,
#         "status": "connected",
#         "prompt": MENU_STRUCTURE["main"]["prompt"]
#     }

# @app.post("/ivr/dtmf")
# def handle_dtmf(input_data: DTMFInput):
#     """
#     Process DTMF key press
    
#     This is the core IVR logic - same as ACS/Twilio would do
#     """
    
#     call_id = input_data.call_id
#     digit = input_data.digit
    
#     # Check if call exists
#     if call_id not in active_calls:
#         raise HTTPException(status_code=404, detail="Call not found")
    
#     call = active_calls[call_id]
#     current_menu = call["current_menu"]
    
#     # Log input
#     call["inputs"].append(digit)
    
#     print(f"\n🔢 DTMF INPUT: Call {call_id}, Menu: {current_menu}, Digit: {digit}")
    
#     # Get menu definition
#     menu = MENU_STRUCTURE.get(current_menu)
#     if not menu:
#         return {"error": "Invalid menu state"}
    
#     # Special handling for PNR input
#     if current_menu == "flight_status" and digit != "#":
#         call["pnr_buffer"] += digit
#         if len(call["pnr_buffer"]) < 6:
#             return {
#                 "status": "collecting",
#                 "prompt": f"You entered {digit}. Continue entering PNR.",
#                 "collected": call["pnr_buffer"]
#             }
    
#     # Check if digit is valid option
#     if digit not in menu["options"]:
#         return {
#             "status": "invalid",
#             "prompt": "Invalid option. Please try again.",
#             "current_menu": current_menu,
#             "valid_options": list(menu["options"].keys())
#         }
    
#     # Get action for this option
#     option = menu["options"][digit]
#     action = option["action"]
#     message = option["message"]
    
#     response = {
#         "status": "processed",
#         "message": message
#     }
    
#     # Execute action
#     if action == "goto_menu":
#         target_menu = option["target"]
#         call["current_menu"] = target_menu
#         call["menu_path"].append(target_menu)
#         response["current_menu"] = target_menu
#         response["prompt"] = MENU_STRUCTURE[target_menu]["prompt"]
        
#     elif action == "end_call":
#         response["status"] = "call_ended"
#         response["call_action"] = "hangup"
#         # Move call to history
#         call["end_time"] = datetime.now().isoformat()
#         call_history.append(call.copy())
#         del active_calls[call_id]
        
#     elif action == "transfer_agent":
#         response["status"] = "transferring"
#         response["call_action"] = "transfer"
#         call["end_time"] = datetime.now().isoformat()
#         call_history.append(call.copy())
#         del active_calls[call_id]
        
#     elif action == "lookup_pnr":
#         pnr = call["pnr_buffer"]
#         if len(pnr) == 6:
#             # Mock PNR lookup
#             response["status"] = "pnr_found"
#             response["pnr_info"] = {
#                 "pnr": pnr,
#                 "flight": "AI101",
#                 "status": "Confirmed",
#                 "route": "Mumbai to Delhi"
#             }
#             response["message"] = f"Your PNR {pnr} is confirmed. Flight AI101 from Mumbai to Delhi."
#             response["call_action"] = "hangup"
#             call["end_time"] = datetime.now().isoformat()
#             call_history.append(call.copy())
#             del active_calls[call_id]
#         else:
#             response["status"] = "invalid_pnr"
#             response["message"] = "Invalid PNR. Please try again."
#             call["pnr_buffer"] = ""
    
#     print(f"✅ ACTION: {action} - {message}")
    
#     return response

# @app.post("/ivr/end")
# def end_call(call_id: str):
#     """End call (user hung up)"""

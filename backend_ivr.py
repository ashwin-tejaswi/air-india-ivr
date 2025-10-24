# ======================================================
# Air India Customer Support IVR Backend (FastAPI + Twilio)
# ======================================================

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather


app = FastAPI(title="Air India IVR Backend")

# ==============================================
# Twilio Configuration
# ==============================================
TWILIO_ACCOUNT_SID =   "xxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_here"    #placeholder for security

TWILIO_PHONE_NUMBER = "+12196005841"             

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ==============================================
# Root Endpoint
# ==============================================
@app.get("/")
def read_root() -> dict:
    return {
        "status": "IVR system is running",
        "active_calls": 0,
        "platform": "Twilio + FastAPI"
    }

# ==============================================
# Basic Menus
# ==============================================
@app.get("/home")
def first_home() -> dict:
    return {
        "message": "Welcome to Air India Customer Support IVR. "
                   "Press 1 for Main Menu, Press 2 for Booking Menu."
    }

@app.get("/booking_menu")
def booking_menu() -> dict:
    return {
        "menu": "Booking Menu",
        "options": ["1. Domestic", "2. International"]
    }

@app.get("/status_menu")
def status_menu() -> dict:
    return {
        "menu": "Status Menu",
        "options": ["Enter the flight ID to check the status"]
    }

@app.get("/domestic_booking")
def domestic_booking() -> dict:
    return {"message": "Domestic booking flow started"}

@app.get("/international_booking")
def international_booking() -> dict:
    return {"message": "International booking flow started"}


class BookingMenu(BaseModel):
    booking_id: str
    trans_id: str
    passenger_fullname: str
    passenger_contact: str

booking_db = []

@app.post("/handle-key")
def handle_key(Digits: str = "", menu: str = "main-menu") -> dict:
    if menu == "main-menu":
        if Digits == "1":
            return booking_menu()
        elif Digits == "2":
            return status_menu()
    elif menu == "booking-menu":
        if Digits == "1":
            return domestic_booking()
        elif Digits == "2":
            return international_booking()
    raise HTTPException(status_code=400, detail="Invalid input")

# ==============================================
# Update Booking
# ==============================================
@app.put("/update_booking/{booking_id}")
def update_booking(booking_id: str, details: BookingMenu) -> dict:
    return {
        "message": f"Booking {booking_id} updated successfully",
        "data": details
    }

# ==============================================
# Flight Info & Status
# ==============================================
flights = [
    {"flight_id": "AI1", "origin": "Mumbai", "destination": "Chennai", "status": "Confirmed"},
    {"flight_id": "AI2", "origin": "Chennai", "destination": "Kochi", "status": "Delayed"},
    {"flight_id": "AI3", "origin": "Delhi", "destination": "Mumbai", "status": "Cancelled"},
    {"flight_id": "AI4", "origin": "Kochi", "destination": "Bengaluru", "status": "Confirmed"},
    {"flight_id": "AI5", "origin": "Hyderabad", "destination": "Goa", "status": "Delayed"}
]

@app.get("/flight/{flight_id}")
def get_flight(flight_id: str) -> dict:
    for f in flights:
        if f["flight_id"] == flight_id:
            return {"flight_id": flight_id, "status": f["status"]}
    raise HTTPException(status_code=404, detail="Flight not found")

@app.get("/status/{flight_id}")
def get_flight_status(flight_id: str) -> dict:
    for f in flights:
        if f["flight_id"] == flight_id:
            return {
                "status": f["status"],
                "origin": f["origin"],
                "destination": f["destination"]
            }
    raise HTTPException(status_code=404, detail="Flight not found")

@app.get("/active_flights")
def active_flights() -> dict:
    return {"active_flights": flights}

# ==============================================
# Cancel Booking
# ==============================================
@app.delete("/cancel_flight/{booking_id}")
def cancel_booking(booking_id: str) -> dict:
    for b in booking_db:
        if b["booking_id"] == booking_id:
            booking_db.remove(b)
            return {"message": "Booking cancelled successfully"}
    raise HTTPException(status_code=404, detail="Booking not found")

# ==============================================
# Error Handling and Logging
# ==============================================
logging.basicConfig(level=logging.INFO)

@app.exception_handler(Exception)
def handle_exceptions(request, exc):
    logging.error(f"Error occurred: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# ==============================================
# IVR Session Management
# ==============================================
call_sessions = {}

@app.post("/ivr/step1")
def step1(call_id: str, origin: str) -> dict:
    call_sessions[call_id] = {"origin": origin}
    return {"message": "Origin saved. Please provide destination."}

@app.post("/ivr/step2")
def step2(call_id: str, destination: str) -> dict:
    session = call_sessions.get(call_id)
    if not session:
        raise HTTPException(status_code=400, detail="Session not found")

    session["destination"] = destination
    return {
        "message": f"You are flying from {session['origin']} to {session['destination']}"
    }

@app.post("/twilio_ivr")
async def twilio_ivr(request: Request):
    """Handle incoming calls from Twilio"""
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio_process_choice", method="POST")
    gather.say("Welcome to Air India IVR. Press 1 for flight status, 2 for booking.", voice="Polly.Aditi")
    response.append(gather)
    response.redirect("/twilio_ivr")
    return Response(content=str(response), media_type="application/xml")

@app.post("/twilio_process_choice")
async def twilio_process_choice(request: Request):
    form = await request.form()
    digits = form.get("Digits")
    response = VoiceResponse()
    if digits == "1":
        response.say("Your flight AI 202 from Delhi to Mumbai is on time.")
    elif digits == "2":
        response.say("Please visit Air India dot com to book tickets.")
    else:
        response.say("Invalid choice. Redirecting to main menu.")
        response.redirect("/twilio_ivr")
    return Response(content=str(response), media_type="application/xml")


"""
from azure.communication.callautomation import (
    CallAutomationClient,
    RecognizeInputType,
    RecognizeDtmfOptions,
    DtmfTone,
    TextSource
)
from azure.core.credentials import AzureKeyCredential

ACS_CONNECTION_STRING = " "
ACS_PHONE_NUMBER = "+1234567890"
CALLBACK_URI = " "

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
active_calls = {}

def create_voice_prompt(text: str):
    return TextSource(text=text, voice_name="en-IN-NeerjaNeural")
"""

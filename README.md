# air-india-ivr
# Air India IVR Backend

## Overview
This is the backend for the Air India Customer Support IVR project. 
It acts as a middleware/API layer connecting calls to the conversational AI stack.  
The backend is implemented using **FastAPI** and supports **Twilio integration** for handling calls and DTMF inputs.

---

## Twilio Configuration 

```python
TWILIO_ACCOUNT_SID = "xxxxxxxxxxxxx"  # Safe to include
TWILIO_AUTH_TOKEN = "YOUR_AUTH_TOKEN"             # Placeholder, do not push real token
TWILIO_PHONE_NUMBER =" +12196005841"             # Safe to include


          +------------------+
          | Caller / Customer|
          +--------+---------+
                   |
                   v
          +--------+---------+
          |   Twilio Cloud   |
          | (Handles Call)   |
          +--------+---------+
                   |
          HTTP POST /twilio_ivr
                   |
                   v
          +--------+---------+
          | FastAPI Backend  |
          | - /twilio_ivr    |
          | - /twilio_process_choice
          | - /handle-key
          | - /ivr/step1, step2
          +--------+---------+
                   |
         Flight info / Booking DB
                   |
                   v
          +--------+---------+
          | Backend Response |
          | - TwiML Voice    |
          +-----------------+


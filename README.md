Air India IVR Simulator
Project Overview

This is a simulated IVR (Interactive Voice Response) system for Air India Customer Support.
It is built using FastAPI for the backend and a simple HTML/JS frontend to simulate calls.
This simulator does not require Twilio or Azure Communication Services, and allows testing IVR flows directly in a browser.

Features

Start a simulated call by entering a phone number.

Navigate a menu using on-screen DTMF buttons.

Handles main menu options:

Booking Enquiry

Flight Status

Transfer to Agent

Collects 6-digit PNR and returns a mock flight status.

Call session management with logs.

Frontend communicates with backend via API.

Files

index.html – Frontend interface with keypad and call simulation.

ivr_simulator_backend.py – FastAPI backend handling IVR logic and calls.

README.md – Project overview and instructions.
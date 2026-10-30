#!/usr/bin/env python3
"""
=============================================================================
GL BAJAJ - College Portal Complete Backend & SQLite Database Server
=============================================================================
Features:
- Full RESTful API with SQLite persistence
- Token-based Authentication & Session Management
- Role-based Accounts (Students, Faculty, Staff / Admin, Others)
- Campus Geolocation & Distance Calculation API (GPS coordinates)
- Floor Plan & Elevator Routing Services (Lifts A, B, C)
- Campus Events & Notice Board System
- Student Contact & Helpdesk Inquiries
- Production-ready Static Asset Serving
=============================================================================
"""

import os
import sys
import json
import sqlite3
import hashlib
import secrets
import math
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database.db")

# Campus Reference Coordinates: GL Bajaj, Knowledge Park III, Greater Noida
CAMPUS_COORDS = {"lat": 28.4727, "lng": 77.4891}

# ---------------------------------------------------------------------------
# Database Initialization & Seeding
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def haversine_distance_meters(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two GPS coordinates using Haversine formula."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 1)

# ---------------------------------------------------------------------------
# Campus Wayfinding Master Locations Catalog & Route Engine
# ---------------------------------------------------------------------------
CAMPUS_LOCATIONS = [
    # Entrances & Landmarks
    {
        "id": "mainGate",
        "name": "Main Campus Gate (Knowledge Park III)",
        "category": "Gate / Entrance",
        "block": "Campus Perimeter",
        "floor": 0,
        "lat": 28.4720,
        "lng": 77.4890,
        "keywords": ["gate", "entrance", "main", "entry", "security", "front gate"]
    },
    {
        "id": "northGate",
        "name": "Secondary North Gate (Hostel Side)",
        "category": "Gate / Entrance",
        "block": "Campus Perimeter",
        "floor": 0,
        "lat": 28.4735,
        "lng": 77.4888,
        "keywords": ["north gate", "hostel gate", "back gate", "entry"]
    },
    {
        "id": "sportsGround",
        "name": "Central Sports Ground & Basketball Arena",
        "category": "Sports & Recreation",
        "block": "Sports Zone",
        "floor": 0,
        "lat": 28.4715,
        "lng": 77.4882,
        "keywords": ["sports", "ground", "cricket", "football", "basketball", "court"]
    },
    {
        "id": "canteen",
        "name": "Campus Cafeteria & Food Court",
        "category": "Amenities",
        "block": "Cafeteria Complex",
        "floor": 0,
        "lat": 28.4724,
        "lng": 77.4894,
        "keywords": ["canteen", "cafeteria", "food", "lunch", "snacks", "cafe"]
    },
    {
        "id": "library",
        "name": "Central Library (Learning Resource Centre)",
        "category": "Academic",
        "block": "library",
        "floor": 0,
        "lat": 28.4728,
        "lng": 77.4888,
        "keywords": ["library", "books", "reading", "study", "central library"]
    },
    {
        "id": "audi",
        "name": "Auditorium & Convention Hall",
        "category": "Events & Culture",
        "block": "audi",
        "floor": 0,
        "lat": 28.4719,
        "lng": 77.4895,
        "keywords": ["auditorium", "audi", "convention", "seminar", "stage"]
    },
    {
        "id": "block1",
        "name": "Academic Block 1 (CSE, IT & Engineering)",
        "category": "Academic Block",
        "block": "block1",
        "floor": 0,
        "lat": 28.4725,
        "lng": 77.4885,
        "keywords": ["block 1", "academic block 1", "cse", "it", "engineering"]
    },
    {
        "id": "block2",
        "name": "Academic Block 2 (ECE, ME, Civil & Applied Sciences)",
        "category": "Academic Block",
        "block": "block2",
        "floor": 0,
        "lat": 28.4721,
        "lng": 77.4890,
        "keywords": ["block 2", "academic block 2", "ece", "me", "civil"]
    },
    {
        "id": "ctmB",
        "name": "CTM Block B (Corporate & Postgraduate Wing)",
        "category": "Academic Block",
        "block": "ctmB",
        "floor": 0,
        "lat": 28.4730,
        "lng": 77.4898,
        "keywords": ["ctm b", "block b", "corporate wing", "postgraduate"]
    },
    {
        "id": "ctmA",
        "name": "CTM Block A (10-Storey Corporate & Computing Tower)",
        "category": "Academic Block",
        "block": "ctmA",
        "floor": 0,
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["ctm a", "ctm block a", "tower", "management", "mba"]
    },
    # CTM Block A - Floors 1-5
    {
        "id": "ctmPlacements",
        "name": "Training & Placement Cell (T&P) - CTM Block A, Floor 1",
        "category": "Administration",
        "block": "ctmA",
        "floor": 1,
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["placement", "t&p", "interviews", "jobs", "floor 1", "first floor"]
    },
    {
        "id": "ctmMbaDept",
        "name": "MBA Department & Faculty Offices - CTM Block A, Floor 2",
        "category": "Academic Department",
        "block": "ctmA",
        "floor": 2,
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["mba", "management dept", "floor 2"]
    },
    {
        "id": "ctmBoardroom",
        "name": "Executive Boardroom & Director Suite - CTM Block A, Floor 5",
        "category": "Administration",
        "block": "ctmA",
        "floor": 5,
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["boardroom", "director", "executive", "floor 5"]
    },
    # Floor 6 Rooms (CTM Block A)
    {
        "id": "examCell",
        "name": "Examination Cell & Controller of Exams - CTM Block A, Floor 6",
        "category": "Examination",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "examCell",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["exam", "examination cell", "controller", "hall ticket", "grade", "floor 6"]
    },
    {
        "id": "room601",
        "name": "Room 601 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room601",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 601", "601", "lecture 601", "floor 6"]
    },
    {
        "id": "room602",
        "name": "Room 602 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room602",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 602", "602", "floor 6"]
    },
    {
        "id": "room603",
        "name": "Room 603 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room603",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 603", "603", "floor 6"]
    },
    {
        "id": "room604",
        "name": "Room 604 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room604",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 604", "604", "floor 6"]
    },
    {
        "id": "room605",
        "name": "Room 605 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room605",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 605", "605", "floor 6"]
    },
    {
        "id": "room606",
        "name": "Room 606 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room606",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 606", "606", "floor 6"]
    },
    {
        "id": "room607",
        "name": "Room 607 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room607",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 607", "607", "floor 6"]
    },
    {
        "id": "room608",
        "name": "Room 608 (Lecture Hall) - CTM Block A, Floor 6",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 6,
        "map_type": "floor6",
        "room_id": "room608",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 608", "608", "floor 6"]
    },
    # Floor 8 Rooms (CTM Block A)
    {
        "id": "room801",
        "name": "Room 801 (Smart Classroom) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room801",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 801", "801", "floor 8"]
    },
    {
        "id": "room802",
        "name": "Room 802 (Lecture Hall) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room802",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 802", "802", "floor 8"]
    },
    {
        "id": "room803",
        "name": "Room 803 (Seminar Hall) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room803",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 803", "803", "floor 8"]
    },
    {
        "id": "room804",
        "name": "Room 804 (Smart Classroom) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room804",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 804", "804", "floor 8"]
    },
    {
        "id": "room806",
        "name": "Room 806 (Tutorial Room) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room806",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 806", "806", "floor 8"]
    },
    {
        "id": "room807",
        "name": "Room 807 (Department Lecture) - CTM Block A, Floor 8",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "room807",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 807", "807", "floor 8"]
    },
    {
        "id": "faculty8",
        "name": "Faculty Cabin Suite (Gates 1 & 2) - CTM Block A, Floor 8",
        "category": "Faculty",
        "block": "ctmA",
        "floor": 8,
        "map_type": "floor8",
        "room_id": "facultyGate1",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["faculty 8", "professors", "hod", "cabin 8", "faculty gate"]
    },
    # Floor 9 Rooms (CTM Block A)
    {
        "id": "room901",
        "name": "Room 901 (Smart Lecture Room) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room901",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 901", "901", "floor 9"]
    },
    {
        "id": "room902",
        "name": "Room 902 (Research Classroom) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room902",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 902", "902", "floor 9"]
    },
    {
        "id": "room903",
        "name": "Room 903 (Seminar Room) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room903",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 903", "903", "floor 9"]
    },
    {
        "id": "room904",
        "name": "Room 904 (Executive Classroom) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room904",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 904", "904", "floor 9"]
    },
    {
        "id": "room906",
        "name": "Room 906 (Tutorial Classroom) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room906",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 906", "906", "floor 9"]
    },
    {
        "id": "room907",
        "name": "Room 907 (Advanced PG Lecture) - CTM Block A, Floor 9",
        "category": "Lecture Hall",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "room907",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["room 907", "907", "floor 9"]
    },
    {
        "id": "faculty9",
        "name": "Senior Faculty & Dean Chamber (Gate 1) - CTM Block A, Floor 9",
        "category": "Faculty",
        "block": "ctmA",
        "floor": 9,
        "map_type": "floor9",
        "room_id": "facultyGate1",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["faculty 9", "dean", "professors", "cabin 9"]
    },
    # Floor 10 Labs (CTM Block A)
    {
        "id": "lab1001",
        "name": "Lab 1001 - Artificial Intelligence & ML Lab (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1001",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1001", "1001", "ai lab", "machine learning", "floor 10"]
    },
    {
        "id": "lab1002",
        "name": "Lab 1002 - Data Science & Deep Learning (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1002",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1002", "1002", "data science", "deep learning", "floor 10"]
    },
    {
        "id": "lab1003",
        "name": "Lab 1003 - Cloud Computing & DevOps (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1003",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1003", "1003", "cloud", "devops", "aws", "floor 10"]
    },
    {
        "id": "lab1004",
        "name": "Lab 1004 - Cybersecurity & Digital Forensics (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1004",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1004", "1004", "cybersecurity", "security", "forensics", "floor 10"]
    },
    {
        "id": "lab1005",
        "name": "Lab 1005 - Software Engineering & Full Stack (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1005",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1005", "1005", "software engineering", "full stack", "web dev", "floor 10"]
    },
    {
        "id": "lab1006",
        "name": "Lab 1006 - Big Data Analytics Lab (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1006",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1006", "1006", "big data", "hadoop", "spark", "floor 10"]
    },
    {
        "id": "lab1007",
        "name": "Lab 1007 - Mobile App Development (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1007",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1007", "1007", "mobile app", "android", "flutter", "ios", "floor 10"]
    },
    {
        "id": "lab1008",
        "name": "Lab 1008 - IoT & Embedded Systems Lab (CTM Block A, Floor 10)",
        "category": "Computing Lab",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "lab1008",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["lab 1008", "1008", "iot", "embedded", "arduino", "sensors", "floor 10"]
    },
    {
        "id": "serverRoom",
        "name": "Central Server Room & Campus NOC (CTM Block A, Floor 10)",
        "category": "Infrastructure",
        "block": "ctmA",
        "floor": 10,
        "map_type": "floor10",
        "room_id": "serverRoom",
        "lat": 28.4732,
        "lng": 77.4893,
        "keywords": ["server room", "noc", "data center", "datacenter", "floor 10"]
    }
]

def resolve_location(query_str):
    """Fuzzy / ID resolver for campus landmarks, blocks, and floor rooms."""
    if not query_str or not isinstance(query_str, str):
        return CAMPUS_LOCATIONS[0] # Default to Main Gate

    q = query_str.strip().lower()

    # 1. Exact ID Match
    for loc in CAMPUS_LOCATIONS:
        if loc["id"].lower() == q:
            return loc

    # 2. Exact or substring Name Match
    for loc in CAMPUS_LOCATIONS:
        if q == loc["name"].lower():
            return loc

    for loc in CAMPUS_LOCATIONS:
        if q in loc["name"].lower():
            return loc

    # 3. Keywords Match
    for loc in CAMPUS_LOCATIONS:
        for kw in loc.get("keywords", []):
            if q == kw.lower() or kw.lower() in q:
                return loc

    # 4. Lat/Lng string match ("28.4720, 77.4890")
    if "," in q:
        parts = q.split(",")
        try:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return {
                "id": "customGps",
                "name": f"Current Position ({lat:.4f}, {lng:.4f})",
                "category": "Live GPS",
                "block": "Live GPS",
                "floor": 0,
                "lat": lat,
                "lng": lng,
                "keywords": ["custom", "gps"]
            }
        except ValueError:
            pass

    # Default fallback to Main Gate
    return CAMPUS_LOCATIONS[0]

def calculate_campus_route(origin_query, dest_query):
    """Computes comprehensive walking distance, walk time, elevator instructions and turn-by-turn steps."""
    orig = resolve_location(origin_query)
    dest = resolve_location(dest_query)

    if not orig or not dest:
        return {"success": False, "error": "Unable to resolve start or destination location."}

    # Haversine distance on horizontal campus plane
    ground_dist = haversine_distance_meters(orig["lat"], orig["lng"], dest["lat"], dest["lng"])

    # Vertical difference
    orig_floor = orig.get("floor", 0)
    dest_floor = dest.get("floor", 0)
    floor_diff = abs(dest_floor - orig_floor)
    vertical_dist = round(floor_diff * 4.0, 1) # ~4m per floor height

    total_dist = round(ground_dist + vertical_dist, 1)

    # Walk time: average 80m/min walk speed + 20s per floor for elevator/stairs
    walk_min = round((ground_dist / 80.0) + (floor_diff * 0.35), 1)
    if walk_min < 1.0:
        walk_min = 1.0

    # Elevator recommendation
    dest_block = dest.get("block", "")
    elevator_info = "Ground level traversal. No elevators required."
    lift_badge = "🚶 Direct Walk"

    if dest_block == "ctmA" and dest_floor > 0:
        if dest_floor >= 8:
            elevator_info = f"Take Lift B (Express - Floors 8, 9, 10) or Lift A (All Floors) to Floor {dest_floor}. Note: Lift C only stops at Floors 1-6."
            lift_badge = "🛗 Lift B (Express) or Lift A"
        elif dest_floor in (1, 2, 3, 4, 5, 6):
            elevator_info = f"Take Lift C (Local - Floors 1-6) or Lift A (All Floors) to Floor {dest_floor}. Note: Lift B Express does not stop here."
            lift_badge = "🛗 Lift C or Lift A"
        elif dest_floor == 7:
            elevator_info = "Floor 7 is vacant/reserved. Only accessible via Lift A (All Floors)."
            lift_badge = "🛗 Lift A (All Floors)"
    elif dest_block in ("block1", "block2") and dest_floor > 0:
        elevator_info = f"Take Central Staircase or West Foyer Elevator to Floor {dest_floor}."
        lift_badge = "🛗 Central Lift / Stairs"
    elif dest_block == "ctmB" and dest_floor > 0:
        elevator_info = f"Take North Foyer Elevator to Floor {dest_floor}."
        lift_badge = "🛗 North Elevator"

    # Turn-by-Turn Wayfinding Steps
    steps = []
    step_num = 1

    # Step 1: Start
    steps.append({
        "step": step_num,
        "icon": "bx-map-pin",
        "title": f"Depart from {orig['name']}",
        "instruction": f"Begin your journey from {orig['name']} ({orig['category']}). Facing towards central campus walkways.",
        "distance": "0 m"
    })
    step_num += 1

    # Step 2: Campus walk
    if ground_dist > 15:
        steps.append({
            "step": step_num,
            "icon": "bx-walk",
            "title": "Follow Central Campus Walkway",
            "instruction": f"Walk approximately {int(ground_dist)} meters along the paved campus boulevard toward {dest.get('block', 'target block')}.",
            "distance": f"~{int(ground_dist)} m"
        })
        step_num += 1

    # Step 3: Foyer entry
    if dest_block in ("ctmA", "ctmB", "block1", "block2", "library", "audi"):
        steps.append({
            "step": step_num,
            "icon": "bx-door-open",
            "title": f"Enter {dest.get('block', 'Building')} Ground Foyer",
            "instruction": f"Pass through the main foyer security gates of {dest.get('name', 'destination building')}.",
            "distance": "15 m"
        })
        step_num += 1

    # Step 4: Vertical transit
    if dest_floor > 0:
        steps.append({
            "step": step_num,
            "icon": "bx-up-arrow-circle",
            "title": f"Elevator / Stairs to Floor {dest_floor}",
            "instruction": elevator_info,
            "distance": f"+{dest_floor} levels ({vertical_dist}m)"
        })
        step_num += 1

    # Step 5: Final room / arrival
    steps.append({
        "step": step_num,
        "icon": "bx-check-circle",
        "title": f"Arrive at {dest['name']}",
        "instruction": f"You have reached your destination: {dest['name']}. Located on Floor {dest_floor}.",
        "distance": "0 m"
    })

    return {
        "success": True,
        "origin": orig,
        "destination": dest,
        "total_distance_meters": total_dist,
        "ground_distance_meters": ground_dist,
        "vertical_distance_meters": vertical_dist,
        "walk_time_minutes": walk_min,
        "floors_traversed": floor_diff,
        "elevator_recommendation": elevator_info,
        "lift_badge": lift_badge,
        "steps": steps,
        "deep_link": {
            "map_type": dest.get("map_type"),
            "room_id": dest.get("room_id"),
            "block_key": dest.get("block")
        }
    }


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users Table (with Avatar Image option)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            id_number TEXT,
            department TEXT,
            avatar TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Safe migration in case table was created earlier without avatar
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT;")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    # 2. Auth Sessions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # 3. Campus Blocks Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS campus_blocks (
            block_key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            floors_count INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT NOT NULL,
            elevator_info TEXT
        );
    """)

    # 4. Floor Plans Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS floor_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_key TEXT NOT NULL,
            floor_number INTEGER NOT NULL,
            floor_label TEXT NOT NULL,
            facilities TEXT NOT NULL,
            lifts_accessible TEXT,
            FOREIGN KEY (block_key) REFERENCES campus_blocks(block_key) ON DELETE CASCADE
        );
    """)

    # 5. Events Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date_str TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 6. Contact Inquiries Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # ------------------ Seed Default Users ------------------
    default_avatars = {
        "student": "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%20width%3D%22100%22%20height%3D%22100%22%3E%0A%20%20%3Ccircle%20cx%3D%2250%22%20cy%3D%2250%22%20r%3D%2248%22%20fill%3D%22%230771db%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%224%22/%3E%0A%20%20%3Ctext%20x%3D%2250%22%20y%3D%2258%22%20font-size%3D%2242%22%20text-anchor%3D%22middle%22%20dominant-baseline%3D%22middle%22%3E%F0%9F%8E%93%3C/text%3E%0A%3C/svg%3E",
        "faculty": "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%20width%3D%22100%22%20height%3D%22100%22%3E%0A%20%20%3Ccircle%20cx%3D%2250%22%20cy%3D%2250%22%20r%3D%2248%22%20fill%3D%22%23059669%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%224%22/%3E%0A%20%20%3Ctext%20x%3D%2250%22%20y%3D%2258%22%20font-size%3D%2242%22%20text-anchor%3D%22middle%22%20dominant-baseline%3D%22middle%22%3E%F0%9F%91%A8%E2%80%8D%F0%9F%8F%AB%3C/text%3E%0A%3C/svg%3E",
        "staff": "data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%20100%20100%22%20width%3D%22100%22%20height%3D%22100%22%3E%0A%20%20%3Ccircle%20cx%3D%2250%22%20cy%3D%2250%22%20r%3D%2248%22%20fill%3D%22%237c3aed%22%20stroke%3D%22%23ffffff%22%20stroke-width%3D%224%22/%3E%0A%20%20%3Ctext%20x%3D%2250%22%20y%3D%2258%22%20font-size%3D%2242%22%20text-anchor%3D%22middle%22%20dominant-baseline%3D%22middle%22%3E%F0%9F%9B%A1%EF%B8%8F%3C/text%3E%0A%3C/svg%3E"
    }
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        demo_users = [
            ("Aarav Sharma", "student", "student@glbitm.org", "student123", "student", "230192010045", "Computer Science", default_avatars["student"]),
            ("Dr. Vivek Verma", "faculty", "faculty@glbitm.org", "faculty123", "faculty", "GLB-FAC-108", "Information Technology", default_avatars["faculty"]),
            ("Admin Office", "admin", "admin@glbitm.org", "admin123", "staff", "GLB-ADM-001", "Registrar & Administration", default_avatars["staff"])
        ]
        for fn, un, em, pw, role, id_num, dept, av in demo_users:
            cursor.execute("""
                INSERT INTO users (fullname, username, email, password, role, id_number, department, avatar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fn, un, em, pw, role, id_num, dept, av))
        conn.commit()
        print(f"[Database] Seeded 3 default accounts in {DB_FILE}")
    else:
        # Ensure default accounts have avatars assigned if null
        for r_key, av_val in default_avatars.items():
            cursor.execute("UPDATE users SET avatar = ? WHERE role = ? AND (avatar IS NULL OR avatar = '')", (av_val, r_key))
        conn.commit()

    # ------------------ Seed Campus Blocks & GPS ------------------
    cursor.execute("SELECT COUNT(*) FROM campus_blocks")
    if cursor.fetchone()[0] == 0:
        blocks = [
            (
                "ctmA", "🏢 CTM Block A", "Management & Corporate Wing", 10,
                28.4732, 77.4893,
                "10-story tower housing MBA, Training & Placement Cell, Business Analytics Labs, and Boardrooms.",
                "Lift A (All Floors 1-10), Lift B (Express: Floors 8, 9, 10 Only), Lift C (Floors 1-6 Only)"
            ),
            (
                "ctmB", "🏢 CTM Block B", "Technology & Innovation Wing", 10,
                28.4730, 77.4898,
                "10-story tower housing MCA, Artificial Intelligence GPU Labs, Atal Startup Incubation Hub, and Hackathon Arena.",
                "Lift A (All Floors 1-10), Lift B (Express: Floors 8, 9, 10 Only), Lift C (Floors 1-6 Only)"
            ),
            (
                "block1", "💻 Academic Block 1", "Computer Science Complex", 4,
                28.4725, 77.4885,
                "4-story computing center housing CSE, IT, Data Science research labs, and faculty cabins.",
                "Central Staircases & North Wing Accessibility Elevator"
            ),
            (
                "block2", "⚙️ Academic Block 2", "Electronics & Mechanical Complex", 4,
                28.4721, 77.4890,
                "4-story engineering facility housing ECE, Robotics Center of Excellence, Mechanical workshops, and Civil labs.",
                "Central Staircases & South Wing Accessibility Ramp"
            ),
            (
                "library", "📚 Central Library", "Learning Commons", 1,
                28.4728, 77.4888,
                "Single-level ground floor learning commons housing 50,000+ volumes, IEEE digital access, and quiet study hall.",
                "Ground Floor Level Facility (No upper floors)"
            ),
            (
                "auditorium", "🎭 Auditorium & Convention Complex", "Cultural & Event Center", 2,
                28.4719, 77.4895,
                "Centrally air-conditioned 1000-seater main auditorium for national symposiums and youth fests.",
                "Main Level Entry & Balcony Access"
            )
        ]
        for key, name, cat, flrs, lat, lng, desc, lifts in blocks:
            cursor.execute("""
                INSERT INTO campus_blocks (block_key, name, category, floors_count, latitude, longitude, description, elevator_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (key, name, cat, flrs, lat, lng, desc, lifts))

        # ------------------ Seed Floor Plans for CTM Block A ------------------
        ctm_a_floors = [
            ("ctmA", 1, "Floor 1", "Corporate Training & Placement Cell (T&P), Executive Interview Suites, Visitors Lounge, Dean Office", "🛗 Lift A & C"),
            ("ctmA", 2, "Floor 2", "Department of Management Studies (MBA & PGDM), Smart Interactive Lecture Theatres 201 - 208, Boardroom", "🛗 Lift A & C"),
            ("ctmA", 3, "Floor 3", "Executive Development Center (EDC), Case Study Discussion Rooms, Faculty Cabins, Management Seminar Hall 1", "🛗 Lift A & C"),
            ("ctmA", 4, "Floor 4", "Department of Finance & Marketing Studies, Stock Market Simulation Terminal, Financial Analytics Lab", "🛗 Lift A & C"),
            ("ctmA", 5, "Floor 5", "Business Analytics High-Performance Computing Center, Big Data Visualization Lab", "🛗 Lift A & C"),
            ("ctmA", 6, "Floor 6", "Examination Cell, Central Evaluation Center, Classrooms (601-608), Washrooms, Lifts, Stairs & Emergency Core", "🛗 Lift A & C"),
            ("ctmA", 7, "Floor 7", "Empty Floor (Vacant / Reserved for Future Institutional Expansion)", "🛗 Lift A Only"),
            ("ctmA", 8, "Floor 8", "Academic Lecture Rooms (801-804, 806-807), Faculty Room Suites (Gate 1 & 2), Washrooms, Normal Lift, Stairs & Emergency Core", "🛗 Lift A & B (Express)"),
            ("ctmA", 9, "Floor 9", "Academic Lecture Rooms (901-904, 906-907), Faculty Room Suites (Gate 1 & 2), Washrooms, Normal Lift, Stairs & Emergency Core", "🛗 Lift A & B (Express)"),
            ("ctmA", 10, "Floor 10", "Advanced Computing, High-Performance Simulation & Department Laboratories Only (Labs Only)", "🛗 Lift A & B (Express)")
        ]
        for b_key, f_num, f_lbl, f_fac, f_lft in ctm_a_floors:
            cursor.execute("""
                INSERT INTO floor_plans (block_key, floor_number, floor_label, facilities, lifts_accessible)
                VALUES (?, ?, ?, ?, ?)
            """, (b_key, f_num, f_lbl, f_fac, f_lft))

        # ------------------ Seed Floor Plans for CTM Block B ------------------
        ctm_b_floors = [
            ("ctmB", 1, "Floor 1", "Main Campus Reception, Security Operations Center, Student Affairs & Helpdesk, Central Server Hub", "🛗 Lift A & C"),
            ("ctmB", 2, "Floor 2", "Department of Computer Applications (MCA) & Cloud Computing Labs, Smart Lecture Theatres 201 - 208", "🛗 Lift A & C"),
            ("ctmB", 3, "Floor 3", "Artificial Intelligence & Deep Learning Research Lab, High-Performance GPU Cluster Center", "🛗 Lift A & C"),
            ("ctmB", 4, "Floor 4", "GL Bajaj Innovation & Entrepreneurship Center, Atal Incubation Hub, Student Startup Bays", "🛗 Lift A & C"),
            ("ctmB", 5, "Floor 5", "Cyber Security Operations Center (SOC) Lab, Digital Forensics & Ethical Hacking Arena", "🛗 Lift A & C"),
            ("ctmB", 6, "Floor 6", "Internet of Things (IoT) & Embedded Systems Research Bay, Robotics Arena & Testing Bay", "🛗 Lift A & C"),
            ("ctmB", 7, "Floor 7", "Advanced Software Engineering & Full-Stack Development Studios, CodeSprint Arena", "🛗 Lift A Only"),
            ("ctmB", 8, "Floor 8", "FinTech, Blockchain & Web3 Technologies Center of Excellence, Corporate Sponsored Labs", "🛗 Lift A & B (Express)"),
            ("ctmB", 9, "Floor 9", "Multi-Disciplinary Research Scholars Bay, Patent Facilitation Cell, Faculty Cabins", "🛗 Lift A & B (Express)"),
            ("ctmB", 10, "Floor 10", "Grand Tech Symposium Arena, Hackathon Arena (24x7 Ready), Sky Lounge & Panoramic Campus Deck", "🛗 Lift A & B (Express)")
        ]
        for b_key, f_num, f_lbl, f_fac, f_lft in ctm_b_floors:
            cursor.execute("""
                INSERT INTO floor_plans (block_key, floor_number, floor_label, facilities, lifts_accessible)
                VALUES (?, ?, ?, ?, ?)
            """, (b_key, f_num, f_lbl, f_fac, f_lft))

        # ------------------ Seed Floor Plans for Academic Block 1 (4 Floors) ------------------
        b1_floors = [
            ("block1", 1, "Floor 1", "HOD Computer Science & IT Office, Department Administrative Registrar, Central Server Room, Helpdesk", "Main Entry"),
            ("block1", 2, "Floor 2", "Interactive Smart Lecture Theatres 101 - 112, Faculty Workspaces, Tutorial Discussion Rooms", "Stairs / Ramp"),
            ("block1", 3, "Floor 3", "Artificial Intelligence, Data Science & Machine Learning Research Labs, Cloud Computing Center", "Stairs / Ramp"),
            ("block1", 4, "Floor 4", "Cyber Security Lab, Full-Stack Web Development Studios, Final Year Capstone Project Center", "Stairs / Ramp")
        ]
        for b_key, f_num, f_lbl, f_fac, f_lft in b1_floors:
            cursor.execute("""
                INSERT INTO floor_plans (block_key, floor_number, floor_label, facilities, lifts_accessible)
                VALUES (?, ?, ?, ?, ?)
            """, (b_key, f_num, f_lbl, f_fac, f_lft))

        conn.commit()
        print("[Database] Seeded Campus GPS Blocks & 10-Floor Plans.")

    # ------------------ Seed Default Events ------------------
    cursor.execute("SELECT COUNT(*) FROM events")
    if cursor.fetchone()[0] == 0:
        events = [
            ("Technovation Hackathon 2026", "November 15, 2026", "Hackathon", "36-hour inter-college AI & Web3 innovation sprint with cash prizes.", "CTM Block B, 10th Floor Hackathon Arena"),
            ("Annual Tech & Cultural Fest 'Vibrance'", "December 2, 2026", "Fest", "Robotics contest, code jams, battle of the bands, and celebrity night.", "Main Auditorium & Campus Ground"),
            ("Corporate HR Conclave & Campus Placements", "January 10, 2027", "Placement", "Annual interaction with 120+ leading IT and core engineering recruiters.", "CTM Block A, Ground Floor Placement Cell")
        ]
        for title, d_str, cat, desc, loc in events:
            cursor.execute("""
                INSERT INTO events (title, date_str, category, description, location)
                VALUES (?, ?, ?, ?, ?)
            """, (title, d_str, cat, desc, loc))
        conn.commit()

    conn.close()


# ---------------------------------------------------------------------------
# HTTP Request Handler & REST API Router
# ---------------------------------------------------------------------------
class CompleteCollegeBackendHandler(SimpleHTTPRequestHandler):

    def end_headers(self):
        # Enable CORS for local cross-origin testing
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def get_auth_user(self):
        """Extract user from Authorization: Bearer <token>."""
        auth_header = self.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

        if not token:
            # Fallback to cookie if present
            cookie = self.headers.get("Cookie", "")
            for c in cookie.split(";"):
                if "glb_token=" in c:
                    token = c.split("glb_token=")[1].strip()

        if not token:
            return None

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.fullname, u.username, u.email, u.role, u.id_number, u.department, u.avatar
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > datetime('now')
        """, (token,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    # -----------------------------------------------------------------------
    # GET Endpoints
    # -----------------------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Health / Ping Check
        if path in ("/api/ping", "/api/health"):
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM campus_blocks")
            block_count = cursor.fetchone()[0]
            conn.close()

            self.send_json(200, {
                "status": "healthy",
                "database": "sqlite3",
                "campus": "GL Bajaj Institute of Technology & Management",
                "coordinates": CAMPUS_COORDS,
                "stats": {
                    "registered_users": user_count,
                    "mapped_blocks": block_count
                },
                "server_time": datetime.now().isoformat()
            })
            return

        # Current Authenticated Session
        if path == "/api/me":
            user = self.get_auth_user()
            if not user:
                self.send_json(401, {"authenticated": False, "error": "No active session"})
                return
            self.send_json(200, {"authenticated": True, "user": user})
            return

        # User Lookup by Username/Email (for Live Avatar & Identity preview)
        if path in ("/api/users/lookup", "/api/user/lookup"):
            un = query.get("username", [None])[0] or query.get("q", [None])[0]
            if not un:
                self.send_json(400, {"error": "Missing username or email query parameter."})
                return
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, fullname, username, role, id_number, department, avatar
                FROM users WHERE username = ? OR email = ?
            """, (un.lower().strip(), un.lower().strip()))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.send_json(200, {
                    "found": True,
                    "user": {
                        "id": row["id"],
                        "fullname": row["fullname"],
                        "username": row["username"],
                        "role": row["role"],
                        "idNumber": row["id_number"],
                        "department": row["department"],
                        "avatar": row["avatar"] or ""
                    }
                })
            else:
                self.send_json(404, {"found": False, "message": f"User '{un}' not found."})
            return

        # List All Users (Admin / Faculty)
        if path == "/api/users":
            conn = get_db()
            cursor = conn.cursor()
            role_filter = query.get("role", [None])[0]
            if role_filter:
                cursor.execute("""
                    SELECT id, fullname, username, email, role, id_number, department, avatar, created_at
                    FROM users WHERE role = ? ORDER BY id DESC
                """, (role_filter,))
            else:
                cursor.execute("""
                    SELECT id, fullname, username, email, role, id_number, department, avatar, created_at
                    FROM users ORDER BY id DESC
                """)
            rows = cursor.fetchall()
            users = [dict(r) for r in rows]

            # Role statistics
            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            counts = {r[0]: r[1] for r in cursor.fetchall()}
            conn.close()

            self.send_json(200, {
                "total": len(users),
                "counts_by_role": counts,
                "users": users
            })
            return

        # Campus Blocks & GPS Navigation Data
        if path == "/api/blocks":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campus_blocks")
            rows = cursor.fetchall()
            blocks = [dict(r) for r in rows]
            conn.close()
            self.send_json(200, {
                "campus": "GL Bajaj Institute of Technology & Management",
                "center": CAMPUS_COORDS,
                "blocks": blocks
            })
            return

        # Single Block Details with Full Floor Plan
        if path.startswith("/api/blocks/"):
            block_key = path.replace("/api/blocks/", "").strip()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM campus_blocks WHERE block_key = ?", (block_key,))
            block_row = cursor.fetchone()
            if not block_row:
                conn.close()
                self.send_json(404, {"error": f"Block '{block_key}' not found"})
                return

            block = dict(block_row)
            cursor.execute("""
                SELECT floor_number, floor_label, facilities, lifts_accessible
                FROM floor_plans WHERE block_key = ? ORDER BY floor_number ASC
            """, (block_key,))
            floors = [dict(r) for r in cursor.fetchall()]
            conn.close()

            block["floors"] = floors
            self.send_json(200, {"block": block})
            return

        # Events List
        if path == "/api/events":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events ORDER BY id DESC")
            events = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"events": events})
            return

        # Contact Inquiries
        if path == "/api/contact":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM contact_messages ORDER BY id DESC")
            messages = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"messages": messages})
            return

        # Admin Comprehensive Statistics
        if path == "/api/admin/stats":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
            users_by_role = {r[0]: r[1] for r in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) FROM campus_blocks")
            total_blocks = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM floor_plans")
            total_floors = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM events")
            total_events = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM contact_messages")
            total_messages = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE expires_at > datetime('now')")
            active_sessions = cursor.fetchone()[0]
            conn.close()

            self.send_json(200, {
                "success": True,
                "campus": "GL Bajaj Institute of Technology & Management",
                "center": CAMPUS_COORDS,
                "stats": {
                    "total_users": total_users,
                    "users_by_role": users_by_role,
                    "total_blocks": total_blocks,
                    "total_floors": total_floors,
                    "total_events": total_events,
                    "total_messages": total_messages,
                    "active_sessions": active_sessions,
                    "active_cad_blueprints": 4,
                    "mapped_locations": len(CAMPUS_LOCATIONS)
                },
                "server": {
                    "status": "online",
                    "database": "sqlite3",
                    "db_path": DB_FILE,
                    "timestamp": datetime.now().isoformat()
                }
            })
            return

        # Campus Locations Catalog
        if path == "/api/locations":
            self.send_json(200, {
                "total": len(CAMPUS_LOCATIONS),
                "campus": "GL Bajaj Institute of Technology & Management",
                "center": CAMPUS_COORDS,
                "locations": CAMPUS_LOCATIONS
            })
            return

        # Campus Wayfinding Route Finder (GET)
        if path == "/api/route":
            origin_query = query.get("from", ["mainGate"])[0]
            dest_query = query.get("to", ["lab1004"])[0]
            result = calculate_campus_route(origin_query, dest_query)
            self.send_json(200 if result.get("success") else 400, result)
            return

        # Serve static frontend files (index.html, vivek.html, his.css, etc.)
        super().do_GET()

    # -----------------------------------------------------------------------
    # POST Endpoints
    # -----------------------------------------------------------------------
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Read JSON body safely
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                data = {}

        # ------------------ Register ------------------
        if path == "/api/register":
            fullname = data.get("fullname", "").strip()
            username = data.get("username", "").strip().lower()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            role = data.get("role", "student").strip().lower()
            id_number = data.get("idNumber", "").strip()
            department = data.get("department", "").strip()
            avatar = data.get("avatar", "").strip()

            if not username or not email or not password:
                self.send_json(400, {"error": "Username, email, and password are required."})
                return

            if len(password) < 4:
                self.send_json(400, {"error": "Password must be at least 4 characters long."})
                return

            conn = get_db()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO users (fullname, username, email, password, role, id_number, department, avatar)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (fullname or username, username, email, password, role, id_number, department, avatar))
                user_id = cursor.lastrowid
                conn.commit()

                # Generate Auth Token
                token = secrets.token_hex(24)
                expires = datetime.now() + timedelta(days=7)
                cursor.execute("""
                    INSERT INTO sessions (token, user_id, role, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (token, user_id, role, expires.strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()

                self.send_json(201, {
                    "success": True,
                    "message": f"Successfully registered as {role.upper()}!",
                    "token": token,
                    "user": {
                        "id": user_id,
                        "fullname": fullname or username,
                        "username": username,
                        "email": email,
                        "role": role,
                        "idNumber": id_number,
                        "department": department,
                        "avatar": avatar
                    }
                })
            except sqlite3.IntegrityError:
                conn.close()
                self.send_json(409, {"error": f"Username '{username}' or email '{email}' is already registered."})
            return

        # ------------------ Login ------------------
        if path == "/api/login":
            username = data.get("username", "").strip().lower()
            password = data.get("password", "")
            role = data.get("role", "").strip().lower()

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, fullname, username, email, password, role, id_number, department, avatar
                FROM users
                WHERE (username = ? OR email = ?)
            """, (username, username))
            row = cursor.fetchone()

            if not row or row["password"] != password:
                conn.close()
                self.send_json(401, {"error": "Invalid username/email or password."})
                return

            user_role = row["role"]
            is_admin_match = (user_role in ("staff", "admin") and role in ("staff", "admin"))
            if role and role != "all" and user_role != role and not is_admin_match:
                conn.close()
                self.send_json(400, {
                    "error": f"Account is registered as '{user_role.upper()}', not '{role.upper()}'. Please select the right role."
                })
                return

            user_id = row["id"]
            # Generate new session token
            token = secrets.token_hex(24)
            expires = datetime.now() + timedelta(days=7)
            cursor.execute("""
                INSERT INTO sessions (token, user_id, role, expires_at)
                VALUES (?, ?, ?, ?)
            """, (token, user_id, user_role, expires.strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()

            user_payload = {
                "id": row["id"],
                "fullname": row["fullname"],
                "username": row["username"],
                "email": row["email"],
                "role": row["role"],
                "idNumber": row["id_number"],
                "department": row["department"],
                "avatar": row["avatar"] or ""
            }

            self.send_json(200, {
                "success": True,
                "message": f"Welcome back, {row['fullname']}!",
                "token": token,
                "user": user_payload
            })
            return

        # ------------------ Update Avatar / Profile Photo ------------------
        if path in ("/api/user/avatar", "/api/users/avatar"):
            username = data.get("username", "").strip().lower()
            avatar = data.get("avatar", "")
            if not username or not avatar:
                self.send_json(400, {"error": "Username and avatar image data are required."})
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET avatar = ?
                WHERE username = ? OR email = ?
            """, (avatar, username, username))
            conn.commit()
            count = cursor.rowcount
            conn.close()

            if count > 0:
                self.send_json(200, {
                    "success": True,
                    "message": "Profile picture updated successfully!",
                    "avatar": avatar
                })
            else:
                self.send_json(404, {"error": f"User '{username}' not found."})
            return

        # ------------------ Logout ------------------
        if path == "/api/logout":
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
                conn.commit()
                conn.close()
            self.send_json(200, {"success": True, "message": "Logged out successfully."})
            return

        # ------------------ GPS Live Location Resolver ------------------
        if path == "/api/locate":
            try:
                user_lat = float(data.get("lat"))
                user_lng = float(data.get("lng"))
            except (TypeError, ValueError):
                self.send_json(400, {"error": "Valid numeric 'lat' and 'lng' are required."})
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT block_key, name, category, latitude, longitude FROM campus_blocks")
            rows = cursor.fetchall()
            conn.close()

            results = []
            for r in rows:
                dist_m = haversine_distance_meters(user_lat, user_lng, r["latitude"], r["longitude"])
                walking_min = round(dist_m / 80.0, 1) # ~80 meters per minute average walk speed
                results.append({
                    "block_key": r["block_key"],
                    "name": r["name"],
                    "category": r["category"],
                    "distance_meters": dist_m,
                    "estimated_walk_minutes": walking_min,
                    "target_coords": {"lat": r["latitude"], "lng": r["longitude"]}
                })

            # Sort by proximity
            results.sort(key=lambda x: x["distance_meters"])
            nearest = results[0] if results else None

            campus_dist = haversine_distance_meters(user_lat, user_lng, CAMPUS_COORDS["lat"], CAMPUS_COORDS["lng"])
            on_campus = campus_dist < 600 # Within 600m radius of GL Bajaj

            self.send_json(200, {
                "user_location": {"lat": user_lat, "lng": user_lng},
                "on_campus": on_campus,
                "distance_to_campus_center_meters": campus_dist,
                "nearest_building": nearest,
                "all_buildings_by_distance": results
            })
            return

        # ------------------ Route Finder & Wayfinding ------------------
        if path == "/api/route":
            origin_query = data.get("from") or data.get("origin") or "mainGate"
            dest_query = data.get("to") or data.get("destination") or "lab1004"
            result = calculate_campus_route(origin_query, dest_query)
            self.send_json(200 if result.get("success") else 400, result)
            return

        # ------------------ Add Event ------------------
        if path == "/api/events":
            title = data.get("title", "").strip()
            date_str = data.get("date", "").strip()
            category = data.get("category", "General").strip()
            desc = data.get("description", "").strip()
            loc = data.get("location", "GL Bajaj Campus").strip()

            if not title or not date_str:
                self.send_json(400, {"error": "Event title and date are required."})
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO events (title, date_str, category, description, location)
                VALUES (?, ?, ?, ?, ?)
            """, (title, date_str, category, desc, loc))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()

            self.send_json(201, {"success": True, "id": new_id, "message": "Event published!"})
            return

        # ------------------ Contact Inquiry ------------------
        if path == "/api/contact":
            name = data.get("name", "").strip()
            email = data.get("email", "").strip()
            subject = data.get("subject", "General Inquiry").strip()
            message = data.get("message", "").strip()

            if not name or not email or not message:
                self.send_json(400, {"error": "Name, email, and message are required."})
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contact_messages (name, email, subject, message)
                VALUES (?, ?, ?, ?)
            """, (name, email, subject, message))
            conn.commit()
            conn.close()

            self.send_json(201, {"success": True, "message": "Your message has been sent to GL Bajaj administration."})
            return

        # ------------------ Admin: Update User ------------------
        if path in ("/api/admin/users/update", "/api/user/update"):
            user_id = data.get("id")
            fullname = data.get("fullname", "").strip()
            role = data.get("role", "").strip().lower()
            department = data.get("department", "").strip()
            id_number = data.get("idNumber", "").strip()

            if not user_id:
                self.send_json(400, {"error": "User ID is required."})
                return

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET fullname = COALESCE(NULLIF(?, ''), fullname),
                    role = COALESCE(NULLIF(?, ''), role),
                    department = COALESCE(NULLIF(?, ''), department),
                    id_number = COALESCE(NULLIF(?, ''), id_number)
                WHERE id = ?
            """, (fullname, role, department, id_number, user_id))
            conn.commit()
            updated = cursor.rowcount
            conn.close()

            if updated > 0:
                self.send_json(200, {"success": True, "message": f"User {user_id} updated successfully."})
            else:
                self.send_json(404, {"error": f"User {user_id} not found."})
            return

        self.send_json(404, {"error": f"Endpoint '{path}' not found"})

    # -----------------------------------------------------------------------
    # DELETE Endpoints
    # -----------------------------------------------------------------------
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Delete User
        if path.startswith("/api/users/"):
            user_id_str = path.replace("/api/users/", "").strip()
            try:
                uid = int(user_id_str)
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
                conn.commit()
                deleted = cursor.rowcount
                conn.close()
                if deleted > 0:
                    self.send_json(200, {"success": True, "message": f"User {uid} deleted successfully."})
                else:
                    self.send_json(404, {"error": f"User {uid} not found."})
            except ValueError:
                self.send_json(400, {"error": "Invalid user ID."})
            return

        # Delete Event
        if path.startswith("/api/events/"):
            event_id_str = path.replace("/api/events/", "").strip()
            try:
                eid = int(event_id_str)
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE id = ?", (eid,))
                conn.commit()
                deleted = cursor.rowcount
                conn.close()
                if deleted > 0:
                    self.send_json(200, {"success": True, "message": f"Event {eid} removed."})
                else:
                    self.send_json(404, {"error": f"Event {eid} not found."})
            except ValueError:
                self.send_json(400, {"error": "Invalid event ID."})
            return

        # Delete Contact Inquiry
        if path.startswith("/api/contact/"):
            msg_id_str = path.replace("/api/contact/", "").strip()
            try:
                mid = int(msg_id_str)
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM contact_messages WHERE id = ?", (mid,))
                conn.commit()
                deleted = cursor.rowcount
                conn.close()
                if deleted > 0:
                    self.send_json(200, {"success": True, "message": f"Inquiry {mid} resolved/deleted."})
                else:
                    self.send_json(404, {"error": f"Inquiry {mid} not found."})
            except ValueError:
                self.send_json(400, {"error": "Invalid message ID."})
            return

        self.send_json(404, {"error": "Not found"})


def main():
    init_db()
    os.chdir(BASE_DIR)

    port_candidates = [PORT, 8000, 5001, 8080, 3000]
    unique_ports = []
    for p in port_candidates:
        if p not in unique_ports:
            unique_ports.append(p)

    server = None
    active_port = None
    for p in unique_ports:
        try:
            server = HTTPServer(("0.0.0.0", p), CompleteCollegeBackendHandler)
            active_port = p
            break
        except OSError as e:
            if getattr(e, 'errno', None) == 48:
                continue
            raise

    if server is None:
        print("❌ Could not bind to any candidate port.")
        sys.exit(1)

    print("=" * 65)
    print(f" 🎓 GL BAJAJ Complete Backend Server Active!")
    print(f" 📍 Local URL:     http://localhost:{active_port}")
    print(f" 🗄️ Database:      SQLite3 ({DB_FILE})")
    print(f" 🗺️ GPS Center:    {CAMPUS_COORDS['lat']}° N, {CAMPUS_COORDS['lng']}° E")
    print("=" * 65)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down backend server.")
        server.server_close()

if __name__ == "__main__":
    main()

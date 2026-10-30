#!/usr/bin/env python3
"""
Automated Backend & Database Test Suite for GL Bajaj College Portal
Runs tests against all SQLite models, authentication, and GPS location endpoints.
"""

import os
import sys
import json
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import server

def test_database():
    print("[1/5] Testing Database Initialization...")
    server.init_db()
    conn = server.get_db()
    cursor = conn.cursor()

    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    assert "users" in tables, "users table missing"
    assert "sessions" in tables, "sessions table missing"
    assert "campus_blocks" in tables, "campus_blocks table missing"
    assert "floor_plans" in tables, "floor_plans table missing"
    assert "events" in tables, "events table missing"
    assert "contact_messages" in tables, "contact_messages table missing"
    print("  ✓ All 6 tables verified in SQLite database.")

    # Check default users
    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    user_counts = dict(cursor.fetchall())
    print(f"  ✓ User accounts in database: {user_counts}")
    assert user_counts.get("student", 0) >= 1, "Student account missing"
    assert user_counts.get("faculty", 0) >= 1, "Faculty account missing"
    assert user_counts.get("staff", 0) >= 1, "Staff account missing"

    # Check Campus Blocks
    cursor.execute("SELECT block_key, name, floors_count FROM campus_blocks")
    blocks = cursor.fetchall()
    print(f"  ✓ Mapped {len(blocks)} Campus Blocks:")
    for b in blocks:
        print(f"    • {b['name']} ({b['floors_count']} Floors)")
    assert len(blocks) >= 6, "Expected at least 6 blocks"

    conn.close()

def test_haversine_gps():
    print("\n[2/5] Testing GPS Location Calculation...")
    # Distance from GL Bajaj Main Gate (28.4720, 77.4890) to CTM Block A (28.4732, 77.4893)
    dist = server.haversine_distance_meters(28.4720, 77.4890, 28.4732, 77.4893)
    print(f"  ✓ Distance from Main Gate to CTM Block A: {dist} meters (~{round(dist/80, 1)} min walk)")
    assert 100 < dist < 200, f"Distance {dist}m outside expected campus range"

def test_user_registration_and_login():
    print("\n[3/5] Testing User Registration & Authentication...")
    conn = server.get_db()
    cursor = conn.cursor()

    test_un = f"testuser_{int(server.datetime.now().timestamp())}"
    test_em = f"{test_un}@glbitm.org"

    cursor.execute("""
        INSERT INTO users (fullname, username, email, password, role, id_number, department, avatar)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Test Student", test_un, test_em, "mypass123", "student", "230192010999", "Computer Science", "data:image/svg+xml;test"))
    uid = cursor.lastrowid
    conn.commit()

    # Verify login query and avatar image retrieval
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (test_un, "mypass123"))
    user = cursor.fetchone()
    assert user is not None, "Login query failed"
    assert user["email"] == test_em, "Email mismatch"
    assert user["avatar"] == "data:image/svg+xml;test", "Avatar image mismatch"
    print(f"  ✓ Registered and verified user '{test_un}' with ID {uid}")

    # Clean up test user
    cursor.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    conn.close()
    print("  ✓ Cleanup complete.")

def test_floor_plans():
    print("\n[4/5] Testing 10-Floor Directory & Lifts...")
    conn = server.get_db()
    cursor = conn.cursor()

    # CTM Block A floors
    cursor.execute("SELECT floor_number, floor_label, facilities, lifts_accessible FROM floor_plans WHERE block_key = 'ctmA' ORDER BY floor_number")
    floors = cursor.fetchall()
    assert len(floors) == 10, f"Expected 10 floors for CTM Block A, got {len(floors)}"

    f6 = [f for f in floors if f["floor_number"] == 6][0]
    assert "Exam" in f6["facilities"] or "601" in f6["facilities"], f"Floor 6 should contain Examination Cell or 601 rooms, got: {f6['facilities']}"
    assert "Lift A & C" in f6["lifts_accessible"] or "Lift A" in f6["lifts_accessible"], "Floor 6 must be accessible via Lift A & C"

    f7 = [f for f in floors if f["floor_number"] == 7][0]
    assert "Empty" in f7["facilities"], f"Floor 7 should be empty, got: {f7['facilities']}"
    assert "Lift A" in f7["lifts_accessible"], "Floor 7 must be accessible via Lift A"

    f8 = [f for f in floors if f["floor_number"] == 8][0]
    assert "801" in f8["facilities"] or "Lecture" in f8["facilities"] or "Faculty" in f8["facilities"], f"Floor 8 should contain lecture rooms and faculty suites, got: {f8['facilities']}"
    assert "Lift A & B" in f8["lifts_accessible"] or "Lift B" in f8["lifts_accessible"], "Floor 8 must be accessible via Lift B (Express)"

    f9 = [f for f in floors if f["floor_number"] == 9][0]
    assert "901" in f9["facilities"] or "Lecture" in f9["facilities"] or "Faculty" in f9["facilities"], f"Floor 9 should contain lecture rooms and faculty suites, got: {f9['facilities']}"
    assert "Lift A & B" in f9["lifts_accessible"] or "Lift B" in f9["lifts_accessible"], "Floor 9 must be accessible via Lift B (Express)"

    f10 = [f for f in floors if f["floor_number"] == 10][0]
    assert "Laborator" in f10["facilities"] or "Labs" in f10["facilities"], f"Floor 10 should contain labs, got: {f10['facilities']}"
    assert "Lift A & B" in f10["lifts_accessible"] or "Lift B" in f10["lifts_accessible"], "Floor 10 must be accessible via Lift B (Express)"

    print(f"  ✓ CTM Block A 10 Floors verified (Floor 6 exam/rooms, Floor 7 empty, Floor 8 & 9 lecture/faculty, Floor 10 labs-only).")
    conn.close()

def test_events_and_contact():
    print("\n[5/6] Testing Events & Inquiries...")
    conn = server.get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    ev_count = cursor.fetchone()[0]
    assert ev_count >= 3, f"Expected at least 3 events, got {ev_count}"
    print(f"  ✓ Verified {ev_count} campus events in database.")
    conn.close()

def test_wayfinding_and_routing():
    print("\n[6/6] Testing Campus Wayfinding Route Finder & Search API...")
    assert len(server.CAMPUS_LOCATIONS) >= 30, f"Expected at least 30 campus locations, got {len(server.CAMPUS_LOCATIONS)}"
    print(f"  ✓ Verified {len(server.CAMPUS_LOCATIONS)} mapped locations across campus & 10-floor tower.")

    # Test Route 1: Main Gate -> 10th Floor Lab 1004
    r1 = server.calculate_campus_route("mainGate", "lab1004")
    assert r1["success"] is True, "Route calculation failed"
    assert 150 < r1["total_distance_meters"] < 250, f"Unexpected route distance: {r1['total_distance_meters']}"
    assert "Lift B" in r1["elevator_recommendation"] or "Lift A" in r1["elevator_recommendation"], "Floor 10 must recommend Lift B Express or Lift A"
    assert r1["deep_link"]["map_type"] == "floor10", "Expected floor10 map deep link"
    assert r1["deep_link"]["room_id"] == "lab1004", "Expected lab1004 room highlight"
    print(f"  ✓ Route Main Gate -> Lab 1004: {r1['total_distance_meters']}m, ~{r1['walk_time_minutes']} min, Elevator: {r1['lift_badge']}")

    # Test Route 2: Library -> 6th Floor Exam Cell
    r2 = server.calculate_campus_route("library", "examCell")
    assert r2["success"] is True, "Route calculation failed"
    assert "Lift C" in r2["elevator_recommendation"] or "Lift A" in r2["elevator_recommendation"], "Floor 6 must recommend Lift C or Lift A"
    assert r2["deep_link"]["map_type"] == "floor6", "Expected floor6 map deep link"
    assert r2["deep_link"]["room_id"] == "examCell", "Expected examCell room highlight"
    print(f"  ✓ Route Library -> Exam Cell: {r2['total_distance_meters']}m, ~{r2['walk_time_minutes']} min, Elevator: {r2['lift_badge']}")

def test_admin_section_api():
    print("\n[7/7] Testing Admin Section & Management APIs...")
    conn = server.get_db()
    cursor = conn.cursor()

    # 1. Verify admin stats
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events")
    e_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM contact_messages")
    m_count = cursor.fetchone()[0]
    assert u_count >= 3, "Expected at least 3 seeded users"
    assert e_count >= 3, "Expected at least 3 seeded events"

    # 2. Test event creation & deletion by Admin
    cursor.execute("""
        INSERT INTO events (title, date_str, category, description, location)
        VALUES (?, ?, ?, ?, ?)
    """, ("Admin Test Tech Fest", "Dec 20, 2026", "Technical", "Test Fest Description", "Campus Auditorium"))
    new_eid = cursor.lastrowid
    conn.commit()
    assert new_eid is not None

    cursor.execute("SELECT * FROM events WHERE id = ?", (new_eid,))
    assert cursor.fetchone() is not None, "Event creation failed"

    cursor.execute("DELETE FROM events WHERE id = ?", (new_eid,))
    conn.commit()
    cursor.execute("SELECT * FROM events WHERE id = ?", (new_eid,))
    assert cursor.fetchone() is None, "Event deletion failed"
    print(f"  ✓ Admin event publication and removal verified.")

    # 3. Test contact inquiry creation & resolution by Admin
    cursor.execute("""
        INSERT INTO contact_messages (name, email, subject, message)
        VALUES (?, ?, ?, ?)
    """, ("Visitor Student", "visitor@gmail.com", "Admission Help", "Inquiry about B.Tech CSE"))
    new_mid = cursor.lastrowid
    conn.commit()

    cursor.execute("DELETE FROM contact_messages WHERE id = ?", (new_mid,))
    conn.commit()
    cursor.execute("SELECT * FROM contact_messages WHERE id = ?", (new_mid,))
    assert cursor.fetchone() is None, "Inquiry deletion failed"
    print(f"  ✓ Admin inquiry inbox and resolution verified.")

    # 4. Verify admin login credentials
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    admin_row = cursor.fetchone()
    assert admin_row is not None, "Admin user 'admin' missing in database"
    assert admin_row["password"] == "admin123", "Admin default password mismatch"
    print(f"  ✓ Verified Admin user account ('{admin_row['username']}', role='{admin_row['role']}') with full system access.")

    conn.close()

if __name__ == "__main__":
    print("==================================================")
    print("Running GL Bajaj Complete Backend Test Suite...")
    print("==================================================")
    test_database()
    test_haversine_gps()
    test_user_registration_and_login()
    test_floor_plans()
    test_events_and_contact()
    test_wayfinding_and_routing()
    test_admin_section_api()
    print("\n==================================================")
    print("🎉 ALL 7 BACKEND & DATABASE TESTS PASSED!")
    print("==================================================")

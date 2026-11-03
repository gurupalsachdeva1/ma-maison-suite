"""
app.py
======
FastAPI Collaborative Server & API Engine for Ma Maison Executive BI Suite.
Runs on 0.0.0.0:8050 to support both native Desktop application
and real-time LAN sharing across office colleagues.
"""

import os
import io
import csv
import socket
import secrets
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

import database

app = FastAPI(title="Ma Maison - Executive BI Suite", version="2.0.0")

# Enable Cross-Origin requests and allow Google Sites iframe embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_and_iframe_headers(request: Request, call_next):
    response = await call_next(request)
    # Allow embedding inside Google Sites (e.g. sites.google.com/mamaison.in/...)
    if "x-frame-options" in response.headers:
        del response.headers["x-frame-options"]
    response.headers["Content-Security-Policy"] = "frame-ancestors * self https://*.google.com https://sites.google.com;"
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR, exist_ok=True)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def find_template(filename: str):
    """Finds template file checking templates/ subfolder, root directory, and cwd."""
    candidates = [
        os.path.join(TEMPLATES_DIR, filename),
        os.path.join(BASE_DIR, filename),
        os.path.join(os.getcwd(), "templates", filename),
        os.path.join(os.getcwd(), filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def find_static_file(filename: str):
    """Finds static file checking static/, static/img/, root directory, and cwd."""
    candidates = [
        os.path.join(STATIC_DIR, "img", filename),
        os.path.join(STATIC_DIR, filename),
        os.path.join(BASE_DIR, "static", "img", filename),
        os.path.join(BASE_DIR, "static", filename),
        os.path.join(BASE_DIR, filename),
        os.path.join(os.getcwd(), filename),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# In-memory session store (token -> user dict)
SESSIONS = {}

def get_lan_ip():
    """Detects the host machine's actual LAN IP address for office colleague sharing."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# --- Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ProjectCreateRequest(BaseModel):
    code: Optional[str] = None
    client: str
    start_date: Optional[str] = None
    description: str
    vendor: str
    owner: str
    status: Optional[str] = "In Progress"
    category: str
    remarks: Optional[str] = ""

class ProjectUpdateRequest(BaseModel):
    code: Optional[str] = None
    client: str
    start_date: str
    description: str
    vendor: str
    owner: str
    status: str
    category: str
    remarks: Optional[str] = ""

class ProjectCodeUpdateRequest(BaseModel):
    code: str

class ProjectStatusUpdateRequest(BaseModel):
    status: str

class BulkDeleteRequest(BaseModel):
    ids: List[int]

class ActionCreateRequest(BaseModel):
    project_code: Optional[str] = ""
    client: str
    task_title: str
    priority: Optional[str] = "Medium"
    due_date: Optional[str] = None
    lane: Optional[str] = "Action Required"
    owner: Optional[str] = ""

class ActionMoveRequest(BaseModel):
    lane: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    email: Optional[str] = ""

class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: str
    branch: Optional[str] = "Delhi HQ"
    department: Optional[str] = "Merchandising"
    phone: Optional[str] = ""

class ForgotPasswordRequest(BaseModel):
    username_or_email: str
    notes: Optional[str] = ""

class ApproveUserRequest(BaseModel):
    user_id: int
    role: Optional[str] = "merchandiser"
    branch: Optional[str] = "Delhi HQ"
    department: Optional[str] = "Merchandising"

class RejectUserRequest(BaseModel):
    user_id: int

class AdminProvisionRequest(BaseModel):
    username: str
    password: str
    full_name: str
    role: str
    branch: str
    department: str
    email: Optional[str] = ""
    phone: Optional[str] = ""

class AdminResetPasswordRequest(BaseModel):
    user_id: int
    new_password: str
    reset_request_id: Optional[int] = None

class AdminToggleStatusRequest(BaseModel):
    user_id: int
    status: str

# --- Dependency ---
def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        return SESSIONS[token]
    return None

def require_admin(user = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required. Please login as Admin.")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Administrator access required.")
    return user

# --- Static File Fallback Routes (Supports flat GitHub uploads) ---
@app.get("/static/img/{filename}")
def serve_static_img(filename: str):
    p = find_static_file(filename)
    if p and os.path.exists(p):
        return FileResponse(p)
    raise HTTPException(status_code=404, detail="Image not found")

@app.get("/static/{filename}")
def serve_static_root(filename: str):
    p = find_static_file(filename)
    if p and os.path.exists(p):
        return FileResponse(p)
    raise HTTPException(status_code=404, detail="File not found")

# --- HTML Serving Routes ---
@app.get("/", response_class=HTMLResponse)
def serve_home():
    """Serves the Ma Maison Corporate Export Home Page."""
    path = find_template("home.html")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Ma Maison Corporate Export Portal - Initializing...</h1>"

@app.get("/portal", response_class=HTMLResponse)
def serve_portal():
    """Serves the Executive BI Suite Tracker & Analytics."""
    path = find_template("index.html")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Ma Maison Executive BI Suite - Initializing...</h1>"

@app.get("/admin", response_class=HTMLResponse)
def serve_admin():
    """Serves the Admin User Governance & Credentials Provisioning Console."""
    path = find_template("admin.html")
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Ma Maison Admin Console - Initializing...</h1>"

# --- Network & Colleague Discovery API ---
@app.get("/api/network-info")
def get_network_info():
    lan_ip = get_lan_ip()
    port = 8050
    return {
        "hostname": socket.gethostname(),
        "lan_ip": lan_ip,
        "port": port,
        "local_url": f"http://localhost:{port}",
        "colleague_url": f"http://{lan_ip}:{port}",
        "sharing_active": True
    }

# --- Auth APIs ---
@app.post("/api/auth/login")
def api_login(req: LoginRequest, response: Response):
    result = database.authenticate(req.username, req.password)
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    
    user = result["user"]
    token = secrets.token_hex(24)
    SESSIONS[token] = user
    response.set_cookie(key="session_token", value=token, max_age=86400 * 7, httponly=False)
    
    redirect_url = "/admin" if user["role"] == "admin" else "/portal"
    return {
        "success": True,
        "token": token,
        "user": user,
        "redirect": redirect_url
    }

@app.post("/api/auth/register-request")
def api_register_request(req: RegisterRequest):
    ok, msg = database.register_user_request(req.model_dump())
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/auth/forgot-password")
def api_forgot_password(req: ForgotPasswordRequest):
    ok, msg = database.request_password_reset(req.username_or_email, req.notes)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/auth/me")
def api_me(user = Depends(get_current_user)):
    if not user:
        return {"authenticated": False, "user": None}
    return {
        "authenticated": True,
        "user": user
    }

@app.post("/api/auth/logout")
def api_logout(request: Request, response: Response):
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    if not token:
        token = request.cookies.get("session_token")
    if token and token in SESSIONS:
        del SESSIONS[token]
    response.delete_cookie(key="session_token")
    return {"status": "logged_out"}

# --- Admin Governance APIs (Protected for Admin) ---
@app.get("/api/admin/overview")
def api_admin_overview(admin = Depends(require_admin)):
    return database.get_admin_overview()

@app.post("/api/admin/approve-user")
def api_admin_approve_user(req: ApproveUserRequest, admin = Depends(require_admin)):
    ok, msg = database.admin_approve_user(req.user_id, req.role, req.branch, req.department, admin["username"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/admin/reject-user")
def api_admin_reject_user(req: RejectUserRequest, admin = Depends(require_admin)):
    ok, msg = database.admin_reject_user(req.user_id, admin["username"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/admin/create-user")
def api_admin_create_user(req: AdminProvisionRequest, admin = Depends(require_admin)):
    ok, msg = database.admin_provision_user(
        req.username, req.password, req.full_name, req.role, req.branch, 
        req.department, req.email, req.phone, admin["username"]
    )
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/admin/reset-password")
def api_admin_reset_password(req: AdminResetPasswordRequest, admin = Depends(require_admin)):
    ok, msg = database.admin_reset_password(req.user_id, req.new_password, req.reset_request_id, admin["username"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.post("/api/admin/toggle-status")
def api_admin_toggle_status(req: AdminToggleStatusRequest, admin = Depends(require_admin)):
    ok, msg = database.admin_toggle_user_status(req.user_id, req.status, admin["username"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.delete("/api/admin/users/{user_id}")
def api_admin_delete_user(user_id: int, admin = Depends(require_admin)):
    ok, msg = database.admin_delete_user(user_id, admin["username"])
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}

@app.get("/api/users")
def api_list_users():
    return database.get_all_users()

# --- Projects APIs ---
@app.get("/api/projects")
def api_get_projects(query: str = "", client: str = "ALL", status: str = "ALL", vendor: str = "ALL", category: str = "ALL"):
    return database.get_projects(query=query, client=client, status=status, vendor=vendor, category=category)

@app.post("/api/projects")
def api_create_project(req: ProjectCreateRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    new_id, code = database.create_project(req.model_dump(), username=uname)
    return {"status": "created", "id": new_id, "code": code}

@app.put("/api/projects/{project_id}")
def api_update_project(project_id: int, req: ProjectUpdateRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    ok, res = database.update_project(project_id, req.model_dump(), username=uname)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return {"status": "updated", "message": res}

@app.patch("/api/projects/{project_id}/code")
def api_update_project_code(project_id: int, req: ProjectCodeUpdateRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    ok, res = database.update_project_code(project_id, req.code, username=uname)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return {"status": "updated", "id": project_id, "code": res}

@app.patch("/api/projects/{project_id}/status")
def api_update_project_status(project_id: int, req: ProjectStatusUpdateRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    ok, res = database.update_project_status(project_id, req.status, username=uname)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    return {"status": "updated", "id": project_id, "message": res}

@app.delete("/api/projects/{project_id}")
def api_delete_project(project_id: int, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    database.delete_project(project_id, username=uname)
    return {"status": "deleted"}

@app.post("/api/projects/bulk-delete")
def api_bulk_delete_projects(req: BulkDeleteRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    ok, count = database.bulk_delete_projects(req.ids, username=uname)
    return {"status": "deleted", "count": count}

@app.get("/api/projects/export-csv")
def api_export_csv():
    """Generates clean CSV matching the original Excel spreadsheet."""
    projects = database.get_projects()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Client", "Start Date", "Task Description", "Vendor", "Owner", "Status", "Category", "Remarks"])
    for p in projects:
        writer.writerow([
            p["code"],
            p["client"],
            p["start_date"],
            p["description"],
            p["vendor"],
            p["owner"],
            p["status"],
            p["category"],
            p.get("remarks") or ""
        ])
    output.seek(0)
    output_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(output_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="ma_maison_master_tracker.csv"'}
    )

# --- Daily Actions (Kanban) APIs ---
@app.get("/api/actions")
def api_get_actions():
    return database.get_daily_actions()

@app.post("/api/actions")
def api_create_action(req: ActionCreateRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    new_id = database.create_daily_action(req.model_dump(), username=uname)
    return {"status": "created", "id": new_id}

@app.put("/api/actions/{action_id}/lane")
def api_move_action(action_id: int, req: ActionMoveRequest, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    database.update_action_lane(action_id, req.lane, username=uname)
    return {"status": "moved", "lane": req.lane}

@app.delete("/api/actions/{action_id}")
def api_delete_action(action_id: int, user = Depends(get_current_user)):
    uname = user["username"] if user else "Sarah M."
    database.delete_action(action_id, username=uname)
    return {"status": "deleted"}

# --- Executive BI Aggregations API ---
@app.get("/api/bi")
def api_get_bi():
    return database.get_bi_analytics()


# --- Advanced Calendar API Routes (Reminders, Appointments, Meetings, Milestones) ---
class CalendarEventCreateRequest(BaseModel):
    title: str
    event_type: str = "Meeting"  # 'Reminder', 'Appointment', 'Meeting', 'Other'
    start_date: str              # YYYY-MM-DD
    start_time: Optional[str] = "10:00"
    end_time: Optional[str] = "11:00"
    client: Optional[str] = ""
    location: Optional[str] = ""
    attendees: Optional[str] = ""
    priority: Optional[str] = "Normal"
    notes: Optional[str] = ""
    status: Optional[str] = "Scheduled"

@app.get("/api/calendar/events")
def api_get_calendar_events(month: Optional[str] = None, year: Optional[str] = None, event_type: Optional[str] = None, client: Optional[str] = None):
    events = database.get_calendar_events(month=month, year=year, event_type=event_type, client=client)
    return {"events": events}

@app.post("/api/calendar/events")
def api_create_calendar_event(req: CalendarEventCreateRequest, user = Depends(get_current_user)):
    uname = user["full_name"] if user else "Tawal Preet Singh"
    data = req.dict()
    data["created_by"] = uname
    new_id = database.create_calendar_event(data)
    return {"status": "created", "id": new_id}

@app.put("/api/calendar/events/{event_id}")
def api_update_calendar_event(event_id: int, req: CalendarEventCreateRequest):
    success = database.update_calendar_event(event_id, req.dict())
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "updated"}

@app.delete("/api/calendar/events/{event_id}")
def api_delete_calendar_event(event_id: int):
    success = database.delete_calendar_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"status": "deleted"}

@app.get("/api/calendar/export-ics")
def api_export_calendar_ics():
    """Generates standard RFC 5545 iCalendar (.ics) file compatible with Google Calendar, Outlook, and Apple Calendar."""
    events = database.get_calendar_events()
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Ma Maison Suite//Executive BI Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Ma Maison Operations & Appointments"
    ]
    for ev in events:
        s_date = (ev["start_date"] or "2026-11-01").replace("-", "")
        s_time = (ev["start_time"] or "10:00").replace(":", "") + "00"
        e_time = (ev["end_time"] or "11:00").replace(":", "") + "00"
        dt_start = f"{s_date}T{s_time}"
        dt_end = f"{s_date}T{e_time}"
        now_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:mamaison-cal-{ev['id']}@mamaison.in",
            f"DTSTAMP:{now_ts}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:[{ev['event_type']}] {ev['title']}",
            f"DESCRIPTION:Client: {ev['client']} | Priority: {ev['priority']} | Attendees: {ev['attendees']} | Notes: {ev['notes']}",
            f"LOCATION:{ev['location']}",
            f"STATUS:CONFIRMED",
            "END:VEVENT"
        ])
    ics_lines.append("END:VCALENDAR")
    ics_data = "\r\n".join(ics_lines)
    return Response(
        content=ics_data,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=Ma_Maison_Executive_Calendar.ics"}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8050))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)


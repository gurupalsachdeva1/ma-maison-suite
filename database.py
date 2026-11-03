"""
database.py
===========
SQLite Database Engine for Ma Maison Executive BI Suite.
Manages multi-user authentication, projects master, daily action items (Kanban),
and real-time business intelligence aggregation.
"""

import sqlite3
import os
import hashlib
import secrets
from datetime import datetime

DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ma_maison.db"))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return hashed, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    hashed, _ = hash_password(password, salt)
    return hashed == stored_hash

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # 1. Users Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'merchandiser', -- 'admin', 'manager', 'merchandiser'
        email TEXT,
        avatar TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Projects Master Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        client TEXT NOT NULL,
        start_date TEXT NOT NULL,
        description TEXT NOT NULL,
        vendor TEXT NOT NULL,
        owner TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'In Progress', -- 'In Progress', 'Completed', 'Pending Approval', 'On Hold', 'Dropped'
        category TEXT NOT NULL,
        remarks TEXT,
        created_by TEXT DEFAULT 'System',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Daily Action Items (Kanban Board)
    c.execute("""
    CREATE TABLE IF NOT EXISTS daily_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_code TEXT,
        client TEXT NOT NULL,
        task_title TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Medium', -- 'High', 'Medium', 'Low'
        due_date TEXT,
        lane TEXT NOT NULL DEFAULT 'Action Required', -- 'Action Required', 'In Progress', 'Pending Approval', 'Completed'
        owner TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 4. Audit Trail Log
    c.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. Password Reset Requests Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        full_name TEXT,
        email TEXT,
        branch TEXT DEFAULT 'Delhi HQ',
        notes TEXT,
        status TEXT DEFAULT 'pending', -- 'pending', 'resolved'
        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        temp_password TEXT
    )
    """)

    # Schema migration: Ensure all required columns exist in users table
    c.execute("PRAGMA table_info(users)")
    existing_cols = [col[1] for col in c.fetchall()]

    if "is_approved" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN is_approved INTEGER DEFAULT 1")
    if "status" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if "branch" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN branch TEXT DEFAULT 'Delhi HQ'")
    if "department" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'Merchandising'")
    if "phone" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
    if "requested_at" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN requested_at TEXT DEFAULT ''")
    if "plain_password" not in existing_cols:
        c.execute("ALTER TABLE users ADD COLUMN plain_password TEXT DEFAULT ''")

    conn.commit()

    # Make sure default users have is_approved=1, status='active', and plain_password populated
    c.execute("UPDATE users SET is_approved = 1, status = 'active' WHERE is_approved IS NULL OR is_approved = 0")
    c.execute("UPDATE users SET branch = 'Delhi HQ' WHERE branch IS NULL OR branch = ''")
    c.execute("UPDATE users SET department = 'Merchandising' WHERE department IS NULL OR department = ''")
    c.execute("UPDATE users SET plain_password = 'admin123' WHERE username = 'admin' AND (plain_password IS NULL OR plain_password = '')")
    c.execute("UPDATE users SET plain_password = 'sarah123' WHERE username = 'sarah' AND (plain_password IS NULL OR plain_password = '')")
    c.execute("UPDATE users SET plain_password = 'priya123' WHERE username = 'priya' AND (plain_password IS NULL OR plain_password = '')")
    c.execute("UPDATE users SET plain_password = 'alex123' WHERE username = 'alex' AND (plain_password IS NULL OR plain_password = '')")
    c.execute("UPDATE users SET plain_password = 'david123' WHERE username = 'david' AND (plain_password IS NULL OR plain_password = '')")
    conn.commit()

    # Seed Default Users if none exist
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        default_users = [
            ("admin", "admin123", "Tawal Preet Singh", "admin", "tawal.singh@mamaison.in"),
            ("sarah", "sarah123", "Sarah M.", "manager", "sarah.m@mamaison.in"),
            ("priya", "priya123", "Priya K.", "manager", "priya.k@mamaison.in"),
            ("alex", "alex123", "Alex R.", "merchandiser", "alex.r@mamaison.in"),
            ("david", "david123", "David L.", "merchandiser", "david.l@mamaison.in")
        ]
        for uname, pwd, fname, role, email in default_users:
            h, s = hash_password(pwd)
            c.execute("""
            INSERT INTO users (username, password_hash, salt, full_name, role, email)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (uname, h, s, fname, role, email))
        conn.commit()

    # Seed 14 Projects exactly from screenshots if none exist
    c.execute("SELECT COUNT(*) FROM projects")
    if c.fetchone()[0] == 0:
        seed_projects = [
            ("PRJ-014", "CBC", "2023-04-22", "Quilted Mattress Protector Factory Audit", "Jiangsu Terry Co.", "Priya K.", "Completed", "Compliance", "BSCI audit scored Grade A."),
            ("PRJ-013", "JACENT", "2023-04-18", "Bamboo Blend Sheet Set Softness Wash Test", "Nantong Home", "Sarah M.", "In Progress", "Quality Assurance", "5th cycle wash completed."),
            ("PRJ-012", "DOLLAR TREE", "2023-04-12", "Value Kitchen Apron 3-pack Polybag Design", "Shaoxing Textile Co.", "Alex R.", "Dropped", "Packaging", "Buyer cancelled SKU requirement."),
            ("PRJ-011", "NASIMI/OMAR", "2023-04-05", "Custom Embroidered Hand Towels Bulk Quote", "Jiangsu Terry Co.", "Sarah M.", "Pending Approval", "Pricing", "Quote submitted to buyer."),
            ("PRJ-010", "BEST S", "2023-04-01", "Spring Floral Printed Curtains Pre-production", "Nantong Home", "David L.", "In Progress", "Production", "Print strike-off approved."),
            ("PRJ-009", "LINEN HOUSE", "2023-03-20", "Woven Cotton Rug Spec Sheet Updates", "Panipat Mills", "Alex R.", "Completed", "Product Dev", "Updated GSM specs distributed."),
            ("PRJ-008", "CBC", "2023-03-15", "Outdoor Canvas Pillow Water-repellent Coating", "Zhejiang Crafts", "Priya K.", "On Hold", "R&D", "Paused due to chemical compliance review."),
            ("PRJ-007", "JACENT", "2023-03-10", "Holiday 24 Oven Mitt Set Fabric Testing", "Shaoxing Textile Co.", "Sarah M.", "In Progress", "Compliance", "Heat resistance test results expected Friday."),
            ("PRJ-006", "DOLLAR TREE", "2023-03-02", "Everyday Microfiber Dishcloth Bulk Order Audit", "Jiangsu Terry Co.", "Alex R.", "Completed", "Quality Assurance", "Passed AQL 2.5 inspection standard."),
            ("PRJ-005", "NASIMI/OMAR", "2023-02-18", "Luxury Velvet Cushion Range Sample Dispatch", "Qingdao Home", "Sarah M.", "In Progress", "Sampling", "Courier tracking"),
            ("PRJ-004", "BEST S", "2023-02-10", "Jacquard Table Runner Gold Thread Sampling", "Shaoxing Textile Co.", "David L.", "In Progress", "Production", "Loom setup ready for trial run."),
            ("PRJ-003", "LINEN HOUSE", "2023-01-28", "Egyptian Cotton Bedding Set Yarn Sourcing", "Panipat Mills", "Alex R.", "Completed", "Product Dev", "600 thread count approved."),
            ("PRJ-002", "CBC", "2023-01-15", "Waterproof Mattress Encasement Lab Certification", "Zhejiang Crafts", "Priya K.", "In Progress", "Compliance", "Awaiting OEKO-TEX certificate renewal."),
            ("PRJ-001", "JACENT", "2023-01-05", "Organic Cotton Bath Mat Development", "Shaoxing Textile Co.", "Sarah M.", "In Progress", "Product Dev", "Initial color swatches approved by buyer.")
        ]
        for p in seed_projects:
            c.execute("""
            INSERT INTO projects (code, client, start_date, description, vendor, owner, status, category, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, p)
        conn.commit()

    # Seed Daily Action Items (Kanban) from screenshot
    c.execute("SELECT COUNT(*) FROM daily_actions")
    if c.fetchone()[0] == 0:
        seed_actions = [
            ("PRJ-007", "JACENT", "Follow up with Shaoxing on lab dip shade B approval", "High", "2026-11-01", "Action Required", "Sarah M."),
            ("PRJ-014", "CBC", "Negotiate container freight rates with Maersk rep", "High", "2026-11-02", "Action Required", "Priya K."),
            ("PRJ-001", "JACENT", "Schedule Q4 product review call with procurement VP", "High", "2026-11-04", "Action Required", "Sarah M."),
            ("PRJ-010", "BEST S", "Verify master carton weight for placemat shipment", "Low", "2026-11-02", "In Progress", "David L."),
            ("PRJ-005", "NASIMI/OMAR", "Confirm DHL express tracking for luxury velvet swatches", "High", "2026-11-03", "In Progress", "Sarah M."),
            ("PRJ-009", "LINEN HOUSE", "Send revised tech packs for SS24 rug collections", "Medium", "2026-11-01", "Pending Approval", "Alex R."),
            ("PRJ-006", "DOLLAR TREE", "Update item master with new UPC codes for dishcloths", "Medium", "2026-11-03", "Completed", "Alex R.")
        ]
        for a in seed_actions:
            c.execute("""
            INSERT INTO daily_actions (project_code, client, task_title, priority, due_date, lane, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, a)
        conn.commit()

    conn.close()

# Initialize DB on import
init_db()

# --- Auth & User Management Functions ---
def authenticate(username, password):
    conn = get_connection()
    c = conn.cursor()
    uname = username.strip().lower()
    c.execute("""
        SELECT id, username, password_hash, salt, full_name, role, email, is_approved, status, branch, department, avatar 
        FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?
    """, (uname, uname))
    u = c.fetchone()
    conn.close()
    
    if not u:
        return {"success": False, "error": "Invalid username or password."}
    if not verify_password(password, u["password_hash"], u["salt"]):
        return {"success": False, "error": "Invalid username or password."}
    
    # Check admin approval restriction: only admin or admin-approved accounts can log in
    if u["is_approved"] == 0 or u["status"] == "pending":
        return {
            "success": False, 
            "error": "Access Denied: Your account is currently PENDING ADMIN APPROVAL. The Administrator has not granted login access yet. Please contact Admin."
        }
    if u["status"] == "suspended":
        return {
            "success": False, 
            "error": "Account Suspended: Please contact System Administrator."
        }
        
    return {
        "success": True,
        "user": {
            "id": u["id"],
            "username": u["username"],
            "full_name": u["full_name"],
            "role": u["role"],
            "email": u["email"],
            "branch": u["branch"] or "Delhi HQ",
            "department": u["department"] or "Merchandising",
            "avatar": u["avatar"] or ""
        }
    }

def register_user_request(data):
    """Called when an employee submits the Create New Account form. Requires Admin approval."""
    conn = get_connection()
    c = conn.cursor()
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    branch = data.get("branch", "Delhi HQ").strip()
    department = data.get("department", "Merchandising").strip()
    phone = data.get("phone", "").strip()

    if not username or not password or not full_name:
        conn.close()
        return False, "Username, Password, and Full Name are required."

    c.execute("SELECT id FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (username, email))
    if c.fetchone():
        conn.close()
        return False, f"Username '{username}' or email '{email}' already registered."

    h, s = hash_password(password)
    c.execute("""
        INSERT INTO users (username, password_hash, salt, full_name, role, email, is_approved, status, branch, department, phone, plain_password)
        VALUES (?, ?, ?, ?, 'merchandiser', ?, 0, 'pending', ?, ?, ?, ?)
    """, (username, h, s, full_name, email, branch, department, phone, password))

    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'SIGNUP_REQUEST', ?)
    """, (username, f"New employee account requested from {branch} ({department})"))
    
    conn.commit()
    conn.close()
    return True, "Your account request has been submitted to the Admin. Login will be enabled once Admin approves your credentials."

def request_password_reset(username_or_email, notes=""):
    conn = get_connection()
    c = conn.cursor()
    val = username_or_email.strip().lower()
    c.execute("SELECT id, username, full_name, email, branch FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?", (val, val))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "No registered account found with that username or email."
    
    c.execute("""
        INSERT INTO password_resets (user_id, username, full_name, email, branch, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (u["id"], u["username"], u["full_name"], u["email"], u["branch"], notes))
    
    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'PASSWORD_RESET_REQUESTED', ?)
    """, (u["username"], f"Password reset requested for {u['username']} ({u['branch']})"))

    conn.commit()
    conn.close()
    return True, "Password reset request submitted to Admin. Admin will provide new credentials."

def get_admin_overview():
    conn = get_connection()
    c = conn.cursor()
    
    # Counts
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE is_approved = 0 OR status = 'pending'")
    pending_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE is_approved = 1 AND status = 'active'")
    active_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM password_resets WHERE status = 'pending'")
    pending_resets_count = c.fetchone()[0]

    # Pending approvals
    c.execute("""
        SELECT id, username, full_name, role, email, branch, department, phone, requested_at, status, plain_password
        FROM users WHERE is_approved = 0 OR status = 'pending'
        ORDER BY id DESC
    """)
    pending_users = [dict(r) for r in c.fetchall()]

    # All users roster
    c.execute("""
        SELECT id, username, full_name, role, email, branch, department, phone, is_approved, status, plain_password, created_at, avatar
        FROM users ORDER BY id ASC
    """)
    all_users = [dict(r) for r in c.fetchall()]

    # Password resets
    c.execute("""
        SELECT id, user_id, username, full_name, email, branch, notes, status, requested_at, temp_password
        FROM password_resets ORDER BY id DESC LIMIT 20
    """)
    resets = [dict(r) for r in c.fetchall()]

    # Recent Audit logs
    c.execute("SELECT id, username, action, details, timestamp FROM audit_logs ORDER BY id DESC LIMIT 25")
    logs = [dict(r) for r in c.fetchall()]

    conn.close()
    return {
        "stats": {
            "total_users": total_users,
            "pending_approvals": pending_count,
            "active_users": active_count,
            "pending_resets": pending_resets_count
        },
        "pending_users": pending_users,
        "all_users": all_users,
        "resets": resets,
        "logs": logs
    }

def admin_approve_user(user_id, role="merchandiser", branch="Delhi HQ", department="Merchandising", admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "User not found"
    
    c.execute("""
        UPDATE users 
        SET is_approved = 1, status = 'active', role = ?, branch = ?, department = ?
        WHERE id = ?
    """, (role, branch, department, user_id))
    
    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_APPROVE_USER', ?)
    """, (admin_uname, f"Approved user {u['username']} with role={role}, branch={branch}"))
    
    conn.commit()
    conn.close()
    return True, f"User '{u['username']}' approved and activated successfully."

def admin_reject_user(user_id, admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "User not found"
    
    username = u["username"]
    c.execute("DELETE FROM users WHERE id = ? AND is_approved = 0", (user_id,))
    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_REJECT_USER', ?)
    """, (admin_uname, f"Rejected pending request for {username}"))
    conn.commit()
    conn.close()
    return True, f"User request for '{username}' was rejected."

def admin_provision_user(username, password, full_name, role, branch, department, email, phone, admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    uname = username.strip().lower()
    c.execute("SELECT id FROM users WHERE LOWER(username) = ?", (uname,))
    if c.fetchone():
        conn.close()
        return False, f"Username '{uname}' already exists."

    h, s = hash_password(password)
    c.execute("""
        INSERT INTO users (username, password_hash, salt, full_name, role, email, is_approved, status, branch, department, phone, plain_password)
        VALUES (?, ?, ?, ?, ?, ?, 1, 'active', ?, ?, ?, ?)
    """, (uname, h, s, full_name.strip(), role, email.strip().lower(), branch, department, phone.strip(), password))

    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_PROVISION_USER', ?)
    """, (admin_uname, f"Directly provisioned employee {uname} for {branch} ({role})"))
    
    conn.commit()
    conn.close()
    return True, f"Employee credentials for '{uname}' provisioned successfully."

def admin_reset_password(user_id, new_password, reset_request_id=None, admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "User not found"
    
    h, s = hash_password(new_password)
    c.execute("UPDATE users SET password_hash = ?, salt = ?, plain_password = ? WHERE id = ?", (h, s, new_password, user_id))
    
    if reset_request_id:
        c.execute("""
            UPDATE password_resets 
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP, temp_password = ?
            WHERE id = ?
        """, (new_password, reset_request_id))

    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_RESET_PASSWORD', ?)
    """, (admin_uname, f"Password reset by admin for user {u['username']}"))

    conn.commit()
    conn.close()
    return True, f"Password for '{u['username']}' updated successfully."

def admin_toggle_user_status(user_id, new_status, admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "User not found"
    if u["username"] == "admin":
        conn.close()
        return False, "Cannot suspend or deactivate primary Admin account."

    c.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_TOGGLE_STATUS', ?)
    """, (admin_uname, f"User {u['username']} status changed to {new_status}"))

    conn.commit()
    conn.close()
    return True, f"User '{u['username']}' is now {new_status}."

def admin_delete_user(user_id, admin_uname="admin"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
    u = c.fetchone()
    if not u:
        conn.close()
        return False, "User not found"
    if u["username"] == "admin":
        conn.close()
        return False, "Cannot delete primary Admin account."

    username = u["username"]
    c.execute("DELETE FROM users WHERE id = ?", (user_id,))
    c.execute("""
        INSERT INTO audit_logs (username, action, details)
        VALUES (?, 'ADMIN_DELETE_USER', ?)
    """, (admin_uname, f"Deleted user {username}"))

    conn.commit()
    conn.close()
    return True, f"User '{username}' was deleted."

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, username, full_name, role, email, branch, department, is_approved, status, created_at, avatar FROM users ORDER BY id ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

# --- Projects CRUD ---
def get_projects(query="", client="ALL", status="ALL", vendor="ALL", category="ALL"):
    conn = get_connection()
    c = conn.cursor()
    sql = "SELECT * FROM projects WHERE 1=1"
    params = []

    if query:
        q = f"%{query.strip()}%"
        sql += " AND (code LIKE ? OR client LIKE ? OR description LIKE ? OR vendor LIKE ? OR owner LIKE ? OR remarks LIKE ?)"
        params.extend([q, q, q, q, q, q])
    if client and client != "ALL":
        sql += " AND client = ?"
        params.append(client)
    if status and status != "ALL":
        sql += " AND status = ?"
        params.append(status)
    if vendor and vendor != "ALL":
        sql += " AND vendor = ?"
        params.append(vendor)
    if category and category != "ALL":
        sql += " AND category = ?"
        params.append(category)

    sql += " ORDER BY id DESC"
    c.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def create_project(data, username="System"):
    conn = get_connection()
    c = conn.cursor()
    # Generate auto project code PRJ-XXX
    c.execute("SELECT id FROM projects ORDER BY id DESC LIMIT 1")
    last_row = c.fetchone()
    next_id = (last_row[0] + 1) if last_row else 1
    code = data.get("code") or f"PRJ-{next_id:03d}"

    c.execute("""
    INSERT INTO projects (code, client, start_date, description, vendor, owner, status, category, remarks, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        code,
        data.get("client"),
        data.get("start_date") or datetime.now().strftime("%Y-%m-%d"),
        data.get("description"),
        data.get("vendor"),
        data.get("owner"),
        data.get("status") or "In Progress",
        data.get("category"),
        data.get("remarks"),
        username
    ))
    new_id = c.lastrowid
    # Log audit
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "CREATE_PROJECT", f"Created {code} for {data.get('client')}"))
    conn.commit()
    conn.close()
    return new_id, code

def update_project_status(project_id, new_status, username="System"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
    row = c.fetchone()
    code = row[0] if row else f"#{project_id}"
    c.execute("UPDATE projects SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, project_id))
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "UPDATE_STATUS", f"Changed status of {code} to {new_status}"))
    conn.commit()
    conn.close()
    return True, f"Status of {code} updated to {new_status}"

def update_project_code(project_id, new_code, username="System"):
    conn = get_connection()
    c = conn.cursor()
    new_code = (new_code or "").strip().upper()
    if not new_code:
        conn.close()
        return False, "Project code cannot be empty"
    
    # Check if duplicate exists for another project
    c.execute("SELECT id FROM projects WHERE code = ? AND id != ?", (new_code, project_id))
    if c.fetchone():
        conn.close()
        return False, f"Code '{new_code}' is already assigned to another project"
        
    c.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Project not found"
    old_code = row[0]
    
    c.execute("UPDATE projects SET code = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_code, project_id))
    # Sync connected daily actions
    c.execute("UPDATE daily_actions SET project_code = ? WHERE project_code = ?", (new_code, old_code))
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "UPDATE_PROJECT_CODE", f"Changed code from '{old_code}' to '{new_code}' for project ID #{project_id}"))
    conn.commit()
    conn.close()
    return True, new_code

def update_project(project_id, data, username="System"):
    conn = get_connection()
    c = conn.cursor()
    
    new_code = (data.get("code") or "").strip().upper()
    if new_code:
        c.execute("SELECT id FROM projects WHERE code = ? AND id != ?", (new_code, project_id))
        if c.fetchone():
            conn.close()
            return False, f"Code '{new_code}' is already assigned to another project"
        
        c.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
        row = c.fetchone()
        old_code = row[0] if row else ""
        
        c.execute("""
        UPDATE projects
        SET code = ?, client = ?, start_date = ?, description = ?, vendor = ?, owner = ?, status = ?, category = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            new_code,
            data.get("client"),
            data.get("start_date"),
            data.get("description"),
            data.get("vendor"),
            data.get("owner"),
            data.get("status"),
            data.get("category"),
            data.get("remarks"),
            project_id
        ))
        if old_code and old_code != new_code:
            c.execute("UPDATE daily_actions SET project_code = ? WHERE project_code = ?", (new_code, old_code))
    else:
        c.execute("""
        UPDATE projects
        SET client = ?, start_date = ?, description = ?, vendor = ?, owner = ?, status = ?, category = ?, remarks = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (
            data.get("client"),
            data.get("start_date"),
            data.get("description"),
            data.get("vendor"),
            data.get("owner"),
            data.get("status"),
            data.get("category"),
            data.get("remarks"),
            project_id
        ))
        
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "UPDATE_PROJECT", f"Updated project ID #{project_id}"))
    conn.commit()
    conn.close()
    return True, "Project updated successfully"

def delete_project(project_id, username="System"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT code FROM projects WHERE id = ?", (project_id,))
    row = c.fetchone()
    code = row[0] if row else f"#{project_id}"
    c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "DELETE_PROJECT", f"Deleted project {code}"))
    conn.commit()
    conn.close()
    return True

def bulk_delete_projects(project_ids, username="System"):
    if not project_ids:
        return True, 0
    conn = get_connection()
    c = conn.cursor()
    placeholders = ",".join(["?"] * len(project_ids))
    c.execute(f"SELECT code FROM projects WHERE id IN ({placeholders})", tuple(project_ids))
    codes = [r[0] for r in c.fetchall()]
    
    c.execute(f"DELETE FROM projects WHERE id IN ({placeholders})", tuple(project_ids))
    deleted_count = c.rowcount
    
    if codes:
        code_placeholders = ",".join(["?"] * len(codes))
        c.execute(f"DELETE FROM daily_actions WHERE project_code IN ({code_placeholders})", tuple(codes))
        
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "BULK_DELETE_PROJECTS", f"Deleted {deleted_count} projects: {', '.join(codes[:5])}"))
    conn.commit()
    conn.close()
    return True, deleted_count

# --- Daily Actions (Kanban) CRUD ---
def get_daily_actions():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM daily_actions ORDER BY id DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def create_daily_action(data, username="System"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO daily_actions (project_code, client, task_title, priority, due_date, lane, owner)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("project_code"),
        data.get("client"),
        data.get("task_title"),
        data.get("priority") or "Medium",
        data.get("due_date") or datetime.now().strftime("%Y-%m-%d"),
        data.get("lane") or "Action Required",
        data.get("owner") or username
    ))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id

def update_action_lane(action_id, new_lane, username="System"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE daily_actions
    SET lane = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (new_lane, action_id))
    c.execute("INSERT INTO audit_logs (username, action, details) VALUES (?, ?, ?)",
              (username, "MOVE_KANBAN_LANE", f"Moved Action #{action_id} to {new_lane}"))
    conn.commit()
    conn.close()
    return True

def delete_action(action_id, username="System"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM daily_actions WHERE id = ?", (action_id,))
    conn.commit()
    conn.close()
    return True

# --- Executive BI Aggregations ---
def get_bi_analytics():
    conn = get_connection()
    c = conn.cursor()

    # 1. Total Projects & Status Counts
    c.execute("SELECT status, COUNT(*) as cnt FROM projects GROUP BY status")
    status_map = {row["status"]: row["cnt"] for row in c.fetchall()}

    total_projects = sum(status_map.values())
    in_progress = status_map.get("In Progress", 0)
    pending_signoff = status_map.get("Pending Approval", 0)
    completed = status_map.get("Completed", 0)
    on_hold = status_map.get("On Hold", 0)
    dropped = status_map.get("Dropped", 0)

    completion_rate = round((completed / total_projects * 100)) if total_projects > 0 else 0

    # 2. Client Workload Distribution
    c.execute("SELECT client, COUNT(*) as count FROM projects GROUP BY client ORDER BY count DESC")
    client_counts = []
    for r in c.fetchall():
        pct = round((r["count"] / total_projects * 100)) if total_projects > 0 else 0
        client_counts.append({
            "client": r["client"],
            "count": r["count"],
            "percentage": pct
        })

    # 3. Vendor Distribution & Operational Volume
    c.execute("""
    SELECT vendor, 
           COUNT(*) as total_vendor_projects,
           SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as done_count
    FROM projects
    GROUP BY vendor
    ORDER BY total_vendor_projects DESC
    """)
    vendor_metrics = []
    for r in c.fetchall():
        t = r["total_vendor_projects"]
        d = r["done_count"]
        v_rate = round((d / t * 100)) if t > 0 else 0
        vendor_metrics.append({
            "vendor": r["vendor"],
            "projects": t,
            "done": d,
            "rate": v_rate
        })

    # 4. Client Account Metrics (with active orders and category tags)
    c.execute("""
    SELECT client, 
           COUNT(*) as active_orders,
           GROUP_CONCAT(DISTINCT category) as categories
    FROM projects
    GROUP BY client
    ORDER BY active_orders DESC
    """)
    client_accounts = []
    for r in c.fetchall():
        cats = [cat.strip() for cat in (r["categories"] or "").split(",") if cat.strip()]
        client_accounts.append({
            "client": r["client"],
            "orders": r["active_orders"],
            "categories": cats
        })

    # 5. Distinct Dropdowns (for Query Builder)
    c.execute("SELECT DISTINCT client FROM projects ORDER BY client ASC")
    clients_list = [r[0] for r in c.fetchall() if r[0]]
    c.execute("SELECT DISTINCT vendor FROM projects ORDER BY vendor ASC")
    vendors_list = [r[0] for r in c.fetchall() if r[0]]
    c.execute("SELECT DISTINCT category FROM projects ORDER BY category ASC")
    categories_list = [r[0] for r in c.fetchall() if r[0]]

    conn.close()

    return {
        "kpis": {
            "total_projects": total_projects,
            "in_progress": in_progress,
            "pending_signoff": pending_signoff,
            "completed": completed,
            "completion_rate": completion_rate,
            "on_hold": on_hold,
            "dropped": dropped
        },
        "client_workload": client_counts,
        "vendor_metrics": vendor_metrics,
        "client_accounts": client_accounts,
        "filter_options": {
            "clients": clients_list,
            "vendors": vendors_list,
            "categories": categories_list,
            "statuses": ["In Progress", "Completed", "Pending Approval", "On Hold", "Dropped"]
        }
    }



# ==============================================================================
# ADVANCED CALENDAR MODULE (Reminders, Appointments, Meetings, Milestones)
# ==============================================================================

def get_calendar_events(month: str = None, year: str = None, event_type: str = None, client: str = None):
    """Retrieves calendar events with optional month, year, type, and client filtering."""
    conn = get_connection()
    c = conn.cursor()
    
    query = "SELECT * FROM calendar_events WHERE 1=1"
    params = []
    
    if year and month:
        prefix = f"{year}-{int(month):02d}"
        query += " AND start_date LIKE ?"
        params.append(f"{prefix}%")
    elif year:
        query += " AND start_date LIKE ?"
        params.append(f"{year}-%")
        
    if event_type and event_type != "All":
        query += " AND event_type = ?"
        params.append(event_type)
        
    if client and client != "ALL":
        query += " AND client = ?"
        params.append(client)
        
    query += " ORDER BY start_date ASC, start_time ASC"
    c.execute(query, params)
    
    events = []
    for r in c.fetchall():
        events.append(dict(r))
        
    conn.close()
    return events


def create_calendar_event(data: dict):
    """Creates a new calendar event (Reminder, Appointment, Meeting, Other)."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("""
    INSERT INTO calendar_events (
        title, event_type, start_date, start_time, end_time, 
        client, location, attendees, priority, notes, status, created_by
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("title", "Untitled Event"),
        data.get("event_type", "Meeting"),
        data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
        data.get("start_time", "10:00"),
        data.get("end_time", "11:00"),
        data.get("client", ""),
        data.get("location", ""),
        data.get("attendees", ""),
        data.get("priority", "Normal"),
        data.get("notes", ""),
        data.get("status", "Scheduled"),
        data.get("created_by", "Tawal Preet Singh")
    ))
    
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_calendar_event(event_id: int, data: dict):
    """Updates an existing calendar event."""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("""
    UPDATE calendar_events SET
        title = ?,
        event_type = ?,
        start_date = ?,
        start_time = ?,
        end_time = ?,
        client = ?,
        location = ?,
        attendees = ?,
        priority = ?,
        notes = ?,
        status = ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (
        data.get("title"),
        data.get("event_type", "Meeting"),
        data.get("start_date"),
        data.get("start_time", "10:00"),
        data.get("end_time", "11:00"),
        data.get("client", ""),
        data.get("location", ""),
        data.get("attendees", ""),
        data.get("priority", "Normal"),
        data.get("notes", ""),
        data.get("status", "Scheduled"),
        event_id
    ))
    
    updated = c.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def delete_calendar_event(event_id: int):
    """Deletes a calendar event by ID."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM calendar_events WHERE id = ?", (event_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

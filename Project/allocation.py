from typing import Optional, List, Dict
import sqlite3

DATABASE_NAME = "tickets.db"

def get_staff_workload() -> Dict[str, int]:
    """Get current workload for all helpers"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
 
        cursor.execute("""
            SELECT assigned_to, COUNT(*) as count
            FROM tickets
            WHERE status NOT IN ('Closed', 'Resolved') AND assigned_to IS NOT NULL
            GROUP BY assigned_to
        """)
        
        workload = {}
        for row in cursor.fetchall():
            workload[row[0]] = row[1]
        

        cursor.execute("SELECT email FROM users WHERE role = 'helper' AND is_active = 1")
        for (email,) in cursor.fetchall():
            if email not in workload:
                workload[email] = 0
        
        conn.close()
        return workload
    except Exception as e:
        print(f"Error getting workload: {e}")
        return {}


def get_available_staff() -> List[Dict]:
    """Get list of all helpers with their current workload"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        

        cursor.execute("""
            SELECT email, name, role
            FROM users
            WHERE role = 'helper' AND is_active = 1
        """)
        
        staff_list = []
        workload = get_staff_workload()
        
        for row in cursor.fetchall():
            email, name, role = row
            current_tickets = workload.get(email, 0)
            max_tickets = 20 
            
            staff_list.append({
                "email": email,
                "name": name,
                "role": role,
                "current_tickets": current_tickets,
                "max_tickets": max_tickets,
                "available_capacity": max_tickets - current_tickets
            })
        
        conn.close()
        
        # Sort by available capacity (most capacity first)
        staff_list.sort(key=lambda x: x["available_capacity"], reverse=True)
        
        return staff_list
    except Exception as e:
        print(f" Error getting available staff: {e}")
        return []


def get_allocation_report():
    """Generate workload distribution report for all helpers"""
    try:
        staff_list = get_available_staff()
        
        if not staff_list:
            print("No helpers found")
            return
        
        print("\n" + "="*60)
        print("HELPER WORKLOAD REPORT")
        print("="*60)
        
        for staff in staff_list:
            bar = "||" * staff['current_tickets']
            capacity = f"{staff['current_tickets']}/{staff['max_tickets']}"
            status = "OK" if staff['current_tickets'] >= staff['max_tickets'] else "NO"
            
            print(f"{status} {staff['name']:20} {bar} {capacity}")
        
        total = sum(s['current_tickets'] for s in staff_list)
        avg = total / len(staff_list) if staff_list else 0
        
        print("-" * 60)
        print(f"Total Active Tickets: {total}")
        print(f"Average per Helper: {avg:.1f}")
        print(f"Total Helpers: {len(staff_list)}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"Error generating report: {e}")


def reassign_ticket(ticket_id: int, new_assignee: str, changed_by: str = "System") -> bool:
    """Reassign a ticket to a different helper"""
    try:
        from database import update_ticket, get_ticket
        
        ticket = get_ticket(ticket_id)
        if not ticket:
            print(f"Ticket #{ticket_id} not found")
            return False
        
        old_assignee = ticket.assigned_to
        update_ticket(ticket_id, assigned_to=new_assignee, changed_by=changed_by)
        
        print(f"Reassigned ticket #{ticket_id}: {old_assignee} → {new_assignee}")
        return True
    except Exception as e:
        print(f"Reassignment error: {e}")
        return False


def get_helper_workload(helper_email: str) -> Dict:
    """Get workload for a specific helper"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Get helper info
        cursor.execute("""
            SELECT name, email FROM users WHERE email = ? AND role = 'helper'
        """, (helper_email,))
        
        helper_row = cursor.fetchone()
        if not helper_row:
            conn.close()
            return {}
        
        name, email = helper_row
        
        # Count active tickets
        cursor.execute("""
            SELECT COUNT(*) FROM tickets
            WHERE assigned_to = ? AND status NOT IN ('Closed', 'Resolved')
        """, (helper_email,))
        
        active_count = cursor.fetchone()[0]
        
        # Count resolved tickets
        cursor.execute("""
            SELECT COUNT(*) FROM tickets
            WHERE assigned_to = ? AND status = 'Resolved'
        """, (helper_email,))
        
        resolved_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "name": name,
            "email": email,
            "active_tickets": active_count,
            "resolved_tickets": resolved_count,
            "total_handled": active_count + resolved_count
        }
    except Exception as e:
        print(f"Error: {e}")
        return {}

import sqlite3
import logging
from typing import Optional, List, Dict

from Project.database import update_ticket, get_ticket, get_all_tickets
from Project.users import is_helper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Get all helpers and set 0 for those with no tickets
        cursor.execute("SELECT email FROM users WHERE role = 'helper' AND is_active = 1")
        for (email,) in cursor.fetchall():
            if email not in workload:
                workload[email] = 0
        
        conn.close()
        return workload
    except Exception as e:
        logger.error(f"Error getting workload: {e}", exc_info=True)
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
        logger.error(f"Error getting available staff: {e}", exc_info=True)
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
            # FIXED: Logic was reversed - now shows FULL when at/over capacity
            status = "FULL" if staff['current_tickets'] >= staff['max_tickets'] else "OK"
            
            print(f"{status:4} {staff['name']:20} {bar} {capacity}")
        
        total = sum(s['current_tickets'] for s in staff_list)
        avg = total / len(staff_list) if staff_list else 0
        
        print("-" * 60)
        print(f"Total Active Tickets: {total}")
        print(f"Average per Helper: {avg:.1f}")
        print(f"Total Helpers: {len(staff_list)}")
        print("="*60 + "\n")
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)


def reassign_ticket(ticket_id: int, new_assignee: str, changed_by: str = "System") -> bool:
    """Reassign a ticket to a different helper"""
    try:
        from database import update_ticket, get_ticket
        
        ticket = get_ticket(ticket_id)
        if not ticket:
            logger.warning(f"Ticket #{ticket_id} not found")
            return False
        
        old_assignee = ticket.assigned_to
        update_ticket(ticket_id, assigned_to=new_assignee, changed_by=changed_by)
        
        logger.info(f"Reassigned ticket #{ticket_id}: {old_assignee} → {new_assignee}")
        return True
    except Exception as e:
        logger.error(f"Reassignment error: {e}", exc_info=True)
        return False


def get_helper_workload(helper_email: str) -> Dict:
    """Get workload for a specific helper"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Get helper info
        cursor.execute("""
            SELECT name, email FROM users WHERE email = ? AND role = 'helper' AND is_active = 1
        """, (helper_email,))
        
        helper_row = cursor.fetchone()
        if not helper_row:
            conn.close()
            logger.warning(f"Helper {helper_email} not found")
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
        logger.error(f"Error getting helper workload: {e}", exc_info=True)
        return {}


def auto_assign_ticket(ticket_id: int, changed_by: str = "System") -> Optional[str]:
    """
    Automatically assign ticket to helper with most available capacity
    Returns the email of assigned helper, or None if no helpers available
    """
    try:
        staff_list = get_available_staff()
        
        if not staff_list:
            logger.warning("No helpers available for auto-assignment")
            return None
        
        # Find helper with most available capacity
        best_helper = staff_list[0]  # Already sorted by capacity
        
        if best_helper['available_capacity'] <= 0:
            logger.warning("All helpers are at full capacity")
            return None
        
        # Assign ticket
        if reassign_ticket(ticket_id, best_helper['email'], changed_by):
            logger.info(f"Auto-assigned ticket #{ticket_id} to {best_helper['name']}")
            return best_helper['email']
        
        return None
    except Exception as e:
        logger.error(f"Error auto-assigning ticket: {e}", exc_info=True)
        return None


def balance_workload(changed_by: str = "System") -> Dict[str, int]:
    """
    Balance workload across all helpers by reassigning tickets
    Returns dict with reassignment counts
    """
    try:
        from database import get_all_tickets
        
        staff_list = get_available_staff()
        if len(staff_list) < 2:
            logger.info("Not enough helpers for balancing")
            return {"reassigned": 0}
        
        # Find overloaded and underloaded helpers
        avg_load = sum(s['current_tickets'] for s in staff_list) / len(staff_list)
        
        overloaded = [s for s in staff_list if s['current_tickets'] > avg_load + 2]
        underloaded = sorted(
            [s for s in staff_list if s['current_tickets'] < avg_load],
            key=lambda x: x['current_tickets']
        )
        
        reassigned = 0
        
        for helper in overloaded:
            # Get their tickets
            tickets = get_all_tickets(assigned_to=helper['email'], status='Open')
            
            # Reassign excess tickets
            excess = int(helper['current_tickets'] - avg_load)
            for i, ticket in enumerate(tickets[:excess]):
                if not underloaded:
                    break
                
                target = underloaded[0]
                if reassign_ticket(ticket.id, target['email'], changed_by):
                    reassigned += 1
                    target['current_tickets'] += 1
                    
                    # Re-sort underloaded list
                    underloaded.sort(key=lambda x: x['current_tickets'])
        
        logger.info(f"Workload balanced: {reassigned} tickets reassigned")
        return {"reassigned": reassigned, "average_load": avg_load}
        
    except Exception as e:
        logger.error(f"Error balancing workload: {e}", exc_info=True)
        return {"reassigned": 0, "error": str(e)}

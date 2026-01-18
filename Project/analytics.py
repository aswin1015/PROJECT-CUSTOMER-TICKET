import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

from database import get_all_tickets
from models import Ticket


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_NAME = "tickets.db"

# ==========================================
# TICKET STATISTICS
# ==========================================

def get_ticket_stats() -> Dict[str, Any]:
    """Get overall ticket statistics"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        stats = {}
        
        # Total tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        stats["total_tickets"] = cursor.fetchone()[0]
        
        # By status
        cursor.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
        stats["by_status"] = dict(cursor.fetchall())
        
        # By priority
        cursor.execute("SELECT priority, COUNT(*) FROM tickets GROUP BY priority")
        stats["by_priority"] = dict(cursor.fetchall())
        
        # Active (not closed/resolved)
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status NOT IN ('Closed', 'Resolved')")
        stats["active_tickets"] = cursor.fetchone()[0]
        
        # Unassigned
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE assigned_to IS NULL AND status != 'Closed'")
        stats["unassigned_tickets"] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return {}


def get_tickets_by_status(status: str) -> List[Dict]:
    """Get all tickets with a specific status"""
    try:
        from database import get_all_tickets
        tickets = get_all_tickets(status=status)
        return [t.to_dict() for t in tickets]
    except Exception as e:
        logger.error(f"Error getting tickets by status: {e}", exc_info=True)
        return []


def get_tickets_by_priority(priority: str) -> List[Dict]:
    """Get all tickets with a specific priority"""
    try:
        from database import get_all_tickets
        tickets = get_all_tickets(priority=priority)
        return [t.to_dict() for t in tickets]
    except Exception as e:
        logger.error(f"Error getting tickets by priority: {e}", exc_info=True)
        return []


def get_tickets_by_assignee(email: str) -> List[Dict]:
    """Get all tickets assigned to a specific person"""
    try:
        from database import get_all_tickets
        tickets = get_all_tickets(assigned_to=email)
        return [t.to_dict() for t in tickets]
    except Exception as e:
        logger.error(f"Error getting tickets by assignee: {e}", exc_info=True)
        return []


# ==========================================
# TIME-BASED ANALYTICS
# ==========================================

def get_tickets_created_today() -> int:
    """Count tickets created today"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM tickets 
            WHERE DATE(created_at) = ?
        """, (today,))
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Error getting today's tickets: {e}", exc_info=True)
        return 0


def get_tickets_by_date_range(start_date: str, end_date: str) -> List[Dict]:
    """Get tickets created within a date range"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE DATE(created_at) BETWEEN ? AND ?
            ORDER BY created_at DESC
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        from models import Ticket
        tickets = []
        for row in rows:
            ticket = Ticket(
                ticket_id=row[0], title=row[1], description=row[2], priority=row[3],
                status=row[4], assigned_to=row[5], created_by=row[6],
                created_at=row[7], updated_at=row[8], resolved_at=row[9], closed_at=row[10]
            )
            tickets.append(ticket.to_dict())
        
        return tickets
    except Exception as e:
        logger.error(f"Error getting tickets by date range: {e}", exc_info=True)
        return []


def get_average_resolution_time() -> float:
    """Calculate average time to resolve tickets (in hours)"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT created_at, resolved_at 
            FROM tickets 
            WHERE resolved_at IS NOT NULL
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return 0.0
        
        total_hours = 0
        for created, resolved in rows:
            try:
                created_dt = datetime.fromisoformat(created)
                resolved_dt = datetime.fromisoformat(resolved)
                hours = (resolved_dt - created_dt).total_seconds() / 3600
                total_hours += hours
            except (ValueError, TypeError):
                continue
        
        avg_hours = total_hours / len(rows) if rows else 0
        return round(avg_hours, 2)
    except Exception as e:
        logger.error(f"Error calculating resolution time: {e}", exc_info=True)
        return 0.0


# ==========================================
# STAFF PERFORMANCE ANALYTICS
# ==========================================

def get_staff_performance() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            assigned_to AS email,
            COUNT(*) AS total_handled,
            SUM(CASE WHEN status NOT IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS active_tickets
        FROM tickets
        WHERE assigned_to IS NOT NULL
        GROUP BY assigned_to
    """)

    ticket_rows = cursor.fetchall()

    cursor.execute("""
        SELECT email, name, role
        FROM users
        WHERE role = 'helper' AND is_active = 1
    """)
    helpers = cursor.fetchall()

    conn.close()

    ticket_map = {
        email: {
            "active_tickets": active or 0,
            "total_handled": total or 0
        }
        for email, total, active in ticket_rows
    }

    performance = []
    for email, name, role in helpers:
        stats = ticket_map.get(email, {})
        performance.append({
            "email": email,
            "name": name,
            "role": role,
            "active_tickets": stats.get("active_tickets", 0),
            "total_handled": stats.get("total_handled", 0)
        })

    performance.sort(key=lambda x: x["total_handled"], reverse=True)
    return performance



# ==========================================
# TREND ANALYSIS
# ==========================================

def get_ticket_trends(days: int = 7) -> Dict[str, int]:
    """Get ticket creation trend for the last N days"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        trends = {}
        today = datetime.now().date()
        
        for i in range(days):
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM tickets 
                WHERE DATE(created_at) = ?
            """, (date_str,))
            
            count = cursor.fetchone()[0]
            trends[date_str] = count
        
        conn.close()
        return dict(sorted(trends.items()))
    except Exception as e:
        logger.error(f"Error getting ticket trends: {e}", exc_info=True)
        return {}


def get_priority_distribution() -> Dict[str, Dict[str, int]]:
    """Get priority distribution by status"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT priority, status, COUNT(*) 
            FROM tickets 
            GROUP BY priority, status
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        distribution = defaultdict(dict)
        for priority, status, count in rows:
            distribution[priority][status] = count
        
        return dict(distribution)
    except Exception as e:
        logger.error(f"Error getting priority distribution: {e}", exc_info=True)
        return {}


# ==========================================
# REPORT GENERATION
# ==========================================

def print_dashboard():
    """Print a comprehensive dashboard"""
    stats = get_ticket_stats()
    performance = get_staff_performance()
    avg_resolution = get_average_resolution_time()
    
    print("\n" + "="*70)
    print("CUSTOMER SUPPORT DASHBOARD")
    print("="*70)
    
    # Overall stats
    print("\n📊 OVERALL STATISTICS")
    print("-"*70)
    print(f"Total Tickets: {stats.get('total_tickets', 0)}")
    print(f"Active Tickets: {stats.get('active_tickets', 0)}")
    print(f"Unassigned: {stats.get('unassigned_tickets', 0)}")
    print(f"Average Resolution Time: {avg_resolution} hours")
    
    # By status
    print("\n📋 BY STATUS")
    print("-"*70)
    for status, count in stats.get('by_status', {}).items():
        bar = "█" * (count // 2 if count > 0 else 0)
        print(f"{status:15} {bar} {count}")
    
    # By priority
    print("\n⚡ BY PRIORITY")
    print("-"*70)
    for priority, count in stats.get('by_priority', {}).items():
        bar = "█" * (count // 2 if count > 0 else 0)
        print(f"{priority:15} {bar} {count}")
    
    # Staff performance
    print("\n👥 STAFF PERFORMANCE")
    print("-"*70)
    print(f"{'Name':<20} {'Role':<15} {'Active':<8} {'Resolved':<10} {'Total':<8}")
    print("-"*70)
    for staff in performance:
        print(f"{staff['name']:<20} {staff['role']:<15} {staff['active_tickets']:<8} "
              f"{staff['resolved_tickets']:<10} {staff['total_handled']:<8}")
    
    print("\n" + "="*70 + "\n")


def export_report_to_text(filename: str = "ticket_report.txt"):
    """Export comprehensive report to text file"""
    try:
        stats = get_ticket_stats()
        performance = get_staff_performance()
        trends = get_ticket_trends(7)
        avg_resolution = get_average_resolution_time()
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("CUSTOMER SUPPORT TICKETING SYSTEM - REPORT\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("OVERALL STATISTICS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total Tickets: {stats.get('total_tickets', 0)}\n")
            f.write(f"Active Tickets: {stats.get('active_tickets', 0)}\n")
            f.write(f"Unassigned Tickets: {stats.get('unassigned_tickets', 0)}\n")
            f.write(f"Average Resolution Time: {avg_resolution} hours\n\n")
            
            f.write("BY STATUS:\n")
            for status, count in stats.get('by_status', {}).items():
                f.write(f"  {status}: {count}\n")
            
            f.write("\nBY PRIORITY:\n")
            for priority, count in stats.get('by_priority', {}).items():
                f.write(f"  {priority}: {count}\n")
            
            f.write("\n\nSTAFF PERFORMANCE\n")
            f.write("-" * 70 + "\n")
            for staff in performance:
                f.write(f"{staff['name']} ({staff['email']}):\n")
                f.write(f"  Active: {staff['active_tickets']}, Resolved: {staff['resolved_tickets']}, ")
                f.write(f"Total: {staff['total_handled']}\n")
            
            f.write("\n\n7-DAY TREND\n")
            f.write("-" * 70 + "\n")
            for date, count in trends.items():
                f.write(f"{date}: {count} tickets\n")
        
        logger.info(f"Report exported to {filename}")
        print(f"✓ Report exported to {filename}")
    except Exception as e:
        logger.error(f"Error exporting report: {e}", exc_info=True)


def search_tickets(keyword: str) -> List[Dict]:
    """Search tickets by keyword in title or description"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tickets 
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY created_at DESC
        """, (f"%{keyword}%", f"%{keyword}%"))
        
        rows = cursor.fetchall()
        conn.close()
        
        from models import Ticket
        tickets = []
        for row in rows:
            ticket = Ticket(
                ticket_id=row[0], title=row[1], description=row[2], priority=row[3],
                status=row[4], assigned_to=row[5], created_by=row[6],
                created_at=row[7], updated_at=row[8], resolved_at=row[9], closed_at=row[10]
            )
            tickets.append(ticket.to_dict())
        
        logger.info(f"Found {len(tickets)} tickets matching '{keyword}'")
        return tickets
    except Exception as e:
        logger.error(f"Error searching tickets: {e}", exc_info=True)
        return []


def get_response_time_stats() -> Dict[str, float]:
    """Get statistics about ticket response times"""
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        
        # Get time to first comment (response time)
        cursor.execute("""
            SELECT 
                t.created_at,
                MIN(c.created_at) as first_response
            FROM tickets t
            LEFT JOIN comments c ON t.id = c.ticket_id
            WHERE c.author != t.created_by
            GROUP BY t.id
            HAVING first_response IS NOT NULL
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {"avg_response_hours": 0.0, "ticket_count": 0}
        
        total_hours = 0
        for created, first_response in rows:
            try:
                created_dt = datetime.fromisoformat(created)
                response_dt = datetime.fromisoformat(first_response)
                hours = (response_dt - created_dt).total_seconds() / 3600
                total_hours += hours
            except (ValueError, TypeError):
                continue
        
        return {
            "avg_response_hours": round(total_hours / len(rows), 2) if rows else 0.0,
            "ticket_count": len(rows)
        }
    except Exception as e:
        logger.error(f"Error getting response time stats: {e}", exc_info=True)
        return {"avg_response_hours": 0.0, "ticket_count": 0}

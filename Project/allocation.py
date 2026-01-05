from database import get_staff_workload, get_all_staff
from typing import Optional

def allocate_round_robin() -> Optional[str]:
    """
    Allocate ticket using round-robin strategy.
    Assigns to the staff member with the least active tickets.
    """
    try:
        workload = get_staff_workload()
        
        if not workload:
            print("✗ No active staff available")
            return None
        
        # Find staff with least tickets
        least_busy = min(workload.items(), key=lambda x: x[1])
        
        print(f"✓ Round-robin allocation: {least_busy[0]} (current load: {least_busy[1]} tickets)")
        return least_busy[0]
    except Exception as e:
        print(f"✗ Allocation error: {e}")
        return None


def get_allocation_report():
    """Generate workload distribution report"""
    try:
        workload = get_staff_workload()
        all_staff = get_all_staff()
        
        print("\n" + "="*60)
        print("TICKET ALLOCATION REPORT (Round-Robin)")
        print("="*60)
        
        staff_info = {}
        for staff in all_staff:
            staff_info[staff.email] = {
                "name": staff.name,
                "role": staff.role,
                "tickets": workload.get(staff.email, 0),
                "max": staff.max_tickets
            }
        
        # Sort by ticket count (descending)
        sorted_staff = sorted(staff_info.items(), key=lambda x: x[1]["tickets"], reverse=True)
        
        for email, info in sorted_staff:
            bar = "█" * info["tickets"]
            capacity = f"{info['tickets']}/{info['max']}"
            status = "🔴" if info["tickets"] >= info["max"] else "🟢"
            
            print(f"{status} {info['name']:20} {info['role']:15} {bar} {capacity}")
        
        total = sum(workload.values())
        avg = total / len(workload) if workload else 0
        
        print("-" * 60)
        print(f"Total Active Tickets: {total}")
        print(f"Average per Staff: {avg:.1f}")
        print(f"Staff Members: {len(all_staff)}")
        print("="*60 + "\n")
    except Exception as e:
        print(f"✗ Error generating report: {e}")


def reassign_ticket(ticket_id: int, new_assignee: str, changed_by: str = "System") -> bool:
    """Reassign a ticket to a different staff member"""
    try:
        from database import update_ticket, get_ticket
        
        ticket = get_ticket(ticket_id)
        if not ticket:
            print(f"✗ Ticket #{ticket_id} not found")
            return False
        
        old_assignee = ticket.assigned_to
        update_ticket(ticket_id, assigned_to=new_assignee, changed_by=changed_by)
        
        print(f"✓ Reassigned ticket #{ticket_id}: {old_assignee} → {new_assignee}")
        return True
    except Exception as e:
        print(f"✗ Reassignment error: {e}")
        return False
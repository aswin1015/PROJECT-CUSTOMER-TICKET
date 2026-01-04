# tickets = []

# def create_ticket(title, description, priority):
#         ticket = {
#             "id": len(tickets)+1,
#             "title": title,
#             "description": description,
#             "status":"OPEN",
#             "priority": priority,
#             "assigned_to": None
#         }

#         tickets.append(ticket)
#         return tickets

# def update_status(ticket_id,new_status):
#         for ticket in tickets:
#                 if ticket["id"] == ticket_id:
#                         ticket["status"] = new_status
#                         return ticket
#         return "Ticket not FOUND"



# def assign_staff(ticket_id, staff_name):
#         for ticket in tickets:
#             if ticket["id"] == ticket_id:
#                 ticket["assigned_to"] = staff_name
#                 return ticket
#         return "Ticket not found"
        


class Ticket:
    def __init__(self,title,description, priority, ticket_id =None, status ="OPEN", assigned_to = None):
        self.id = ticket_id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.assigned_to = assigned_to

    def to_dict(self):
        return{
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "assigned_to": self.assigned_to
        }
    
    def __str__(self):
        return f"Ticket {self.id}: {self.title} [{self.status}]"
"""Seed demo data: workspace "Northwind Store" with owner + agents,
24 international tickets, 8 KB articles, replies, drafts and mock payments.

Run:  python -m app.seed
Demo logins:
  owner@northwind.store / owner123  (owner, Free plan)
  sara@northwind.store  / agent123  (agent)
  omar@northwind.store  / agent123  (agent)
"""
from datetime import datetime, timedelta

from .ai import generate_draft, triage
from .auth import get_password_hash
from .db import Base, SessionLocal, engine
from .models import (BillingRecord, Draft, KBArticle, Ticket, TicketReply,
                     User, Workspace)

Base.metadata.create_all(bind=engine)

KB_ARTICLES = [
    ("How to track your order", "Shipping", "Once your order ships, you will receive a tracking link by email. You can also track it from your account page under Orders. Tracking updates can take up to 24 hours to appear after dispatch."),
    ("Returns and refunds", "Orders", "You can return any unused item within 30 days of delivery for a full refund. Start a return from your account page, pack the item in its original packaging, and use the prepaid label. Refunds are processed within 5-7 business days after we receive the return."),
    ("Shipping costs and delivery times", "Shipping", "Standard international delivery takes 3-7 business days and costs are calculated at checkout by destination and weight. Express delivery (1-3 business days) is available at checkout. Orders over $100 ship free to the US, UK and EU."),
    ("How to change your delivery address", "Orders", "You can change the delivery address from your account page while the order still shows as Processing. Once an order is dispatched, the address cannot be changed — please contact support and we will try to intercept the parcel."),
    ("Payment methods we accept", "Billing", "We accept Visa, Mastercard, American Express, Apple Pay, Google Pay and PayPal. All payments are processed over encrypted connections. We never store full card numbers on our servers."),
    ("Resetting your password", "Account", "Click 'Forgot password' on the login page and enter your email address. You will receive a reset link valid for 30 minutes. If the email does not arrive, check your spam folder or contact support."),
    ("Warranty and product care", "Products", "All electronics carry a 12-month warranty against manufacturing defects. Clothing can be machine washed cold. Keep your order number handy when contacting us about a warranty claim."),
    ("Cancelling an order", "Orders", "Orders can be cancelled free of charge while they still show as Processing. Once an order is dispatched, cancellation is no longer possible — you can refuse delivery or start a return instead."),
]

# (subject, body, customer, email, country, channel, status, priority)
TICKETS = [
    ("Where is my order #ORD-4821?", "Hi, where is my order #ORD-4821? It was placed 5 days ago and I have not received any update.", "Emma Wilson", "emma.w@example.com", "United States", "email", "open", None),
    ("Refund for damaged headphones", "I would like a refund for order #ORD-4733. The item arrived damaged and the left earbud does not work.", "Liam Carter", "liam.c@example.co.uk", "United Kingdom", "email", "open", None),
    ("Do you ship to Canada?", "Do you ship to Canada? What are the delivery times to Toronto?", "Sophia Chen", "sophia.c@example.ca", "Canada", "chat", "open", None),
    ("Very disappointed with the delay", "This is the third time my order arrived late. Your service is getting worse and I am very unhappy.", "Noah Patel", "noah.p@example.com", "United States", "email", "pending", None),
    ("Cannot log in to my account", "I cannot log in to my account. It says my password is incorrect but I just reset it.", "Ava Thompson", "ava.t@example.com.au", "Australia", "chat", "open", None),
    ("Is this jacket waterproof?", "Is this jacket waterproof? I need it for rainy weather in London.", "Lucas Meyer", "lucas.m@example.de", "Germany", "whatsapp", "open", None),
    ("Order #ORD-5113 stuck at warehouse", "Order #ORD-5113 has been stuck at the warehouse for 3 days. Please check.", "Mia Garcia", "mia.g@example.es", "Spain", "email", "pending", None),
    ("Charged twice for one order", "My bank shows the payment was taken twice for order #ORD-4907. Please refund one charge.", "Ethan Brown", "ethan.b@example.com", "United States", "email", "open", None),
    ("Thank you, great service!", "Hello, just wanted to say thank you, the order arrived in perfect condition!", "Isabella Rossi", "isabella.r@example.it", "Italy", "chat", "resolved", None),
    ("How much is shipping to the UK?", "How much does shipping to the UK cost for an order under 2kg?", "James Anderson", "james.a@example.co.uk", "United Kingdom", "email", "resolved", None),
    ("Wrong item delivered", "I received a used item instead of a new one. This is unacceptable and I want a replacement.", "Charlotte Dubois", "charlotte.d@example.fr", "France", "email", "pending", None),
    ("Change my delivery address", "Can I change the delivery address for my order? It has not shipped yet.", "Benjamin Lee", "benjamin.l@example.sg", "Singapore", "chat", "open", None),
    ("Refund status for order #ORD-4788", "Refund status for order #ORD-4788 please, it has been two weeks.", "Amelia Khan", "amelia.k@example.ae", "United Arab Emirates", "email", "open", None),
    ("Does the laptop stand fit 16 inch?", "Does the laptop stand fit a 16 inch MacBook Pro?", "Henry Wright", "henry.w@example.com", "United States", "whatsapp", "resolved", None),
    ("Password reset link not arriving", "I forgot my password and the reset link is not arriving in my inbox.", "Ella Novak", "ella.n@example.cz", "Czech Republic", "email", "open", None),
    ("Express shipping to the UAE?", "Do you offer express shipping to the UAE? I need delivery within 3 days.", "Omar Haddad", "omar.h@example.ae", "United Arab Emirates", "chat", "open", None),
    ("Product broke after two days", "The product broke after two days of normal use. This is not acceptable quality.", "Grace Liu", "grace.l@example.ca", "Canada", "email", "pending", None),
    ("Student discount available?", "Hi, I am a student. Do you offer a student discount?", "Jack Miller", "jack.m@example.com.au", "Australia", "chat", "resolved", None),
    ("Where is my parcel?", "Where is my parcel? Order #ORD-5054, tracking shows no movement.", "Freya Larsen", "freya.l@example.dk", "Denmark", "email", "open", None),
    ("Gift card for my sister", "Good afternoon, do you sell gift cards? I want one for my sister.", "Leo Martin", "leo.m@example.fr", "France", "chat", "open", None),
    ("Refund for duplicate subscription charge", "I was charged for an order I never placed. Please refund the full amount immediately.", "Zoe Adams", "zoe.a@example.co.nz", "New Zealand", "email", "open", None),
    ("How to track my shipment?", "How do I track my shipment once it leaves your warehouse?", "Daniel Kim", "daniel.k@example.kr", "South Korea", "whatsapp", "resolved", None),
    ("Shoes arrived in wrong color", "The shoes I received are a different color than what I ordered. Very poor quality control.", "Nina Petrov", "nina.p@example.nl", "Netherlands", "email", "pending", None),
    ("Do you accept Apple Pay?", "Hello, what payment methods do you accept? Do you take Apple Pay?", "Chris Evans", "chris.e@example.com", "United States", "chat", "open", None),
]


def seed():
    db = SessionLocal()
    existing = db.query(Workspace).filter(Workspace.name == "Northwind Store").first()
    if existing:
        print("Northwind Store already seeded — skipping.")
        db.close()
        return

    ws = Workspace(name="Northwind Store", plan="free")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    owner = User(workspace_id=ws.id, name="Olivia North", email="owner@northwind.store", password_hash=get_password_hash("owner123"), role="owner")
    sara = User(workspace_id=ws.id, name="Sara Ahmed", email="sara@northwind.store", password_hash=get_password_hash("agent123"), role="agent")
    omar = User(workspace_id=ws.id, name="Omar Farouk", email="omar@northwind.store", password_hash=get_password_hash("agent123"), role="agent")
    db.add_all([owner, sara, omar])
    db.commit()
    db.refresh(owner)
    db.refresh(sara)
    db.refresh(omar)

    for title, category, body in KB_ARTICLES:
        db.add(KBArticle(workspace_id=ws.id, title=title, body=body, category=category, published=True))
    db.commit()

    base_time = datetime.utcnow() - timedelta(days=6)
    for i, (subject, body, name, email, country, channel, status, _prio) in enumerate(TICKETS):
        result = triage(f"{subject}. {body}")
        created = base_time + timedelta(hours=i * 5)
        ticket = Ticket(
            workspace_id=ws.id,
            number=f"SP-{1001 + i}",
            subject=subject,
            body=body,
            customer_name=name,
            customer_email=email,
            customer_country=country,
            channel=channel,
            status=status,
            priority=result["priority"],
            ai_intent=result["intent"],
            ai_sentiment=result["sentiment"],
            ai_priority=result["priority"],
            ai_confidence=str(result["confidence"]),
            sla_hours=24,
            created_at=created,
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        if status in ("pending", "resolved"):
            ticket.assignee_id = sara.id if i % 2 == 0 else omar.id
            ticket.first_response_at = created + timedelta(hours=2)
            db.add(TicketReply(ticket_id=ticket.id, author_id=ticket.assignee_id, author_name=sara.name if i % 2 == 0 else omar.name, body="Hi, thanks for reaching out — I'm looking into this for you right now and will update you shortly.", internal=False))
        if status == "resolved":
            ticket.resolved_at = created + timedelta(hours=20)
            ticket.csat_rating = 5 if i % 3 else 4
        draft = Draft(ticket_id=ticket.id, workspace_id=ws.id, body=generate_draft(result["intent"], name, body), status="drafted", created_by_id=sara.id)
        db.add(draft)
        db.commit()

    db.add(BillingRecord(workspace_id=ws.id, plan="free", amount_usd=0, reference="MOCK-STRIPE-FREE0001", status="paid"))
    db.commit()
    print("Seeded Northwind Store: 3 users, 24 tickets, 8 KB articles, 1 mock billing record.")
    print("Demo logins: owner@northwind.store / owner123 | sara@northwind.store / agent123 | omar@northwind.store / agent123")
    db.close()


if __name__ == "__main__":
    seed()

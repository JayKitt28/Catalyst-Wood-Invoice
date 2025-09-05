from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import JSON
from sqlalchemy.ext.mutable import MutableList

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    used_invoices = db.Column(        
        MutableList.as_mutable(JSON),
        nullable=False,
        default=list
    )
    total_cost = db.Column(db.Float, nullable=False, default = 0)

    budget_items = relationship(
        "BudgetItem", back_populates="project", cascade="all, delete-orphan"
    )
    
    def add_invoice(self, invoice):
        """Add an invoice number to the used list if it's not already there."""
        if self.used_invoices is None:
            self.used_invoices = []
        if invoice not in self.used_invoices:
            self.used_invoices.append(invoice)
        
    def is_invoice_used(self, invoice_num):
        """Check if an invoice number has already been used."""
        if self.used_invoices is None:
            return False
        for inv in self.used_invoices:
            
            if inv["invoice_number"] == invoice_num:
                return True
        return False
    
    def get_used_invoice(self):
        """Get the list of used invoice numbers."""
        return self.used_invoices or []

class BudgetItem(db.Model):
    __tablename__ = "budget_items"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), nullable=False)
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    material_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    received = db.Column(db.Integer, nullable=False, default=0)
    total_payed = db.Column(db.Float, nullable = False, default = 0)
    extra_data = db.Column(JSON, nullable=True, default=dict)
    
    # Ensure unique combination of sku and project_id
    __table_args__ = (db.UniqueConstraint('sku', 'project_id', name='unique_sku_per_project'),)

    project = relationship("Project", back_populates="budget_items")
    
    def __init__(self, data):
        self.sku = data['sku']
        self.received = data['shipped']
        self.material_name = data['description']
        self.quantity = -1
        self.total_payed = round(float(data['extension']), 2)  # Initialize total_payed to 0
        self.extra_data = {
            "ordered": data['ordered'],
            "um": data['unit_measurement'],
            "location": data['location'],
            "units": data['units'],
            "price_per": data['price_per'],
        }
        
    
    def overwrite(self, sku, material, quantity_int, received_int, total_payed):
        self.sku = sku
        self.material_name = material
        self.quantity = quantity_int
        self.received = received_int
        self.total_payed = total_payed
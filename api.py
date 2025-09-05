from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import func

from models import db, Project, BudgetItem
from pdf import apply_via_upload
from invoiceDownloader import download_and_process_invoices

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/projects', methods=['GET'])
def return_all_projects():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    payload = []
    for p in projects:
        payload.append(
            {
                "id": p.id,
                "name": p.name,
                "createdAt": p.created_at.isoformat(),
                "budgetItems": [
                    {
                        "id": bi.id,
                        "sku": bi.sku,
                        "materialName": bi.material_name,
                        "quantity": bi.quantity,
                        "received": bi.received,
                        "total_payed": bi.total_payed,
                    }
                    for bi in p.budget_items
                ],
            }
        )
    return jsonify(payload)

@api_bp.route('/projects', methods=['POST'])
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    items = data.get("budgetItems") or []

    if not name:
        return jsonify({"error": "Project name is required"}), 400
    if not isinstance(items, list):
        return jsonify({"error": "budgetItems must be a list"}), 400

    # Enforce unique name (case-insensitive)
    existing = Project.query.filter(func.lower(Project.name) == name.lower()).first()
    if existing is not None:
        return jsonify({"error": "A project with that name already exists"}), 409

    project = Project(name=name)
    
    # Only process budget items if they are provided
    if items:
        for item in items:
            sku = (item.get("sku") or "").strip()
            material = (item.get("materialName") or "").strip()
            quantity = item.get("quantity")
            try:
                quantity_int = int(quantity)
            except Exception:
                quantity_int = None
            received_val = item.get("received", 0)
            try:
                received_int = int(received_val)
            except Exception:
                received_int = None
            if (
                not sku
                or not material
                or quantity_int is None
                or quantity_int < 0
                or received_int is None
                or received_int < 0
            ):
                return (
                    jsonify(
                        {
                            "error": "Each item requires sku, materialName, non-negative quantity, and non-negative received amount",
                        }
                    ),
                    400,
                )
            project.budget_items.append(
                BudgetItem(sku=sku, material_name=material, quantity=quantity_int, received=received_int)
            )

    db.session.add(project)
    db.session.commit()

    return jsonify({"id": project.id}), 201

@api_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Not found"}), 404
    payload = {
        "id": project.id,
        "name": project.name,
        "createdAt": project.created_at.isoformat(),
        "budgetItems": [
            {
                "id": bi.id,
                "sku": bi.sku,
                "materialName": bi.material_name,
                "quantity": bi.quantity,
                "received": bi.received,
                "total_payed": bi.total_payed,
            }
            for bi in project.budget_items
        ],
        "total_cost": project.total_cost
    }
    return jsonify(payload)

@api_bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id: int):
    project = db.session.get(Project, project_id)

    if project is None:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(project)
    db.session.commit()
    return ("", 204)

@api_bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or project.name).strip()
    items = data.get("budgetItems")

    if not name:
        return jsonify({"error": "Project name is required"}), 400

    # Enforce unique name (case-insensitive, excluding self)
    existing = (
        Project.query.filter(func.lower(Project.name) == name.lower(), Project.id != project.id)
        .first()
    )
    if existing is not None:
        return jsonify({"error": "A project with that name already exists"}), 409

    project.name = name

    if items is not None:
        if not isinstance(items, list):
            return jsonify({"error": "budgetItems must be a list"}), 400
        # Replace all budget items

        
        for item in items:
            sku = (item.get("sku") or "").strip()
            print(item)
            material = (item.get("materialName") or "").strip()
            quantity = item.get("quantity")
            try:
                quantity_int = int(quantity)
            except Exception:
                quantity_int = None
            received_val = item.get("received", 0)
            try:
                received_int = int(received_val)
            except Exception:
                received_int = None
            total_payed = (item.get("total_payed"))
            if (
                not sku
                or not material
                or quantity_int is None
                or quantity_int < 0
                or received_int is None
                or received_int < 0
            ):
                return (
                    jsonify(
                        {
                            "error": "Each item requires sku, materialName, non-negative quantity, and non-negative received amount",
                        }
                    ),
                    400,
                )
            for budget_item in project.budget_items:
                if budget_item.sku == sku:
                    budget_item.overwrite(sku, material, quantity_int, received_int, total_payed)
                    
    db.session.commit()
    return ("", 204)

@api_bp.route('/projects/<int:project_id>/apply-pdf', methods=['POST'])
def apply_pdf_to_project_route(project_id: int):
    project = db.session.get(Project, project_id)
    if project is None:
        return jsonify({"error": "Not found"}), 404

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    try:
        result = apply_via_upload(file, project)
        if result["invoice_used"]:
            print("BAD BOY")
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@api_bp.route('/process-invoices', methods=['POST'])
def process_invoices_from_email():
    """Manually trigger the invoice downloader to process emails."""
    try:
        (resp, processed_count) = download_and_process_invoices(current_app)
        message = ""
        if resp.get('error', '') != "": 
            message = resp['error']
        else: 
            message = f"Successfully processed {processed_count} invoices from email"
        return jsonify({
            "message": message,
            "processed_count": processed_count
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to process invoices: {str(e)}"}), 500


@api_bp.route('/invoices/<int:project_id>', methods=['GET'])
def get_invoices_by_project(project_id):
    try:
        project = db.session.get(Project, project_id)
        if project is None:
            return jsonify({"error": "Not found"}), 404
        
        # Get the used invoices from the project
        invoices = project.get_used_invoice()
        return jsonify(invoices)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch invoices: {str(e)}"}), 500
    
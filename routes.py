from flask import send_from_directory

def register_routes(app):
    @app.route('/')
    def serve_index():
        return send_from_directory("./pages", "index.html")
    
    @app.route("/projects/<int:project_id>")
    def serve_project_page(project_id: int):
        return send_from_directory("./pages", "project.html")

    @app.route('/invoices/<int:project_id>')
    def serve_invoices_page(project_id: int):
        return send_from_directory("./pages", "invoices.html")
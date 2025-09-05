import re
import pdfplumber
from models import db, BudgetItem, Project
import os



def apply_via_upload(file, project):

    response = parse_pdf(file)
    return apply_pdf_to_project(project, response)
    

def apply_pdf_via_email(path):
    # Read the file at 'path' and save it to a local file
    with open(path, "rb") as src_file:
        file_data = src_file.read()
    filename = os.path.basename(path)
    save_path = os.path.join(os.getcwd(), filename)
    with open(save_path, "wb") as dest_file:
        dest_file.write(file_data)
    file = save_path
    response = parse_pdf(file)
    
    project = None
    existing_project = Project.query.filter(Project.name == response['adress']).first()
    if existing_project:
        project = existing_project
        print(project)
    else:

        project = create_project(response)
    return apply_pdf_to_project(project, response)


def create_project(response):
    project = Project()
    project.name = response['adress']

    db.session.add(project)
    db.session.commit()
    return project    

def parse_pdf(file):
    # Parse the PDF file and extract its text content
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    parsing_items = False

    invoiceNum = 0
    
    DaysOW = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"}

    response = {
        "items": [],
        "skipped_lines": [],
        "invoice_number": 0,
        "invoice_used": False,
        "total_price": 0,
        "error": "",
        "adress": ""
    }

    expect_adress = False

    for line in text.splitlines():
        if parsing_items and line.upper().strip() in DaysOW:
            parsing_items = False
        elif "INVOICE:" in line:
            response["invoice_number"] = re.sub(r'\D', '', line)
            
        elif "TOTAL" in line:
            # Extract the total price including the decimal point
            match = re.search(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})', line.replace(',', ''))
            if match:
                response['total_price'] = match.group(1)
            else:
                response['total_price'] = ""
        elif "SHIP TO:" in line: expect_adress = True
        elif expect_adress:
            split = line.split()
            capture = False
            for word in split:
                if word == "DEL.":
                    expect_adress=False
                    break
                if capture:
                    response["adress"] += word
                if word == "LLC":
                    capture = True

    
        if parsing_items:
            split_line = line.split()
            if len(split_line) < 14:
                response["skipped_lines"].append(split_line[0] if split_line else "")
                response["error"] += ("Lines were skipped due to failure in pdf parsing please email the pdf to jaykit19@gmail.com \n")
                continue  # skip lines that don't have enough columns
            data = {
                'line': re.sub(r'\D', '', split_line[0]),
                'shipped': re.sub(r'\D', '', split_line[1]),
                'ordered': re.sub(r'\D', '', split_line[2]),
                'unit_measurement': split_line[3],
                'sku': split_line[4],
                'description': " ".join(split_line[5:9]),
                'location': split_line[9] ,
                'units': split_line[10],
                'price_per': re.sub(r'\D', '', split_line[11]),
                'extension': split_line[13]
            }
            
            response["items"].append(data)
            if data['shipped'] != data['ordered']:
                response['error'] += ('LESS ITEMS SHIPPED THAN ORDERED PLEASE EMAIL JAYKITT19@GMAIL.COM \n')

        if "EXTENSION" in line:
            parsing_items = True
    return response

def apply_pdf_to_project(project, response):
    # Refresh the project from database to get current budget_items
    db.session.refresh(project)
    
    if project.is_invoice_used(response['invoice_number']):
        response['invoice_used'] = True
        response['error'] = "INVOICE HAS ALREADY BEEN USED IF ERROR EMAILL JAYKITT19@GMAIL.COM"
        return response

    for line in response['items']:
        sku = line.get('sku')
        quantity = int(line.get('shipped', 0))
        total_payed = line.get('extension', '0')
        
        existing_item = None
        for budget_item in project.budget_items:
            if budget_item.sku == sku:
                existing_item = budget_item
                break
        
        if existing_item:
            existing_item.received += quantity
            
            existing_item.total_payed += round(float(total_payed), 2)
        else:
            # Create new budget item=
            new_item = BudgetItem(line)
            new_item.project_id = project.id
            project.budget_items.append(new_item)
    project.add_invoice(response)
    project.total_cost += round(float(response['total_price']), 2)
    db.session.commit()
    return response
import os 
from imbox import Imbox
import traceback

from pdf import apply_pdf_via_email

host = "imap.gmail.com"
username = "JayKitt19@gmail.com"
password = "hicc qfxd rbgg inxe"
pdfFolder = "./invoicePDFs"

def download_and_process_invoices(app):
    """Download PDF invoices from email and process them with Flask app context."""
    with app.app_context():
        if not os.path.isdir(pdfFolder):
            os.makedirs(pdfFolder, exist_ok=True)

        mail = Imbox(host, username=username, password=password, ssl=True, ssl_context=None, starttls=False)

        messages = mail.messages(subject='PDF', unread=True, sent_from="JayKitt19@gmail.com", raw = "has:attachment")
        processed_count = 0
        resp = {}
        
        messages_list = list(messages)
        print(f"Found {len(messages_list)} emails matching criteria")
        
        if len(messages_list) == 0:
            print("No emails found with subject 'PDF', unread=True, from 'JayKitt19@gmail.com' with attachments")
            resp = {'error' : 'No new invoices in the inbox'}
            return (resp, processed_count)
        
        # Print details about each email found
        for i, (uid, message) in enumerate(messages_list):
            print(f"Email {i+1}: UID={uid}, Subject='{message.subject}', From='{message.sent_from}', Attachments={len(message.attachments)}")
        for (uid, message) in messages_list:
            print(uid)
            for idx, attachment in enumerate(message.attachments):

                try:
                    
                    att_fn = attachment.get('filename')
                    download_path = f"{pdfFolder}/{att_fn}"
                    print(f"Processing: {att_fn}")
                    with open(download_path, "wb") as fp:
                       fp.write(attachment.get('content').read())
                    
                    resp = apply_pdf_via_email(download_path)
                    processed_count += 1
                    print(f"Successfully processed: {att_fn}")
                    mail.mark_seen(uid)
                except Exception as e:
                    print(f"Error processing {att_fn}: {str(e)}")
                    print(traceback.print_exc())
                
        
        print(f"Processed {processed_count} invoices")
        return (resp, processed_count)
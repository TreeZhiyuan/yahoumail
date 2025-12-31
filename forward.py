import os
import imapclient
from email.parser import BytesParser
import smtplib
from email.message import EmailMessage

def fetch_new_emails():
    # Debug log for Yahoo credentials
    print(f"[DEBUG] YAHOO_USER: {os.environ.get('YAHOO_USER')}")
    print(f"[DEBUG] YAHOO_APP_PASSWORD: {os.environ.get('YAHOO_APP_PASSWORD')}")
    with imapclient.IMAPClient('imap.mail.yahoo.com') as client:
        client.login(os.environ['YAHOO_USER'], os.environ['YAHOO_APP_PASSWORD'])
        client.select_folder('INBOX', readonly=True)
        messages = client.search(['UNSEEN'])
        for uid in messages:
            raw = client.fetch([uid], ['RFC822'])[uid][b'RFC822']
            mail = BytesParser().parsebytes(raw)
            yield mail

def forward_email(mail):
    # Debug log for SMTP credentials/settings
    print(f"[DEBUG] SMTP_HOST: {os.environ.get('SMTP_HOST')}")
    print(f"[DEBUG] SMTP_PORT: {os.environ.get('SMTP_PORT')}")
    print(f"[DEBUG] SMTP_USER: {os.environ.get('SMTP_USER')}")
    print(f"[DEBUG] SMTP_PASS: {os.environ.get('SMTP_PASS')}")
    smtp = smtplib.SMTP_SSL(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']))
    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
    msg = EmailMessage()
    msg['Subject'] = "FWD: " + mail['Subject']
    msg['From'] = os.environ['SMTP_USER']
    msg['To'] = os.environ['FORWARD_TO']
    msg.set_content(mail.get_payload())
    smtp.send_message(msg)
    smtp.quit()

if __name__ == '__main__':
    for mail in fetch_new_emails():
        forward_email(mail)

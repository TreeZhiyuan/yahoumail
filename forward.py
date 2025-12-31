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
    # Use STARTTLS (typically port 587). Connect with plain SMTP, then upgrade to TLS.
    smtp = smtplib.SMTP(os.environ['SMTP_HOST'], int(os.environ['SMTP_PORT']))
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(os.environ['SMTP_USER'], os.environ['SMTP_PASS'])
    msg = EmailMessage()
    msg['Subject'] = "FWD: " + (mail['Subject'] or '')
    msg['From'] = os.environ['SMTP_USER']
    msg['To'] = os.environ['FORWARD_TO']
    # Try to get a sensible text payload
    try:
        body = mail.get_payload(decode=True) if mail.get_content_maintype() != 'multipart' else ''
        if isinstance(body, bytes):
            body = body.decode(errors='ignore')
    except Exception:
        body = str(mail)
    msg.set_content(body)
    smtp.send_message(msg)
    smtp.quit()

if __name__ == '__main__':
    for mail in fetch_new_emails():
        forward_email(mail)

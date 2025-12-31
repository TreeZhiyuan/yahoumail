import os
import imapclient
from email.parser import BytesParser
import smtplib
from email.message import EmailMessage

def fetch_new_emails():
    with imapclient.IMAPClient('imap.mail.yahoo.com') as client:
        client.login(os.environ['YAHOO_USER'], os.environ['YAHOO_APP_PASSWORD'])
        client.select_folder('INBOX', readonly=True)
        messages = client.search(['UNSEEN'])
        for uid in messages:
            raw = client.fetch([uid], ['RFC822'])[uid][b'RFC822']
            mail = BytesParser().parsebytes(raw)
            yield mail

def forward_email(mail):
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

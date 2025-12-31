import os
import imaplib
import smtplib
import email
from email.message import EmailMessage
from email.header import decode_header
from datetime import datetime, timedelta, timezone

# --- 配置区：从 GitHub Secrets 自动读取 ---
YAHOO_EMAIL = os.environ.get('YAHOO_EMAIL')
YAHOO_APP_PASS = os.environ.get('YAHOO_APP_PASS')
TARGET_OUTLOOK = os.environ.get('TARGET_EMAIL')

def clean_header(header_value):
    if not header_value: return ""
    return " ".join(str(header_value).split())

def run_forwarder():
    # 基础检查
    if not all([YAHOO_EMAIL, YAHOO_APP_PASS, TARGET_OUTLOOK]):
        print("错误: 环境变量配置不完整")
        return

    # 时间过滤逻辑：IMAP按天搜，Python按6小时滤
    today = datetime.now().strftime("%d-%b-%Y")
    now = datetime.now(timezone.utc)
    six_hours_ago = now - timedelta(hours=6)
    
    try:
        # --- IMAP 连接 ---
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(YAHOO_EMAIL, YAHOO_APP_PASS)
        mail.select("inbox")

        # 搜索今天以内的未读邮件
        status, messages = mail.search(None, f'(UNSEEN SINCE {today})')
        if status != 'OK' or not messages[0]:
            print("没有发现新的未读邮件。")
            mail.logout()
            return

        # --- SMTP 连接 (仅在确定有邮件时开启) ---
        server = smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465)
        server.login(YAHOO_EMAIL, YAHOO_APP_PASS)

        for num in messages[0].split():
            # 抓取原始邮件
            res, msg_data = mail.fetch(num, "(RFC822)")
            original_msg = email.message_from_bytes(msg_data[0][1])

            # 精确时间过滤
            raw_date = original_msg.get('Date')
            try:
                mail_date = email.utils.parsedate_to_datetime(raw_date)
                if mail_date < six_hours_ago:
                    continue
            except:
                pass

            # 清洗头信息
            orig_subject = clean_header(original_msg.get('Subject', '无主题'))
            orig_from = clean_header(original_msg.get('From', '未知'))
            
            # 构建转发邮件
            new_msg = EmailMessage()
            new_msg['Subject'] = f"Fwd: {orig_subject}"
            new_msg['From'] = YAHOO_EMAIL
            new_msg['To'] = TARGET_OUTLOOK

            # 网页风格头
            header_html = f"""
            <div style="border-left: 3px solid #e1e4e8; padding-left: 15px; margin-bottom: 20px; color: #586069; font-family: sans-serif;">
                <p>---------- Forwarded message ---------</p>
                <p><b>From:</b> {orig_from}</p>
                <p><b>Date:</b> {raw_date}</p>
                <p><b>Subject:</b> {orig_subject}</p>
            </div>
            """

            # 正文与附件处理
            main_content_html = ""
            for part in original_msg.walk():
                content_type = part.get_content_type()
                disposition = str(part.get("Content-Disposition"))

                if content_type == "text/html" and "attachment" not in disposition:
                    main_content_html = part.get_payload(decode=True).decode(errors='ignore')
                elif "attachment" in disposition:
                    filename = part.get_filename()
                    if filename:
                        # 解码文件名
                        decoded = decode_header(filename)
                        fname = "".join([str(t[0].decode(t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0]) for t in decoded])
                        new_msg.add_attachment(
                            part.get_payload(decode=True),
                            maintype=part.get_content_maintype(),
                            subtype=part.get_content_subtype(),
                            filename=clean_header(fname)
                        )

            if not main_content_html:
                for part in original_msg.walk():
                    if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                        main_content_html = f"<pre>{part.get_payload(decode=True).decode(errors='ignore')}</pre>"
                        break

            new_msg.set_content("请查看 HTML 邮件内容")
            new_msg.add_alternative(header_html + main_content_html, subtype='html')

            # 发送邮件
            server.send_message(new_msg)
            
            # 重要：标记为已读，避免下次 Actions 重复抓取
            mail.store(num, '+FLAGS', '\\Seen')
            print(f"成功转发: {orig_subject}")

        server.quit()
        mail.logout()

    except Exception as e:
        print(f"执行异常: {e}")

if __name__ == "__main__":
    run_forwarder()
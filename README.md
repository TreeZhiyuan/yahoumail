# yahoumail

fetch and forward yahoo mail from Chinese mainland.

## 详细设计方案：使用Python监控Yahoo邮箱新邮件并转发，脚本通过GitHub Actions定时执行

### 一、功能目标概述

- 自动定时检测指定Yahoo邮箱新邮件（收件箱）。
- 新邮件通过SMTP方式自动转发到指定邮箱（如QQ邮箱、Gmail等）。
- 实现全部逻辑基于Python脚本。
- 通过GitHub Actions定时调度任务，无需自有服务器，支持无间断云端运维。

### 二、技术选型

- 主要开发语言：Python
- IMAP协议库：`imaplib` 或 `imapclient`（推荐后者，封装更为友好）
- 邮件解析库：`email`
- 邮件发送库：`smtplib`
- 作业调度：GitHub Actions 定时触发
- 凭据安全存储：GitHub Actions Secret

### 三、Python脚本设计要点

#### 1. 登录Yahoo邮箱

- 采用IMAP协议，连接Yahoo邮箱收件箱（imap.mail.yahoo.com）。
- 可用`imapclient`简化IMAP操作。
- 使用App Password（Yahoo邮箱需开启两步验证并生成专用密码）。

#### 2. 检查新邮件

- 标记上次检查的位置（如uid)。
- 每次运行脚本时拉取新邮件，可简单获取24小时内的全部未读邮件。
- 使用`email`库解析邮件内容、附件等。

#### 3. 邮件转发

- 连接目标邮箱SMTP服务器（如smtp.qq.com）。
- 将解析后的新邮件以转发形式发送到指定邮箱，可以保留原始发件人、标题等。
- 可配置多收件人。

#### 4. 环境变量/Secrets配置

- Yahoo邮箱用户名和App Password
- 目标邮箱SMTP服务器、端口、用户名和授权码
- 接收邮箱清单

这些凭据应作为GitHub Action的Secret安全存储，在workflow中注入脚本。

#### 5. 错误处理和日志

- 捕获IMAP/SMTP异常，适当重试，失败时记录日志方便排查。
- 可将异常信息邮件主动告警到管理员邮箱或输出到工作流日志。

---

### 四、GitHub Actions自动化方案

#### 1. Workflow定义

- 创建`.github/workflows/forward.yml`
- 使用`schedule`触发器（例如每10分钟/30分钟/1小时执行）
- 步骤包括：拉取代码、设置Python环境、安装依赖、运行转发脚本

#### 2. Secret配置

- 在Repo Settings > Secrets and variables > Actions中添加：
    - YAHOO_USER
    - YAHOO_APP_PASSWORD
    - SMTP_HOST
    - SMTP_PORT
    - SMTP_USER
    - SMTP_PASS
    - FORWARD_TO（支持逗号分隔多个收件人）

#### 3. Workflow示例

```yaml
name: YahooMail Forward

on:
  schedule:
    - cron: '*/30 * * * *' # 每30分钟执行一次
  workflow_dispatch:

jobs:
  forward:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install imapclient
      - name: Forward new Yahoo mails
        env:
          YAHOO_USER: ${{ secrets.YAHOO_USER }}
          YAHOO_APP_PASSWORD: ${{ secrets.YAHOO_APP_PASSWORD }}
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASS: ${{ secrets.SMTP_PASS }}
          FORWARD_TO: ${{ secrets.FORWARD_TO }}
        run: python forward.py
```

---

### 五、核心脚本伪代码

`forward.py`

```python
import os, imapclient, smtplib
from email.parser import BytesParser
from email.message import EmailMessage

def fetch_new_emails():
    # 连接IMAP
    with imapclient.IMAPClient('imap.mail.yahoo.com') as client:
        client.login(os.environ['YAHOO_USER'], os.environ['YAHOO_APP_PASSWORD'])
        client.select_folder('INBOX', readonly=True)
        # 比如查找24小时内的未读邮件
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
```

**实际开发时应考虑附件转发、原始发件人信息保留、时间区间过滤、邮件ID去重、敏感信息日志脱敏等完善性细节。**

---

### 六、参考与风险说明

- [Yahoo官方IMAP介绍](https://help.yahoo.com/kb/imap-settings-for-yahoo-mail-sln4075.html)
- [imapclient文档](https://imapclient.readthedocs.io/en/3.0/)
- 建议务必使用App Password，避免暴露主密码。
- 若遇到账户安全限制、发送频率限制，可通过增加监控频率、分批转发优化。
- **注意严禁将任何身份凭证（如邮箱密码、App密码等）明文写入代码库！全部交由GitHub Secrets托管。**

---

如需具体代码实现，请开启相关Issue或PR。

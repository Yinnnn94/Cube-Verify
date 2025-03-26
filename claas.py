import pandas as pd
from openai import OpenAI
import time
from pathlib import Path
import st_static_export as sse
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header
from datetime import datetime
import os

class OpenAIClient:
    """負責與 OpenAI API 的交互"""
    def __init__(self, api_key, assistant_id):
        self.client = OpenAI(api_key=api_key)
        self.assistant_id = assistant_id

    def Reply(self, content): # lambda storeai_query_assistant API取代
        thread = self.client.beta.threads.create(
            messages=[{"role": "user", "content": content}]
        )
        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=self.assistant_id
        )
        messages = list(self.client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))
        message_content = messages[0].content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = self.client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")
        response = self.client.beta.threads.delete(thread.id)
        if not response.deleted:
            time.sleep(1)
        citations = "\n".join(citations)
        return_message = message_content.value + citations
        print(f'生成回覆：{return_message}')
        return return_message

    def MakeCompletions(self, developer_content, prompt, model):
        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "developer", "content": developer_content},
                {"role": "user", "content": prompt}
            ]
        )
        return completion.choices[0].message.content

class TextProcessor:
    """負責文本處理"""
    def TextToList(self, text):
        return text.strip("[]").replace(" ", "").replace("'", "").split(',')

class ReportGenerator:
    """負責生成報表"""
    def __init__(self, root_path):
        self.root_path = root_path

    def generate_html_content(self, data: pd.DataFrame) -> str:
        css_text = """
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        tr:nth-child(even) {background-color: #f2f2f2;}
        .table {
            width:100%;
        }
        .footn {
            color:#c0c0c0;
        }
        .table ul {
            margin: 0;           /* 去除清單的上下邊距 */
            padding-left: 20px;  /* 設定左側縮進，讓項目符號有空間 */
        }
        """
        
        # 建立 StreamlitStaticExport 實例
        static_html = sse.StreamlitStaticExport(css=css_text)
        
        # 添加標題和說明文字
        static_html.add_header(id="title", text="Issue Analysis", size="H1")
        static_html.add_text(id="explanation", text="""這邊羅列的是已將「匯入的回覆」放置到DB1.1 UAT中，卻在「DB1.1 UAT 回覆」沒有看到「匯入的回覆」資訊""")
        
        # 建立用於顯示的資料框副本，避免修改原始資料
        display_data = data[['original_index', 'Title', 'Comment', 'Platform', 'UserReply', 'Reformulated_Reply', 'YesNoList']].copy()
        
        for i, row in enumerate(data['Reformulated_Reply']):
            for j, item in enumerate(row):
                data.loc[i, 'Reformulated_Reply'][j] = f"第{j+1}筆：{item}\n" + "-" *20 + "\n"
                


        # 匯出資料框
        static_html.export_dataframe(id="data", dataframe = display_data, table_class='table', inside_expandable=True)
        
        # 創建並返回 HTML 字串
        return static_html.create_html(return_type="String")

    def save_to_html(self, data: pd.DataFrame) -> str:
        html_content = self.generate_html_content(data)
        now = datetime.now().strftime('%Y_%m_%d %H:%M:%S')
        file_path = f'{self.root_path}/Issue_web_{now}.html'
        try:
            with open(file_path, 'w', encoding='utf-8-sig') as b:
                b.write(html_content)
            print("Successfully saved to html")
            return file_path
        except Exception as e:
            print(f"Error saving HTML: {e}")
            return None

class EmailSender:
    """負責發送電子郵件"""
    def send_email(self, sender: str, receiver: str, password: str, data: pd.DataFrame, report_generator: ReportGenerator):
        html_content = report_generator.generate_html_content(data)
        now = datetime.now().strftime('%Y_%m_%d %H:%M:%S')
        file_name = f'Issue_web_{now}.html'

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = Header(f'Issue_web_{now}', 'utf-8').encode()

        body = "附檔是有問題的評論，請查收"
        msg.attach(MIMEText(body, 'plain'))

        part = MIMEApplication(html_content.encode('utf-8'), Name=file_name)
        part['Content-Disposition'] = f'attachment; filename="{file_name}"'
        msg.attach(part)

        context = ssl.create_default_context()
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender, password)
                server.sendmail(sender, receiver, msg.as_string())
            print("Successfully sent email")
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
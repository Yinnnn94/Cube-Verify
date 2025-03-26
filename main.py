import pandas as pd
import json
from openai import OpenAI
from conflict_with_multi_class import OpenAIClient, TextProcessor, ReportGenerator, EmailSender
import requests
from datetime import datetime


# ======================== OpenAI API Key & Assistant ID & 寄信的資訊========================
api_key = 'open-api-key'
assistant_ids = {
    "ios": "ios_id",
    "android": "android_id"}

# 寄發有issue的資料 ＆ 寄發無問題可以匯入DB的資料
sender_email = 'sendmail@gmail.com' # 可以修改寄件人
receiver_email = 'receivermail@gmail.com' 
password = 'abcd efgh ijkl mnop' # 若修改寄件人記得要先把密碼改掉

# ============================= Prompt 設定 =======================================
conflict_warning_prompt = """
請以專業的角度分析 **「主體的回覆」** 與 **「生成的回覆」**，的關係為以下四種的何種類型。
1. **「主體的回覆」** 與 **「生成的回覆」** 文意相同且完整度雷同
2. **「主體的回覆」** 比 **「生成的回覆」** 明顯還更完整且文意相同
3. **「主體的回覆」** 比 **「生成的回覆」** 明顯還更不完整且文意相同
4. **「主體的回覆」** 有回答到 **「主體的評論」**  ，並且 **「生成的回覆」** 沒有回答到 **「主體的評論」**(答非所問)

請務必 **只輸出 JSON 格式的內容，不要額外加上任何文字或 `json` 標籤**。
回傳的格式：
{"Conflict_Type": , "Reason": "判定原因"}
ex : {"Conflict_Type": 2, "Reason": "因為..."}
"""

change_prompt = "請用中文把這句話換句話說5次(請盡量還原這句話的語氣)："
change_system_prompt = "You are a helpful assistant. The reply should be in Python list format, e.g., ['Response1', 'Response2', ..., 'Response5']"

check_system_prompt = "You are a helpful assistant. The reply should be only in Python list format, e.g., ['yes', 'no', ..., 'yes'], len(list) == 5. please use the Single quotation marks to wrap the 'yes' or 'no'."
check_prompt = "分析 **「reformulate_reply」的資訊 ** 是否有包含 **「主體的回覆」** 的關鍵資訊"


# ============================= 主程式 =======================================
def main(data_dict):

    # 初始化類別實例
    openai_client = OpenAIClient(api_key, None)  # 先不設置 assistant_id
    text_processor = TextProcessor()
    report_generator = ReportGenerator('path/to/report')
    email_sender = EmailSender()

    summarized_list = []
    for i, body in enumerate(data_dict):
        print(f"評論內容: {body['Comment']}")
        print(f"原始回覆: {body['UserReply']}")
        original_comment = body["Comment"].strip()
        user_reply = body["UserReply"].strip()
        platform = body["Platform"].lower()

        # 動態設置 assistant_id
        assistant_id = assistant_ids.get(platform)
        if assistant_id is None:
            print(f"Error Platform Format:{platform}")

            continue
        openai_client.assistant_id = assistant_id

        try:
            # 生成回覆
            response = openai_client.Reply(original_comment)
            print(f"生成回覆: {response}")

            # 檢查與原始回覆的衝突並轉成json格式
            conflict_user_prompt = f"主體的評論：{original_comment}\n主體的回覆：{user_reply}\n生成的回覆：{response} ，請幫我注意一定要以json格式回覆"
            conflict_check_result = openai_client.MakeCompletions(conflict_warning_prompt, conflict_user_prompt, 'o3-mini')
            conflict_check_result = json.loads(conflict_check_result)
            print(f"衝突檢查結果: {conflict_check_result}")
            print('已檢查完畢是否有衝突，並進行分類了')
            
            if conflict_check_result['Conflict_Type'] in [1, 3]:
                print('「匯入的」回覆 與 生成的回覆 文意相同且完整度雷同')
                print('-' * 100)
                continue
            elif conflict_check_result['Conflict_Type'] in [2, 4]:
                print('「匯入的」回覆 比 生成的回覆 明顯還更完整且文意相同')
                url = 'add_kms_url'

                # 定義請求主體（Body）
                Body = {
                    "datas": [
                        {
                            "id": body["ReviewID"],
                            "title": body["Title"],
                            "quest": body["Comment"],
                            "response": body["UserReply"],
                            "platform": platform,
                            "datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), # 先以現在匯入評論時的時間當作datetime <- 未來可以修改
                            "rank": body["Rating"]
                        }
                    ]
                }

                try:
                    response = requests.post(url, json=Body)
                    if response.status_code == 200:
                        data = response.json()
                        print("API 回應：", data)
                    else:
                        print(f"請求失敗，狀態碼：{response.status_code}")
                        print(f"錯誤訊息：{response.text}")
                        continue
                except Exception as e:
                    print(f"API 請求錯誤：{e}")
                    continue
            
                # 換句話說5遍並回覆
                reformulation_prompt = change_prompt + original_comment
                reformulated_list = openai_client.MakeCompletions(change_system_prompt, reformulation_prompt, 'gpt-4o')
                reformulated_list = text_processor.TextToList(reformulated_list)
                print('已換句話說完畢')
                responses_list = []
                for sentence in reformulated_list:
                    response = openai_client.Reply(sentence)
                    responses_list.append(response)

                # 檢查與原始回覆的衝突
                chck_prompt = check_prompt + "「reformulate_reply」 : " + str(responses_list) + "「主體的回覆」 : " + body["UserReply"]
                YesNoList = openai_client.MakeCompletions(check_system_prompt, chck_prompt, 'o3-mini')
                YesNoList = text_processor.TextToList(YesNoList)
                yes_times = YesNoList.count('yes')
                no_times = YesNoList.count('no')

                summarized_list.append(
                    {
                        "original_index": i,
                        "Title": Body["datas"][0]["title"],
                        "Comment": Body["datas"][0]["quest"],
                        "Platform": Body["datas"][0]["platform"],
                        "UserReply": Body["datas"][0]["response"],
                        "Reformulated_Reply": responses_list,
                        "YesNoList": YesNoList,
                        "Yes_times": yes_times,
                        "No_times": no_times
                    }
                )    
                print('-' * 100)
        except Exception as e:
            print(f"處理評論失敗: {e}")
            continue

    # 創建 DataFrame
    if summarized_list:
        summarized_df = pd.DataFrame(summarized_list)
        issue_df = summarized_df[summarized_df["Yes_times"] != 5]
        want_to_export = summarized_df[summarized_df["Yes_times"] == 5]["original_index"].tolist()
        print(f"需要匯出的數據索引: {want_to_export}")
    else:
        print("沒有數據需要處理")
        summarized_df = pd.DataFrame()
        issue_df = pd.DataFrame()
        want_to_export = []

    # 生成報表並發送郵件
    if not issue_df.empty:
        export_path = report_generator.save_to_html(issue_df)
        if export_path:
            print(f"HTML 報表已保存至：{export_path}")
        send = email_sender.send_email(sender_email, receiver_email, password, issue_df, report_generator)
        if send:
            print("成功發送郵件")
        else:
            print("郵件發送失敗")
    else:
        print("沒有問題數據需要處理")

    # 返回最終結果
    final_return = {"datas": []}
    print(want_to_export)
    for i in want_to_export:
        final_return["datas"].append(data_dict[int(i)])
    if not final_return["datas"]:
        print("沒有數據需要匯出")
    print(f"最終返回數據: {final_return}")
    return final_return

# ============================= 測試區 =======================================
if __name__ == "__main__":
    df = pd.read_excel('path/test.xlsx')
    df = df.dropna(subset=['Platform', 'Comment', 'UserReply'])
    data_dict = df.to_dict(orient='records')
    main(data_dict)
# Cube Verify Program 🛡️

### 💼 專案概述
**Issue Analysis Tool** 是一個基於 Python 的應用程式，旨在協助分析使用者評論與其對應回覆之間是否存在語意上的衝突。該工具利用 OpenAI API 將評論進行語意改進（換句話說），並生成對應的回覆，隨後檢查這些回覆與原始回覆是否一致，並分類潛在的衝突類型。最終結果以 HTML 報表形式輸出，並可選擇透過電子郵件發送。

### 📌 核心功能
- **核心類別定義**：定義與 OpenAI API 交互、文本處理、報表生成及電子郵件發送的類別。
- **Streamlit 應用程式**：提供使用者介面，用於展示分析結果並進行互動查詢。  
適用場景包括客服回覆品質檢查、內容審核與自動化回覆系統的驗證。

[class-link]: https://github.com/Yinnnn94/Cube-AWS-Verify/blob/main/class.py
[main-link]: https://github.com/Yinnnn94/Cube-AWS-Verify/blob/main/main.py

### 🔄 流程圖解說 
<img src="https://github.com/Yinnnn94/Cube-AWS-Verify/blob/main/flow_chart.png" width="50%">

#### 🔗 [核心類別功能][class-link]
- **OpenAI API 交互**：透過 `OpenAIClient` 類別生成改進語句及回覆，並進行衝突檢測。
- **文本處理**：使用 `TextProcessor` 將文本轉換為 Python 列表格式。
- **報表生成**：透過 `ReportGenerator` 將分析結果生成 HTML 格式的報表，並儲存至本地。
- **電子郵件發送**：使用 `EmailSender` 將報表作為附件發送至指定收件人。

#### 🔗 [Streamlit 應用程式功能][main-link]
- **資料輸入**：從 Excel 文件讀取評論資料（包括平台、評論內容及使用者回覆）。
- **語意改進**：對每條評論生成 5 種換句話說的版本。
- **衝突檢測**：檢查 AI 生成的回覆與原始回覆是否一致，並標記衝突的回覆。
- **衝突分類**：將衝突類型分為「亂回答」或「回答不完整」。
- **結果展示**：以表格形式展示分析結果，並提供詳細查詢功能。

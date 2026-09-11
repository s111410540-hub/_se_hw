# AI 協同開發歷程與提示詞紀錄 (AI Collaboration Log)

## 學生與專案資訊
- **學生**：邱瀚緯 (學號: 40)
- **學校/課程**：國立金門大學資訊工程系《現代軟體工程》
- **專案**：作業 1 - 類似 curl 的命令列程式 (mycurl)

---

## 階段一：可行性分析與架構規劃

### 提示詞 (Prompt)
> 教授要求使用 AI 做一個類似 curl 的專案程式，請幫我分析可行性，並規劃符合軟體工程規範的系統架構與時程。

### AI 協助產出
1. **可行性評估**：
   - 區分三種深度：Level 1（高階庫封裝）、Level 2（手刻 HTTP/1.1 協議 + Socket/TLS）、Level 3（自製加密握手）。
   - 建議採用 **Level 2**，以平衡教學深度（資工網路協議底層）與交付時程。
2. **模組架構切分**：
   - 規劃 `CLI Parser`、`URL Parser`、`Transport Engine`、`Protocol Engine`、`Client Controller` 五大模組，符合 SOLID 原則。

---

## 階段二：模組實作與測試驅動開發 (TDD)

### 提示詞 (Prompt)
> 1. 請實作 `mycurl.url_parser` 模組，能夠解析 URL、自動補全 http/https 預設 port，並解析重定向 relative URL。
> 2. 請實作 `mycurl.protocol` 模組，依照 RFC 9112 規範建立 HTTP/1.1 請求字串，並實作狀態碼、大小寫不敏感 Headers 字典，以及包含 `Content-Length` 與 `Transfer-Encoding: chunked` 的響應解碼。
> 3. 請實作 `mycurl.transport` 模組，使用 Python 原生 `socket` 與 `ssl` 模組建立連線。

### 開發過程發現的 Bug 與修復 (Edge Cases)
在執行單元測試 `tests/test_url_parser.py` 時，測試套件回報錯誤：
* **錯誤現象**：輸入非支援協議（如 `ftp://example.com`）時，未能拋出 `ValueError`。
* **原因分析**：原代碼使用 `if not clean_url.startswith(("http://", "https://")):`，導致 `ftp://` 被誤當作沒有 scheme 而在前面自動補上 `http://` 變成 `http://ftp://example.com`。
* **修復方案**：增加對 `://` 的獨立判定，若已有自訂協議且非 http/https 則直接拋出例外，驗證通過。

---

## 階段三：整合測試與實機驗證

### 提示詞 (Prompt)
> 請撰寫一個本機 Mock HTTP Server 的整合測試，能夠測試 GET、POST Echo、自訂 Header、302 重定向與檔案儲存功能。

### 驗證成果
* 執行 `python -m unittest discover -s tests -v`：
  - 共 19 個測試案例全數通過 (19/19 OK)。
  - 成功於真實公開伺服器 (`https://example.com`) 進行 TLSv1.3 握手連線與 Chunked Transfer 解碼。

---

## 學習心得與軟體工程體會

1. **AI 是強大的結對程式設計師（Pair Programmer）**：
   AI 能夠快速提供符合 RFC 規範的代碼雛形，但軟體工程師必須具備**架構審查**與**單元測試**的能力，才能抓出邊界錯誤（如 URL scheme 誤判）。
2. **高內聚低耦合的價值**：
   將 Socket 傳輸與 HTTP 封包解析抽離，使得單元測試可以透過記憶體虛擬 Socket（`DummySocket`）進行快速測試，無須依賴外網，大大提升 CI/CD 穩定性。

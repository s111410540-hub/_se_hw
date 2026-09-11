# mycurl - 輕量化 HTTP/1.1 命令列客戶端

本專案為國立金門大學資訊工程系《現代軟體工程》作業 1。  
透過 AI 協同開發（Pair Programming），基於底層網路通訊協定自主實作類似 `curl` 的命令列 HTTP/1.1 客戶端工具。

---

## 🎯 專案特色與架構

本專案**不依賴任何第三方高階 HTTP 函式庫**（如 requests 或 urllib3），而是直接基於作業系統的 **TCP Socket** 與 **TLS/SSL 加密通道**，嚴格依循 **RFC 9110 / RFC 9112** 標準自行實作請求封裝與響應解析。

### 模組化架構圖

```
┌────────────────┐     ┌─────────────────────┐     ┌────────────────────────┐
│   CLI Parser   │ ──> │  Client Controller  │ ──> │   URL & Port Parser    │
│  (mycurl.cli)  │     │   (mycurl.client)   │     │  (mycurl.url_parser)   │
└────────────────┘     └──────────┬──────────┘     └────────────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │    Transport Engine (TCP Socket)     │
               │  - DNS 解析 (IPv4 / IPv6)            │
               │  - SSL/TLS 握手封裝 (mycurl.transport)│
               └──────────────────┬───────────────────┘
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │      HTTP/1.1 Protocol Engine        │
               │  - RFC 9112 Wire-format Builder      │
               │  - Content-Length & Chunked 解碼     │
               │  - 狀態行與標頭解析 (mycurl.protocol) │
               └──────────────────────────────────────┘
```

---

## 🚀 支援功能 (Features)

| 參數 | 說明 | 範例 |
| :--- | :--- | :--- |
| `url` | 目標請求網址（支援 HTTP 與 HTTPS） | `python mycurl.py https://example.com` |
| `-X`, `--request` | 指定 HTTP 請求方法 (GET, POST, PUT, DELETE...) | `-X POST` |
| `-H`, `--header` | 自訂 HTTP Header（可重複使用） | `-H "Accept: application/json"` |
| `-d`, `--data` | HTTP POST 資料負載（指定後預設 Method 為 POST） | `-d "username=admin"` |
| `-v`, `--verbose` | 詳細輸出模式，顯示連線握手細節與請求/響應標頭 | `-v` |
| `-i`, `--include` | 輸出結果包含 HTTP 響應標頭 | `-i` |
| `-o`, `--output` | 將回傳內容儲存至指定檔案 | `-o result.html` |
| `-L`, `--location` | 自動跟隨 HTTP 301/302 重定向 | `-L` |
| `-u`, `--user` | 支援 HTTP Basic 驗證 | `-u user:pass` |
| `--timeout` | 設定連線與傳輸逾時秒數（預設 10 秒） | `--timeout 5` |

---

## 💻 快速開始 (Quick Start)

### 執行環境需求
* Python 3.8+（已在 Python 3.14 嚴格測試相容）
* 無須安裝額外套件（零外部依賴）

### 基本使用範例

#### 1. 發送 GET 請求
```bash
python mycurl.py https://example.com
```

#### 2. 詳細模式 (`-v`) 觀察 SSL 握手與 HTTP 封包
```bash
python mycurl.py -v https://example.com
```

#### 3. 發送 POST 請求並帶自訂標頭與 Body
```bash
python mycurl.py -X POST -H "Content-Type: application/json" -d '{"message": "hello"}' http://127.0.0.1:8080/api
```

#### 4. 自動跟隨重定向 (`-L`)
```bash
python mycurl.py -v -L http://example.com
```

#### 5. 輸出包含 Response Headers 並存檔
```bash
python mycurl.py -i -o page.html https://example.com
```

---

## 🧪 自動化測試 (Automated Testing)

本專案奉行**測試驅動開發 (TDD)**，包含單元測試與本機 Mock HTTP Server 整合測試：

```bash
# 執行所有測試案例
python -m unittest discover -s tests -v
```

測試涵蓋項目：
1. **URL 解析器測試**：HTTP/HTTPS 自動推導、Port 判定、相對與絕對路徑 Redirect 解析。
2. **協議引擎測試**：RFC 請求序列化、大小寫不敏感 Headers 字典、Content-Length 與 Transfer-Encoding: Chunked 解碼。
3. **整合測試**：建立 local socket HTTP server，實測 GET、POST Echo、自訂 Header 驗證、302 Redirect 追蹤、檔案存取。

---

## 📂 專案檔案結構

```
hw1/
├── mycurl/               # 核心程式套件
│   ├── __init__.py       # 版本宣告
│   ├── __main__.py       # 模組入口點 (python -m mycurl)
│   ├── cli.py            # 命令列參數解析
│   ├── client.py         # 客戶端調度器與重定向控制
│   ├── protocol.py       # HTTP/1.1 RFC 協議編解碼
│   ├── transport.py      # TCP Socket 與 TLS/SSL 傳輸層
│   └── url_parser.py     # 網址解析與正規化
├── tests/                # 自動化測試套件
│   ├── test_integration.py # 本機 Mock Server 整合測試
│   ├── test_protocol.py    # 協議序列化與 Chunked 單元測試
│   └── test_url_parser.py  # 網址解析單元測試
├── AI_PROMPTS.md         # AI 協同開發歷程與 Prompt 記錄
├── FEASIBILITY_AND_PLAN.md # 教授要求之可行性分析與開發時程規劃報告
├── mycurl.py             # 快速啟動入口腳本
└── README.md             # 專案文檔說明
```

---

## 📑 相關軟工報告文件
* 📊 [作業可行性分析與規劃報告 (FEASIBILITY_AND_PLAN.md)](./FEASIBILITY_AND_PLAN.md)
* 🤖 [AI 協同開發歷程與提示詞紀錄 (AI_PROMPTS.md)](./AI_PROMPTS.md)


# 美術工程工作台

由需求驅動的 3D 美術資產製作、驗收與歸檔；本檔是 domain 用語表，不是規格。

## Language

### Workspace identity

**Request digest**:
需求內容的唯一身分：以排序鍵、無多餘空白的 UTF-8 JSON 計算的 SHA-256；排版、鍵序或 BOM 不同但內容相同，即為同一個需求。
_Avoid_: 需求檔案雜湊、request file hash、request sha

**File digest**:
一個檔案原始 bytes 的 SHA-256，用來認定交付檔、artifact 或參考圖是否為同一份。
_Avoid_: 檔案指紋、checksum

**Asset ID**:
工作台內所有可命名事物共用的識別碼文法（需求、資產、專案、檢查項、trial、Hyper3D operation）；可含點分段，例如 `evoloot.weapon.iron_sword_neutral`。
_Avoid_: operation ID 文法、slug、key

**Recorded path**:
寫在 JSON 紀錄裡、相對於 repo 根目錄的 POSIX 路徑；重新 clone 後必須仍能定位同一檔案。
_Avoid_: 證據路徑、相對路徑

**Catalog asset**:
`catalog/assets.json` 中的批量需求條目；需求可用選填的 `catalog_asset_id` 連到它。
_Avoid_: 資產需求、demand asset

**Command path**:
人在 shell 輸入的命令列路徑參數；可為絕對路徑或使用反斜線，但必須落在 repo 內，且不得寫入紀錄。
_Avoid_: 本機路徑、local path

### Operation ledger

**Operation ledger**:
付費生成操作的唯一帳本，保存在 `runs/hyper3d/operations/`；決定哪些需求與 Catalog asset 被保留，以及離線規劃是否必須停止。
_Avoid_: runs 紀錄、journal、交易鎖

**Operation**:
一次付費生成從準備到下載的生命週期；狀態只描述這筆生成，不描述資產的美術或交付驗收。
_Avoid_: 任務、job、asset status

**Blocking operation**:
狀態為 pending、unknown，或無法辨識、無法推導其需求的 Operation；存在時離線規劃與新提交都必須停止，先核對原操作。
_Avoid_: 進行中操作、未完成操作

**Legacy import record**:
為早於現行 client 的 Operation 補登的帳本紀錄，明寫需求／Catalog asset 並附原始證據雜湊；原始檔案不改寫，也不能用來查詢或下載。
_Avoid_: 遷移紀錄、補帳

### Contract evaluation

**Contract evaluation**:
一份證據對目前需求的評估結果：哪些必要檢查已有證據、證據是否對應目前需求，以及哪些 Gate failure 存在；只核對申報與檔案完整性，不判斷美術品質。
_Avoid_: 驗收、assessment 結果、審查

**Gate failure**:
使候選版本不能保留的非美術缺口：非美術檢查申報失敗、沒有登記交付檔，或缺少需求指定的交付格式；以代碼識別，不以訊息文字判斷。
_Avoid_: blocker、技術失敗

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

**Command path**:
人在 shell 輸入的命令列路徑參數；可為絕對路徑或使用反斜線，但必須落在 repo 內，且不得寫入紀錄。
_Avoid_: 本機路徑、local path

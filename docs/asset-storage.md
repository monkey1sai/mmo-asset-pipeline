# 工程師資產與 Git LFS 保存

工程師素材是 repo 的一部分。需求、原始 master、後製版本、交付包、預覽、素材索引與驗收證據都保存在 repo；`.gitignore` 只排除工具暫存及秘密，不排除 assets／deliveries。模型的雲端展示頁是來源資訊，不能代替交付檔案。

## 資料布局

| 位置 | 必須保留的內容 |
| --- | --- |
| `assets/raw/<asset-id>/v001/` | 原始模型、相依貼圖及必要來源包；保留 master，不原地覆寫 |
| `assets/processed/<asset-id>/v002/` | 後製模型與可編輯源檔，記錄來源版本、操作與轉換 |
| `deliveries/<request-id>/v001/` | 最終輸出、依賴、manifest、README、預覽及驗收索引 |
| `library/index.json` | 檔案路徑、版本、來源、用途、已驗／未驗及重用限制 |
| `requests/`／`runs/` | 需求與不可混淆的提交、扣點、下載、QA 證據 |

相依檔用相對路徑，不引用 Downloads、另一個遊戲 repo 或個人桌面。交付包應能獨立搬移；repo 同時保存可修訂的來源。範例規格與候選不能標為已交付，版本變更需更新 manifest 及 SHA-256。

## LFS 與一般 Git

`.gitattributes` 讓模型格式、可編輯 Blender 源檔、二進位依賴及 ZIP 由 LFS 保存；assets／deliveries 中的貼圖也走 LFS。這是依資產類型的預設，避免大型檔案先進一般 Git 歷史。文字需求、索引、manifest、README、QA 與小型 runs 證據截圖維持一般 Git。

本機已存在 `git-lfs/3.4.0` 及標準 clean／smudge／process／required 設定；這次不安裝 hook、不修改全域設定。新增格式時先確認需求與相依性，再補 `.gitattributes`，不要把憑證或暫存當素材加入。

協調者只暫存核對過的模型、貼圖、索引及 QA；禁止盲目 `git add .`。`git add`、commit、Git／LFS push 依當次使用者具體授權，核對遠端可見性與既有歷史。推送授權不擴張為變更 repo 可見性、Hyper3D 公開發布、加購配額或修改全域設定。

## 保存證據與還原

Git 保存 LFS 指標，內容含版本、`oid sha256` 及檔案大小；LFS 保存實際資料。暫存後逐檔核對：工作區實際 SHA-256／大小 = 索引指標 = 本機 `.git/lfs/objects/` 物件，並檢查 `git lfs ls-files`。文件或指標存在不能單獨證明模型資料完整。

正式讓資產在別的電腦「跟著 repo 走」需經授權的 commit、Git 與 LFS 物件遠端同步，以及全新 clone 的 LFS 還原及雜湊檢查。未完成這些前，只能宣稱本機已納管，不能宣稱遠端備份或移機還原已驗證。同步需確認服務接受物件且未回報配額不足，不能自行購買；成功傳輸不代表已查得帳戶剩餘配額。實際保存進度見 `runs/qa/git-portability-20261002.json`，較早 QA 保留當時狀態。

新電腦具備 Git／Git LFS 後，clone repo 並在根目錄執行 `git lfs pull`；核對 `git lfs ls-files`、模型實際檔案大小及素材庫／QA 的 SHA-256。若物件缺少或雜湊不符就停止使用，保留錯誤與 ref；不要把指標當完整模型。

保持 hooks 停用的操作中，可在已授權範圍明確執行 `git lfs push origin HEAD`，確認大型物件成功後再普通 Git push；不需安裝 pre-push hook。推送不得覆寫遠端歷史或略過分支保護。

目前兩個候選共有四份 GLB、一張 emissive PNG。既有需求偏差保留在 QA／素材庫，LFS 保存不改驗收狀態。沒有正式交付包，`deliveries/README.md` 是之後實際交付的保存契約。

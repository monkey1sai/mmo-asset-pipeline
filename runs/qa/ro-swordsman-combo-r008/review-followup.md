# r008 交付前覆核補充

本文件在階段關帳及 `final-verification.json` 之後追加，保留原帳、時計、四候選與證據雜湊。
`independent-final-review.md` 是 `/root/hand_phase_review` 的原樣報告；Astra/high 審查屬 advisory，
不構成交付批准。Jev 最終路由觀測 `92e5ad07-d6ba-4d6b-8b6d-0f0fa1ae6934` 要求 architecture
review；這是確定性路由，`provider_called=false`、`executed=false`。

**VERIFIED：保存端點不只缺兩指接觸。**掌根 edge 277–278 靜止長 8.917424 mm，
重開求值長 0.593593 mm，最小邊比 0.0665655768，縮短約93.34%；edge 372–388
從13.760541 mm降至2.989338 mm，最大絕對變化10.771203 mm。這是局部嚴重壓縮
的數值證據，不是精確體積、骨心或拓樸原因已確診。原3／1／3／0／4接觸失敗保持。

**VERIFIED：重開的求值頂點指紋不同。**`point_fingerprint_equal=false`；靜止geometry、
UV、來源屬性、權重、原16骨位和未縮放劍仍通過各自核對。保存／重開的實際basis矩陣
最大分量差1.490116119e-7，最大絕對邊長變化的彙總差6.22755e-9 m；這些數字不能
證明全部逐點差都在特定容差內。原求值點陣列未歸檔，所以本次只宣稱受測失敗結果
重現，不宣稱逐點等價，也不把指紋差直接定為浮點誤差。

**下一方法修正（INFERRED／未執行）：**先定位上述掌根壓縮及各指握柄可達性，
再決定必要四指權重、關節位置或MCP／虎口面流修訂。保留拇指向量改善；不因這次
失敗斷言所有骨心錯誤或必須重拓樸。舊 `next-method-proposal.json` 保留為當時草稿；
本補充是後續選擇的推薦表述。若實證需要大幅改形，遵守先設計圖片→Hyper3D→
Blender流程，並重新核對造型、UV與功能。新階段須明確允許相應保護區改動，不自動
開第五候選或重設舊预算。

本輪歸檔驗證通過145組檔案／雜湊引用、42份QA JSON及178支Python語法；
119項unittest已通過；歸檔後再驗39筆pipeline清單schema通過。
完整角色／300幀／60fps／左右手／裝備／VFX／新動畫GLB仍未通過或未執行。
新增API提交0、點數0；stage、commit、push繼續等待人驗證。沒有新增背景產製。

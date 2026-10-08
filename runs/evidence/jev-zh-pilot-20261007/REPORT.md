# Jev 中文遊戲美術需求試點

狀態：partial；7/20 案例有實際 provider 回覆。

Codex 依專案規則預先編寫的合成案例與預期標籤；尚未經人類覆核

分類對照是 intake 的 static_prop 預設，並非語意分類器。排序對照為相同人工候選集合的中文二字組字面相似度；不宣稱全庫檢索品質。

分類：Jev 7/7；intake 預設 5/20。
素材 Choice：7/7。
同批已跑案例的字面排序：{'evaluated_cases': 7, 'top1_correct': 7, 'top3_correct': 7, 'mrr': 1.0}；Jev Score 排序：{'evaluated_cases': 7, 'top1_correct': 7, 'top3_correct': 7, 'mrr': 1.0}。
待覆核：0；tokens／估算：{'input_tokens': 20488, 'output_tokens': 1449, 'estimated_usd': 0.0008605, 'actual_charge': 'UNVERIFIED'}；實際扣款未核對。
實際模型：['jev-1.13.0']；延遲：{'measurement': '每次 provider 呼叫至契約核對完成；不含案例編寫、離線準備或實際美術製作', 'mean_ms': 243.19, 'median_ms': 236.9, 'max_ms': 297.02}。

| 遊戲類型 | 中文需求 | 預期類型 | Jev 類型 | 建議素材 | 結果 |
|---|---|---|---|---|---|
| 動作 ARPG | 暗黑奇幻動作遊戲要一把樸素的鏽蝕鐵劍。只做獨立靜態武器 GLB，完整單一劍刃，不要雙叉刃、金色裝飾，也不需要骨架。 | static_prop | static_prop | fx-plain-sword | 符合預期／僅建議 |
| 動作 ARPG | 做一名原創卡通劍士，完整人形角色要綁骨、可換劍，能跑步、待機與揮劍。武器和身體要分開，交付 GLB。 | rigged_character | rigged_character | fx-rig-fighter | 符合預期／僅建議 |
| MMORPG | 線上角色扮演遊戲需要手繪風長袍治療師，完整角色需骨架與權重，能施法、走路及待機，長袍不要和雙腿黏在一起。 | rigged_character | rigged_character | fx-rig-healer | 符合預期／僅建議 |
| MMORPG | 城鎮廣場要一座長袍人物石雕，只作靜態景物。不需要骨架、走路或施法動畫，請交付單件石材模型。 | static_prop | static_prop | fx-healer-statue | 符合預期／僅建議 |
| 射擊 FPS／TPS | 第一人稱射擊遊戲要寫實步槍模型。槍機和扳機必須分開，能往復拉動槍機及旋轉扳機；本次不做持槍角色或人形骨架。 | interactive_prop | interactive_prop | fx-rifle-parts | 符合預期／僅建議 |
| 射擊 FPS／TPS | 需要科幻基地走廊套件，牆、地板、頂板、轉角採統一模數，接合邊對齊，可反覆拼接成不同路線；不做整條合併走廊。 | modular_environment | modular_environment | fx-corridor-kit | 符合預期／僅建議 |
| 生存製作 | 生存遊戲需要可以掀蓋的木製補給箱。箱體與箱蓋分件，箱蓋繞後側鉸鏈開關，必須保留 pivot；不要封死箱蓋的裝飾箱。 | interactive_prop | interactive_prop | fx-hinged-crate | 符合預期／僅建議 |
| 生存製作 | 場景要石座、鐵盆、炭火組成的火盆。只要靜態道具，炭火用自發光材質，不把實體火焰黏在模型；不要金屬支腳代替石座。 | static_prop | — | — | failed |
| 策略 RTS | 中式戰場需要城牆拼接套件，直牆、角牆、垛口採固定接合尺寸，可重複排成不同城池。門洞只作靜態模組，不要求開門。 | modular_environment | — | — | NOT_RUN |
| 策略 RTS | 魏軍軍營要一棟木構營房，牆身與屋頂分件方便改材質。本次是固定擺放的單棟建築，不需要開門、人物骨架或反覆拼接的場景模組。 | static_prop | — | — | NOT_RUN |
| 塔防 | 塔防要一座可以瞄準的砲塔，底座、旋轉盤、砲管分件，盤能左右旋轉，砲管可俯仰；不要底座與砲管融合的固定雕像。 | interactive_prop | — | — | NOT_RUN |
| 療癒農場模擬 | 農場遊戲要大頭短身的 Q 版園丁 NPC，完整人形需綁骨與手部掛點，能待機、走路和鋤地，農具要分件。 | rigged_character | — | — | NOT_RUN |
| 療癒農場模擬 | 做 Q 版稻草人放在田裡當裝飾。固定木架與稻草，不是 NPC，不需要骨架、鋤地、走路或其他動畫。 | static_prop | — | — | NOT_RUN |
| 競速 | 賽車遊戲需要直線、彎道、坡道三種路段套件，寬度和接合點一致，可拼出不同賽道；不要整圈封閉賽道的單網格。 | modular_environment | — | — | NOT_RUN |
| 競速 | 做可操作的寫實賽車模型，車輪能滾動、前輪能轉向、方向盤能旋轉，車體與四輪及方向盤分件並設定 pivot。不需要人形角色骨架。 | interactive_prop | — | — | NOT_RUN |
| 解謎平台 | 卡通解謎場景要雙扇木門，門框、左門扇、右門扇分離，兩扇門各自繞鉸鏈開關，不能把門框門扇合成一件。 | interactive_prop | — | — | NOT_RUN |
| Roguelike 地城 | 低多邊形手繪地城需要六角房間、走道與入口模組，固定邊長且可以程序拼接；不是一次建好的完整地城場景。 | modular_environment | — | — | NOT_RUN |
| 卡牌對戰 | 本次只要 2D 卡面插畫和透明背景 UI 圖示，PNG 交付，不需要任何 3D 模型、GLB、骨架或場景。 | out_of_scope | — | — | NOT_RUN |
| 恐怖冒險 | 恐怖遊戲要一個人物放在場景裡，但還沒決定是固定擺件、可動 NPC 還是會追人的敵人；骨架與動作需求之後再確認。 | needs_clarification | — | — | NOT_RUN |
| 生存製作 | 生存遊戲要做一個場景素材，用途、造型以及是否互動都還沒決定，請先列待確認事項，不要直接決定製作哪一件。 | needs_clarification | — | — | NOT_RUN |

限制：合成案例、人工設計候選集合、單次抽樣，未經人類覆核；不能推廣成真實委託準確率、全庫檢索能力、模型美術／動畫／引擎驗收或節省總成本。

0.8 只作本試點待覆核標記，不是校準完成或自動執行門檻。所有需求維持 draft，所有製作路線維持 review_existing。

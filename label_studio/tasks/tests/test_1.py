
你在界面上点"Import"，选了 100 张药片图
        ↓
后端批量写入 Task 表（每图一行）：

id  | project_id | data                                | is_labeled | overlap | inner_id
----+------------+-------------------------------------+------------+---------+---------
1   | 1          | {"image": "/upload/001.jpg"}        | false      | 2       | 1
2   | 1          | {"image": "/upload/002.jpg"}        | false      | 2       | 2
3   | 1          | {"image": "/upload/003.jpg"}        | false      | 2       | 3
... | ...        | ...                                 | ...        | ...     | ...
100 | 1          | {"image": "/upload/100.jpg"}       | false      | 2       | 100



后端从 `Task.objects.filter(project=..., is_labeled=False)` 里按 `sampling` 规则（顺序 / 随机 / 不确定性）捞一行出来，把 `data["image"]` 给前端，前端加载图片，让标注员画框 ——**一屏 = 一个 Task**。
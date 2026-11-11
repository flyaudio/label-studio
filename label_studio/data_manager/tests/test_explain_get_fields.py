"""用「可运行的测试」解释 data_manager/managers.py 的 get_fields_for_evaluation。

跑法（在 label-studio 根目录、test 环境）：
    python -m pytest label_studio/data_manager/tests/test_explain_get_fields.py -v

这个函数干的事：
    返回「数据管理器展示任务列表时，需要 annotate（现场计算）的虚拟字段名」。
    比如 annotators（标注者）、agreement（一致率）这些不是 Task 表里存好的字段，
    需要 annotate 算出来；而 id、total_annotations 是表里本来就有，data.xxx 走另一套，
    所以要被 skip_regular 过滤掉。
"""
from unittest.mock import patch

from data_manager.managers import get_fields_for_evaluation
from data_manager.prepare_params import PrepareParams

# 模拟一个项目「所有列」的定义（真实场景由 _get_all_project_columns 从 label config 解析得到）。
# 每一列是一个 dict，id 是列名；parent == 'data' 表示它来自 task.data 这个 JSON。
COLUMNS = {
    'columns': [
        {'id': 'agreement'},                # 虚拟列：需要 annotate 算出来
        {'id': 'annotators'},               # 虚拟列：需要 annotate
        {'id': 'total_annotations'},        # Task 表的常规字段（不用 annotate）
        {'id': 'image', 'parent': 'data'},  # data 字段（图片）
        {'id': 'text', 'parent': 'data'},   # data 字段（文本）
        {'id': 'data'},                     # data 本身（特殊项，会被 - {'data'} 去掉）
    ]
}


# ========== 测试1：没有 hiddenColumns，只看排序/筛选字段 ==========

def test_没有隐藏列时_只收集排序字段():
    """data 里没有 hiddenColumns → 完全不碰「列定义」，只从 ordering 提取字段。"""
    # params = PrepareParams(project=1, ordering=['tasks:-agreement'], data={})
    params = PrepareParams(project=1, data={'hiddenColumns': ['tasks:data.image', 'tasks:agreement']})

    fields = get_fields_for_evaluation(params, user=None)

    # 'tasks:-agreement' → 去掉 'tasks:' 和 '-' → 'agreement'
    # 没隐藏列，所以只返回 ordering 提取出的这个字段
    # assert fields == ['agreement']


# # ========== 测试2：有 hiddenColumns，返回「可见的虚拟列」 ==========

# def test_有隐藏列时_返回可见的虚拟计算列():
#     """核心逻辑：可见列 = 全部列 - 隐藏列，再过滤掉常规字段和 data 字段。"""
#     # 两种模式都隐藏了 image（data 列）和 agreement（虚拟列）
#     params = PrepareParams(project=1, data={'hiddenColumns': ['tasks:data.image', 'tasks:agreement']})

#     with patch('data_manager.managers._get_all_project_columns', return_value=COLUMNS):
#         fields = get_fields_for_evaluation(params, user=None)
#         print("==fields=", fields)

#     # 可见列 = 全部 - {image, agreement} = {annotators, total_annotations, text}
#     # 再去掉「常规字段」(total_annotations) 和「data.xxx」(text)
#     # → 最后只剩虚拟列 annotators
#     assert set(fields) == {'annotators'}


# # ========== 测试3：skip_regular 的作用 ==========

# def test_skip_regular为False时_保留常规字段和data字段():
#     """skip_regular=False 时不过滤，能看到「常规字段」和「data.xxx」也留在结果里。"""
#     params = PrepareParams(project=1, data={'hiddenColumns': ['tasks:agreement']})

#     with patch('data_manager.managers._get_all_project_columns', return_value=COLUMNS):
#         fields = get_fields_for_evaluation(params, user=None, skip_regular=False)

#     # 不过滤：total_annotations（常规字段）和 data.image / data.text 都保留
#     assert fields == {'annotators', 'total_annotations', 'data.image', 'data.text'}


# # ========== 测试4：空隐藏列表 = 全部可见 ==========

# def test_空隐藏列表_等于所有虚拟列都可见():
#     """hiddenColumns 是空列表 [] 时，表示「两种模式都没藏任何列」，全部可见。"""
#     params = PrepareParams(project=1, data={'hiddenColumns': []})

#     with patch('data_manager.managers._get_all_project_columns', return_value=COLUMNS):
#         fields = get_fields_for_evaluation(params, user=None)

#     # 全部可见 → 过滤后剩下两个虚拟列
#     assert set(fields) == {'agreement', 'annotators'}

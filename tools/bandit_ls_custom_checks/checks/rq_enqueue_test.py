"""
rq_enqueue_test.py — 用可运行的测试代码解释 checks/rq_enqueue.py（B901 插件）

为什么要用"测试"来解释？
    插件本身不是"主动执行"的程序，而是被 bandit 框架回调的被动函数。
    单看源码容易产生三个疑问：
      1. 这个函数什么时候被调用？        → 装饰器注册机制（TestRegistration）
      2. 黑名单 FORBIDDEN_METHODS 怎么起作用？→ 命中/放行行为（TestHit / TestPass）
      3. 返回的 bandit.Issue 是什么？    → 违章单内容（TestHit 内断言）
    测试把这些问题变成一条条可执行、可断言的语句：
    跑一遍 = 亲眼看到插件的每一种行为。

运行（任意目录，标准库 unittest，无需安装 pytest）：
    python rq_enqueue_test.py -v

依赖：需要 bandit（pip install bandit），因为插件本身 import bandit。
"""

import os
import sys
import types
import unittest

# 把 checks/ 的父目录（bandit_ls_custom_checks/）加入导入路径，
# 这样无论从哪个目录运行本文件，`from checks.rq_enqueue import ...` 都能成功。
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import bandit
    from bandit.core import test_properties as test
    from checks.rq_enqueue import FORBIDDEN_METHODS, direct_rq_enqueue
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "缺少依赖 bandit：请先执行 `python -m pip install bandit`\n"
        f"原始错误：{exc}"
    ) from exc


def make_context(call_function_name):
    """模拟 bandit 扫描到一次函数调用时，塞给插件函数的 context 对象。

    bandit 的真实 context 里有更多字段（调用参数、文件路径、行号……），
    但本插件只用到 call_function_name 一个属性，测试只需模拟这一个。
    """
    return types.SimpleNamespace(call_function_name=call_function_name)


class TestRegistration(unittest.TestCase):
    """疑问 1：装饰器到底做了什么？—— 答案是"注册元数据"。

    bandit 并不"认识"我们的函数，它靠两个装饰器挂在函数上的元数据来调度：
      - @test.checks('Call')  → 函数挂上 _checks = ('Call',)
        bandit 遍历 AST 时，遇到函数调用节点，查注册表里 _checks 含 'Call' 的函数并调用它
      - @test.test_id('B901') → 函数挂上 _test_id = 'B901'
        报告里用这个编号标识规则
    """

    def test_checks_decorator_registers_call_trigger(self):
        # 断言：@test.checks('Call') 的真实效果是给函数附加 _checks 元数据。
        # 注意：bandit 各版本的内部容器不同（1.9 实测为 list，早期为 tuple），
        # 因此断言"包含 'Call'"而不是断言具体容器类型，更健壮也更贴近语义。
        self.assertIn('Call', direct_rq_enqueue._checks)

    def test_test_id_decorator_sets_b901(self):
        # 断言：@test.test_id('B901') 的真实效果是给函数附加 _test_id 元数据
        self.assertEqual(direct_rq_enqueue._test_id, 'B901')

    def test_dispatch_only_for_call_nodes(self):
        # 模拟 bandit 的分派逻辑：节点类型匹配 _checks 才调用插件，
        # 否则根本不调用 —— 这就是"函数被动、框架主动"的体现。
        def dispatch(node_type, ctx):
            if node_type in direct_rq_enqueue._checks:
                return direct_rq_enqueue(ctx)
            return None

        # 'Call' 节点 → 调用插件 → 命中黑名单 → 返回 Issue
        self.assertIsNotNone(dispatch('Call', make_context('enqueue')))
        # 其他节点类型（如 Import、Assign）→ 不调用 → 永远没有 B901
        self.assertIsNone(dispatch('Import', make_context('enqueue')))
        self.assertIsNone(dispatch('Assign', make_context('enqueue')))


class TestBlacklist(unittest.TestCase):
    """疑问 2a：黑名单 FORBIDDEN_METHODS 是什么？"""

    EXPECTED = {
        'enqueue', 'enqueue_in', 'enqueue_at',
        'enqueue_call', 'enqueue_many', 'enqueue_job',
    }

    def test_blacklist_is_frozenset(self):
        # 用 frozenset（不可变集合）而非列表：
        # 1) 集合的 in 判断是 O(1) 哈希查找；2) 常量不可被意外修改
        self.assertIsInstance(FORBIDDEN_METHODS, frozenset)

    def test_blacklist_exactly_contains_six_rq_methods(self):
        # RQ 的 Queue 类共有 6 个入队方法，一个不多一个不少
        self.assertEqual(FORBIDDEN_METHODS, self.EXPECTED)


class TestHitBehavior(unittest.TestCase):
    """疑问 2b：命中黑名单时，插件返回什么？—— 一张 bandit.Issue "违章单"。

    bandit 对每次函数调用都会调用我们的插件：
      命中 → 返回 Issue（bandit 记入报告）
      未命中 → 返回 None（继续扫描，无事发生）
    """

    def test_each_forbidden_method_yields_issue(self):
        # 6 个禁止方法，每一个都必须触发检查（不许漏网）
        for name in FORBIDDEN_METHODS:
            with self.subTest(method=name):
                issue = direct_rq_enqueue(make_context(name))
                self.assertIsNotNone(issue, f'{name} 应触发 B901')

    def test_issue_is_bandit_issue_object(self):
        # 返回值的类型是 bandit.Issue —— bandit 报告系统认识的"违章单"
        issue = direct_rq_enqueue(make_context('enqueue'))
        self.assertIsInstance(issue, bandit.Issue)

    def test_issue_severity_is_medium(self):
        # severity（危害程度）= MEDIUM：直接入队危害中等（绕过了统一封装）
        issue = direct_rq_enqueue(make_context('enqueue'))
        self.assertEqual(issue.severity, bandit.MEDIUM)

    def test_issue_confidence_is_high(self):
        # confidence（确信度）= HIGH：函数名精确匹配，基本不会误报
        issue = direct_rq_enqueue(make_context('enqueue'))
        self.assertEqual(issue.confidence, bandit.HIGH)

    def test_issue_text_contains_detected_name(self):
        # 违章单文案里带上被调用的方法名，方便开发者定位
        issue = direct_rq_enqueue(make_context('enqueue_many'))
        self.assertIn('enqueue_many', issue.text)

    def test_issue_text_explains_the_fix(self):
        # 违章单不只报错，还告诉正确做法：改用 core.redis.start_job_async_or_sync()
        issue = direct_rq_enqueue(make_context('enqueue'))
        self.assertIn('start_job_async_or_sync', issue.text)
        self.assertIn('Direct RQ', issue.text)


class TestPassBehavior(unittest.TestCase):
    """疑问 2c：未命中黑名单时，插件返回什么？—— 返回 None，放行。"""

    def test_official_wrapper_passes(self):
        # 正确做法 start_job_async_or_sync 不在黑名单 → 不产生任何问题
        self.assertIsNone(direct_rq_enqueue(make_context('start_job_async_or_sync')))

    def test_similar_but_different_names_pass(self):
        # 只做精确匹配，不做前缀/模糊猜测：
        # 名字里"看起来像"enqueue 的都不会被误伤
        for name in ('dequeue', 'enqueue_inner', 'enqueue_and_run',
                     'enqueue_async', 'my_enqueue', 'Enqueue'):
            with self.subTest(name=name):
                self.assertIsNone(direct_rq_enqueue(make_context(name)))

    def test_unrelated_calls_pass(self):
        # 普通函数调用与 B901 无关
        self.assertIsNone(direct_rq_enqueue(make_context('print')))
        self.assertIsNone(direct_rq_enqueue(make_context('save')))


class TestRealBanditIntegration(unittest.TestCase):
    """端到端集成演示：让【真实 bandit】扫描代码，验证 B901 真的会被加载、触发、上报。

    普通情况下 bandit 只加载"已安装"的插件（通过 entry-points 机制）。
    bandit-ls-custom-checks 并没有 pip install 进当前环境，
    所以本测试在进程内把它"模拟成已安装插件"塞进 bandit 的插件注册表
    （效果等价于 `pip install -e tools/bandit_ls_custom_checks` 之后跑 bandit），
    然后走 bandit 的完整真实链路：
        AST 解析 → visit_Call → tester.run_tests('Call')
        → test_set 按 _checks 索引找到 B901 → Context 包装 → 调用插件 → 进报告
    """

    SAMPLE_VIOLATION = '''\
# 违规样例：直接调用 RQ 入队方法（应被 B901 抓到）
import django_rq


def launch(queue, task, tasks):
    queue.enqueue(task)            # 违规 1：普通入队
    queue.enqueue_many(tasks)      # 违规 2：批量入队
    queue.enqueue_job(task)        # 违规 3：任务对象入队
'''

    SAMPLE_CLEAN = '''\
# 合规样例：走官方封装的 start_job_async_or_sync（不应出现 B901）
from core.redis import start_job_async_or_sync


def launch(task):
    start_job_async_or_sync(task, task_id=1)
'''

    @classmethod
    def setUpClass(cls):
        # 把插件注册进 bandit 全局插件注册表（模拟 entry-point 安装的效果）
        from bandit.core import extension_loader

        ext_mgr = extension_loader.MANAGER
        if not any(getattr(p, 'name', None) == 'direct_rq_enqueue'
                   for p in ext_mgr.plugins):
            ext = types.SimpleNamespace(
                name='direct_rq_enqueue', plugin=direct_rq_enqueue,
            )
            ext_mgr.plugins.append(ext)
            ext_mgr.plugin_names.append(ext.name)
            # 注意：test_set 的过滤集合来自 plugins_by_id 的键，
            # 只加 plugins 不加 plugins_by_id 会导致 B901 被过滤掉。
            ext_mgr.plugins_by_id[direct_rq_enqueue._test_id] = ext
            ext_mgr.plugins_by_name[ext.name] = ext

    def _scan(self, source):
        """用真实 bandit 扫描一段源码，返回全部 Issue 列表。"""
        import tempfile

        from bandit.core import config as b_config
        from bandit.core import manager as b_manager

        with tempfile.TemporaryDirectory() as tmp:
            sample_path = os.path.join(tmp, 'sample.py')
            with open(sample_path, 'w', encoding='utf-8') as f:
                f.write(source)

            bm = b_manager.BanditManager(
                config=b_config.BanditConfig(),
                agg_type='file',
                debug=False,
                verbose=False,
                quiet=True,
                ignore_nosec=False,
            )
            bm.discover_files([sample_path], recursive=False)
            bm.run_tests()
            return bm.get_issue_list()

    def test_violation_reports_exactly_three_b901(self):
        # 违规样例里 3 次直接入队 → 报告里必须有 3 条 B901（每次调用都被检查）
        issues = self._scan(self.SAMPLE_VIOLATION)
        b901 = [i for i in issues if i.test_id == 'B901']
        self.assertEqual(len(b901), 3, f'B901 数量应为 3，实际为 {len(b901)}')

    def test_b901_issue_fields_in_real_report(self):
        # 真实报告里的 B901 违章单：ID/等级/文案/定位信息一应俱全
        issues = self._scan(self.SAMPLE_VIOLATION)
        b901 = next(i for i in issues if i.test_id == 'B901')

        self.assertEqual(b901.severity, bandit.MEDIUM)
        self.assertEqual(b901.confidence, bandit.HIGH)
        self.assertIn('start_job_async_or_sync', b901.text)
        # 报告还能定位到具体文件和行号（真实 bandit 的能力，单元测试模拟不了）
        # 注意：bandit 1.9 的 Issue 里文件名属性叫 fname（早期版本叫 filename）
        self.assertTrue(b901.fname.endswith('sample.py'))
        self.assertIsInstance(b901.lineno, int)
        self.assertGreaterEqual(b901.lineno, 1)

    def test_clean_sample_has_no_b901(self):
        # 合规样例：即使被完整扫描，也不应出现任何 B901
        issues = self._scan(self.SAMPLE_CLEAN)
        self.assertFalse(any(i.test_id == 'B901' for i in issues))


if __name__ == '__main__':
    unittest.main(verbosity=2)

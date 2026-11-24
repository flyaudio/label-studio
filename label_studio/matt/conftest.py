"""
`conftest.py` 放在测试目录下，pytest 自动识别，**不需要 import**
"""
import pytest
import requests
import requests_mock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session




# ===================== 数据库配置（改成你项目的连接串） =====================
DB_URL = "sqlite:///./test.db"  # 测试库，推荐sqlite；mysql：mysql+pymysql://user:pass@127.0.0.1:3306/test_db
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ===================== Fixture 定义 =====================

@pytest.fixture(scope="session")
def db_engine():
    """session级别：数据库引擎，整个测试会话只创建一次"""
    yield engine
    # 后置：测试全部跑完后关闭引擎
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    function级别（默认）：每个测试用例独立DB session
    ✅ 核心机制：开启事务，用例结束自动rollback，隔离测试数据
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session: Session = TestingSessionLocal(bind=connection)

    yield session

    # 后置清理：回滚事务 + 关闭连接，不会污染测试库
    session.rollback()
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function") #每个测试函数都新建一次
def req_mock():
    """
    全局requests_mock fixture
    function级别：每个用例全新mock实例，避免不同用例之间mock规则互相污染
    使用方式：在测试函数参数写上 req_mock
    """
    with requests_mock.Mocker() as m:
        # 这里可以放[所有用例通用的mock规则]
        # m.get("https://common.example.com/health", json={"status": "ok"})
        yield m
    # 退出with自动停止mock，无需手动stop


@pytest.fixture(scope="function")
def http_client(req_mock):
    """
    可选：封装一个预装好mock的requests Session，很多项目会用
    适合业务代码内部用requests.Session发请求的场景
    """
    session = requests.Session()
    with requests_mock.Mocker(session=session) as m:
        yield m, session

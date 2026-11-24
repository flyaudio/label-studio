"""
不需要 import conftest
"""
import requests


def test_request_mock_demo(req_mock):
    # 直接用全局的 req_mock
    req_mock.get("https://api.example.com/user/1001", json={"id": 1001, "name": "zhangsan"})
    resp = requests.get("https://api.example.com/user/1001")
    assert resp.json()["name"] == "zhangsan"


def test_db_operate(db_session):
    # 直接注入db_session，做数据库CRUD
    # user = User(name="test")
    # db_session.add(user)
    # db_session.commit()
    # 查询
    # res = db_session.query(User).first()
    assert db_session is not None

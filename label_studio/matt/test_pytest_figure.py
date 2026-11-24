import pytest
import requests
import requests_mock


@pytest.fixture
def user_data():
    """返回测试用的用户数据"""
    return {"id": 1001, "name": "zhangsan", "age": 20}

# 测试函数参数写 fixture 的名字，pytest自动注入
def test_user_name(user_data):
    assert user_data["name"] == "zhangsan"

def test_user_age(user_data):
    assert user_data["age"] == 20


# @pytest.fixture
# def demo_file():
#     # 前置：创建文件
#     f = open("tmp_test.txt", "w", encoding="utf-8")
#     yield f   # 传给测试函数
#     # 后置：测试结束后自动执行
#     f.close()
#
#
# def test_write_file(demo_file):
#     demo_file.write("hello pytest fixture")
#     demo_file.flush()




@pytest.fixture
def mock_http():
    # 前置：创建mocker
    with requests_mock.Mocker() as m:
        # 在这里注册通用mock规则
        m.get("https://api.example.com/hello", json={"msg": "hello"})
        yield m  # 把m对象传给测试用例
    # 退出with自动停止mock，不用手动stop

def test_get_hello(mock_http):
    resp = requests.get("https://api.example.com/hello")
    assert resp.json()["msg"] == "hello"
    assert mock_http.called

def test_custom_post(mock_http):
    # 用例里可以继续追加mock规则
    mock_http.post("https://api.example.com/save", json={"ok": True})
    resp = requests.post("https://api.example.com/save", json={"data": 1})
    assert resp.json()["ok"] is True



@pytest.fixture(scope="module") # 整个 py 文件只执行一次
def module_data():
    print("\n==== module fixture 只执行一次 ====")
    return [1,2,3]


@pytest.fixture
def token():
    return "abc123token"

@pytest.fixture
def headers(token):
    # 依赖上面的 token fixture
    return {"Authorization": f"Bearer {token}"}

def test_headers(headers):
    assert headers["Authorization"] == "Bearer abc123token"



@pytest.fixture(params=[1, 3, 5]) #运行后会自动跑 3 条用例
def odd_num(request):
    # request.param 拿到当前这一组参数
    return request.param

def test_is_odd(odd_num):
    assert odd_num % 2 == 1


"""
usage:
pytest test_pytest_figure.py -v
"""
import requests
import requests_mock #pip install requests requests-mock pytest


def test_basic_mock():
    # 1. 创建mocker上下文
    with requests_mock.Mocker() as m:
        # 注册 GET 请求的 mock：get请求，url匹配，返回json
        m.get("https://httpbin.org/get", json={"code": 200, "msg": "mock success"})

        # 发起请求（不会真访问外网）
        resp = requests.get("https://httpbin.org/get")

        # 断言
        print(resp)
        assert resp.status_code == 200
        assert resp.json()["msg"] == "mock success"

        # 查看调用信息
        assert m.called is True # 是否被调用过
        assert m.call_count == 1 # 调用次数
        last_req = m.last_request # 最后一次请求对象
        print("请求url:", last_req.url)
        print("请求方法:", last_req.method)


def query_user_info() -> dict:
    """待测试的业务函数，依赖http接口"""
    url = "https://api.example.com/user/1001"
    resp = requests.get(url, timeout=5)
    resp.raise_for_status()
    return resp.json()


def test_query_user_info():
    # 使用 fixture 风格的 requests_mock（pytest插件方式，也可以用with）
    with requests_mock.Mocker() as m:
        # mock get，指定返回json
        r_data = {"id": 1001, "name": "zhangsan", "age": 20}
        m.get("https://api.example.com/user/1001", json=r_data)

        result = query_user_info()

        # 校验返回数据
        assert result["id"] == 1001
        assert result["name"] == "zhangsan"

        # 校验请求参数
        assert m.last_request.method == "GET"


def test_mock_post():
    """mock POST请求 + 捕获提交的body"""
    with requests_mock.Mocker() as m:
        # 注册 POST 请求的 mock
        m.post("https://api.example.com/login", json={"token": "abc123"})

        payload = {"username": "test", "password": "123456"}
        resp = requests.post("https://api.example.com/login", json=payload)

        assert resp.json()["token"] == "abc123"
        # 获取post上传的json
        req_body = m.last_request.json()# 获取上传的json参数
        assert req_body["username"] == "test"
        assert req_body["password"] == "123456"


def test_mock_status_code():
    """mock 异常状态码 404 / 500"""
    with requests_mock.Mocker() as m:
        # 只设置状态码，无返回内容
        m.get("https://api.example.com/notfound", status_code=404)
        resp = requests.get("https://api.example.com/notfound")
        assert resp.status_code == 404


def test_mock_text_response():
    """返回文本而不是json"""
    with requests_mock.Mocker() as m:
        m.get("https://api.example.com/text", text="hello mock")
        resp = requests.get("https://api.example.com/text")
        assert resp.text == "hello mock"


def test_adapter_style():
    # 这里是 Adapter，不是 Mocker！
    adapter = requests_mock.Adapter()
    # 注册mock接口：register_uri(方法, url, ...)
    adapter.register_uri("GET", "https://demo.com/api", json={"ok": True})

    session = requests.Session()
    # 挂载到session，前缀匹配
    session.mount("https://demo.com", adapter)

    resp = session.get("https://demo.com/api")
    assert resp.json()["ok"] is True

    # 同样可以拿调用信息
    assert adapter.call_count == 1
    print(adapter.last_request.url)


if __name__ == "__main__":
    # test_basic_mock()
    # test_query_user_info()
    # test_mock_post()
    # test_mock_status_code()
    # test_mock_text_response()
    test_adapter_style()

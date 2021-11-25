from __future__ import annotations

import pathlib
import re
from base64 import b64encode
from configparser import ConfigParser
from typing import Any, Callable, TypedDict

import comfort_browser_ext
import pytest
import requests
import responses
import sentry_sdk
import sentry_sdk.utils
from comfort_browser_ext import (
    PACKAGE_NAME,
    Config,
    FrappeApi,
    FrappeException,
    _get_item_codes,
    _send_sales_order_to_server,
    get_config,
    init_sentry,
    update_token,
)


@pytest.fixture
def html() -> str:
    return "&lt;h5 class=&quot;im-page--history-new-bar im-page--history-new-bar_days _im_bar_date _im_bar_2242021 &quot; data-date=&quot;1619105444&quot;&gt;&lt;span&gt;сегодня&lt;/span&gt;&lt;/h5&gt;&lt;div class=&quot;im-mess-stack _im_mess_stack &quot; data-peer=&quot;258788324&quot; data-admin=&quot;&quot;&gt; &lt;div class=&quot;im-mess-stack--photo&quot;&gt; &lt;div class=&quot;nim-peer nim-peer_small fl_l&quot;&gt; &lt;div class=&quot;nim-peer--photo-w&quot;&gt; &lt;div class=&quot;nim-peer--photo&quot;&gt; &lt;a target=&quot;_blank&quot; class=&quot;im_grid&quot; href=&quot;/id258788324&quot;&gt;&lt;img alt=&quot;Иван&quot; src=&quot;https://sun9-52.userapi.com/s/v1/if1/bMcX5KGbAhudv1OS6vRJywK9GNxBPwMKl8yEppErOWWuD4nS2OzdmrY0bQo1MOtzOzC_jHQw.jpg?size=100x0&amp;amp;quality=96&amp;amp;crop=582,319,1340,1340&amp;amp;ava=1&quot;&gt;&lt;/a&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;div class=&quot;im-mess-stack--content&quot;&gt; &lt;div class=&quot;im-mess-stack--info&quot;&gt; &lt;div class=&quot;im-mess-stack--pname&quot;&gt; &lt;a href=&quot;/id258788324&quot; class=&quot;im-mess-stack--lnk&quot; title=&quot;&quot; target=&quot;_blank&quot;&gt;Иван&lt;/a&gt; &lt;span class=&quot;im-mess-stack--tools&quot;&gt; &lt;a href=&quot;/gim51200237?sel=258788324&amp;amp;msgid=38585&quot; class=&quot;_im_mess_link&quot;&gt;18:30&lt;/a&gt;&lt;/span&gt; &lt;/div&gt; &lt;/div&gt; &lt;ul class=&quot;ui_clean_list im-mess-stack--mess _im_stack_messages&quot;&gt; &lt;li class=&quot;im-mess _im_mess im-mess_was_edited _im_mess_38585&quot; aria-hidden=&quot;false&quot; data-ts=&quot;1619105444&quot; data-msgid=&quot;38585&quot; data-peer=&quot;258788324&quot;&gt;&lt;div class=&quot;im-mess--actions&quot;&gt; &lt;span role=&quot;link&quot; aria-label=&quot;Переслать&quot; class=&quot;im-mess--forward _im_mess_forward&quot;&gt;&lt;/span&gt; &lt;span role=&quot;link&quot; aria-label=&quot;Ответить&quot; class=&quot;im-mess--reply _im_mess_reply&quot;&gt;&lt;/span&gt; &lt;span role=&quot;link&quot; aria-label=&quot;Редактировать&quot; class=&quot;im-mess--edit _im_mess_edit&quot;&gt;&lt;/span&gt; &lt;span role=&quot;link&quot; aria-label=&quot;Важное сообщение&quot; class=&quot;im-mess--fav _im_mess_fav&quot;&gt;&lt;/span&gt; &lt;/div&gt; &lt;div class=&quot;im-mess--check fl_l&quot;&gt;&lt;/div&gt; &lt;div class=&quot;im-mess--text wall_module _im_log_body&quot;&gt;&lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fhugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-serebristyy-s99326231%2F&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-serebristyy-s99326231/&quot;&gt;https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka..&lt;/a&gt; - 2 штуки &lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fhugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-belyy-s09326198%2F&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-belyy-s09326198/&quot;&gt;https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka..&lt;/a&gt; - 2 штуки &lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fsyrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-belyy-00370713%2F-&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-belyy-00370713/-&quot;&gt;https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kol..&lt;/a&gt; 4 упаковки &lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Friktig-riktig-kryuchok-gardinnyy-30370702%2F&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/riktig-riktig-kryuchok-gardinnyy-30370702/&quot;&gt;https://www.ikea.com/ru/ru/p/riktig-riktig-kryuchok-g..&lt;/a&gt; - 4 упаковки &lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fsyrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-serebristyy-80370337%2F&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-serebristyy-80370337/&quot;&gt;https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kol..&lt;/a&gt; - 4 упаковки &lt;a href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;amp;cc_key=&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot; title=&quot;https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-goryachee-probka-20372829/-&quot;&gt;https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-g..&lt;/a&gt; 1 упаковка&lt;div class=&quot;_im_msg_media38585&quot;&gt;&lt;div class=&quot;im_msg_media im_msg_media_link&quot;&gt; &lt;div class=&quot;media_link media_link--sized media_link--photo&quot;&gt; &lt;a class=&quot;media_link__media&quot; style=&quot;padding-top: 44.692737430168%;&quot; href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;amp;el=snippet&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot;&gt; &lt;img class=&quot;media_link__photo &quot; src=&quot;https://sun9-72.userapi.com/impg/G8IP0O96dXJIPa33HRNbuN71LEMIF0w_F5A_yQ/lYJqogdZJDo.jpg?size=1074x480&amp;amp;quality=96&amp;amp;sign=089aa3bfd3d0b21ece3342e1cfa41592&amp;amp;type=share&quot; alt=&quot;ХИТ Подставка под горячее - пробка - IKEA&quot;&gt; &lt;button class=&quot;page_media_link__bookmark_button&quot; data-state=&quot;&quot; data-add=&quot;Сохранить в закладках&quot; data-remove=&quot;Удалить из закладок&quot; data-link-url=&quot;https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-goryachee-probka-20372829/-&quot; data-link-img=&quot;2000015489_457329657&quot; data-link-title=&quot;ХИТ Подставка под горячее - пробка - IKEA&quot; onmouseover=&quot;bookmarkTooltip(this)&quot; onclick=&quot;bookmarkLink(event, this, c7b28164c29e311a0e);&quot;&gt;&lt;/button&gt; &lt;/a&gt; &lt;div class=&quot;media_link__label&quot;&gt; &lt;div class=&quot;media_link__info&quot;&gt; &lt;a class=&quot;media_link__title&quot; href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;amp;el=snippet&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot;&gt;ХИТ Подставка под горячее - пробка - IKEA&lt;/a&gt; &lt;a class=&quot;media_link__subtitle&quot; href=&quot;/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;amp;el=snippet&quot; target=&quot;_blank&quot; rel=&quot;nofollow noopener&quot;&gt;www.ikea.com&lt;/a&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt;&lt;/div&gt; &lt;span class=&quot;im-mess--lbl-was-edited _im_edit_time&quot; data-time=&quot;1619105604&quot;&gt;(ред.)&lt;/span&gt;&lt;/div&gt; &lt;span tabindex=&quot;0&quot; role=&quot;link&quot; aria-label=&quot;Выделить сообщение&quot; class=&quot;blind_label im-mess--blind-select _im_mess_blind_label_select&quot;&gt;&lt;/span&gt; &lt;span class=&quot;blind_label im-mess--blind-read _im_mess_blind_unread_marker&quot;&gt;&lt;/span&gt; &lt;span class=&quot;im-mess--marker _im_mess_marker&quot;&gt;&lt;/span&gt; &lt;/li&gt; &lt;/ul&gt; &lt;/div&gt; &lt;/div&gt;&lt;div class=&quot;im-mess-stack _im_mess_stack &quot; data-peer=&quot;-51200237&quot; data-admin=&quot;57223676&quot;&gt; &lt;div class=&quot;im-mess-stack--photo&quot;&gt; &lt;div class=&quot;nim-peer nim-peer_small fl_l&quot;&gt; &lt;div class=&quot;nim-peer--photo-w&quot;&gt; &lt;div class=&quot;nim-peer--photo&quot;&gt; &lt;a target=&quot;_blank&quot; class=&quot;im_grid&quot; href=&quot;/ikeaseverodvinsk&quot;&gt;&lt;img alt=&quot;Название группы&quot; src=&quot;https://sun9-72.userapi.com/s/v1/ig1/VkrIZEb_lNls1nXNBMs849Njr1aYSubS3nHg0PRAU8eerzt_DxVQNgWBMkDSx1Kz21EzYX7t.jpg?size=100x0&amp;amp;quality=96&amp;amp;crop=0,0,2048,2048&amp;amp;ava=1&quot;&gt;&lt;/a&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;/div&gt; &lt;div class=&quot;im-mess-stack--content&quot;&gt; &lt;div class=&quot;im-mess-stack--info&quot;&gt; &lt;div class=&quot;im-mess-stack--pname&quot;&gt; &lt;a href=&quot;/ikeaseverodvinsk&quot; class=&quot;im-mess-stack--lnk&quot; title=&quot;&quot; target=&quot;_blank&quot;&gt;Название группы&lt;/a&gt;&lt;/div&gt;&lt;/div&gt;&lt;/div&gt;&lt;/div&gt;"


@pytest.fixture
def config():
    return Config(  # nosec
        url="https://example.com",
        api_key="rjtklewjt1290ij",
        api_secret="djkj2rl2jr3",
        sentry_dsn="https://public@sentry.example.com/1",
    )


empty_config = f"""[{PACKAGE_NAME}]
url =
api_key =
api_secret =
sentry_dsn =

"""


def test_get_config(tmp_path: pathlib.Path, config: Config):
    dir_path_str = tmp_path.as_posix()
    file_path = tmp_path.joinpath("config.ini")

    # Make sure can write empty config multiple time without duplicating sections
    for _ in range(3):
        with pytest.raises(RuntimeError, match="Config is incomplete"):
            get_config(dir_path_str)

        assert open(file_path).read().replace(" \n", "\n") == empty_config

    parser = ConfigParser()
    parser.read(file_path)
    parser.set(PACKAGE_NAME, "url", config.url)
    with open(file_path, "a+") as f:
        f.seek(0)
        f.truncate()
        parser.write(f)
    with pytest.raises(RuntimeError, match="Config is incomplete"):
        get_config(dir_path_str)

    parser.set(PACKAGE_NAME, "api_key", config.api_key)
    parser.set(PACKAGE_NAME, "api_secret", config.api_secret)
    parser.set(PACKAGE_NAME, "sentry_dsn", config.sentry_dsn)
    with open(file_path, "a+") as f:
        f.seek(0)
        f.truncate()
        parser.write(f)

    assert get_config(dir_path_str) == config


def test_init_sentry(monkeypatch: pytest.MonkeyPatch, config: Config):
    def mock_init(dsn: str, release: str, **kwargs: Any):
        assert dsn == config.sentry_dsn
        assert len(re.findall(PACKAGE_NAME + r"@\d+\.\d+\.\d+", release)) == 1

    monkeypatch.setattr(sentry_sdk, "init", mock_init)
    init_sentry(config)
    assert sentry_sdk.utils.MAX_STRING_LENGTH == 8192


def test_get_item_codes(html: str):
    assert not set(_get_item_codes(html)) ^ {
        "00370713",
        "09326198",
        "20372829",
        "30370702",
        "80370337",
        "99326231",
    }


def test_frappe_exception_success():
    exp_resp = "some exc"
    with pytest.raises(FrappeException, match=exp_resp):
        raise FrappeException(f'["{exp_resp}"]')


def test_frappe_exception_fails():
    exp_resp = "some exc"
    with pytest.raises(FrappeException, match=exp_resp):
        raise FrappeException(exp_resp)


def test_frappe_api_init():
    url = "https://example.com"
    api_key = "my_api_key"
    api_secret = "my_api_secret"  # nosec
    client = FrappeApi(url, api_key, api_secret)
    assert client.url == url
    assert type(client._session) == requests.Session
    assert "Authorization" in client._session.headers


@pytest.fixture
def frappe_api():
    return FrappeApi("https://example.com", "", "")


def test_frappe_api_authenticate(frappe_api: FrappeApi):
    api_key = "my_api_key"
    api_secret = "my_api_secret"  # nosec
    frappe_api._authenticate(api_key, api_secret)
    assert (
        frappe_api._session.headers["Authorization"]
        == f"Basic {b64encode(f'{api_key}:{api_secret}'.encode()).decode()}"
    )


def test_frappe_api_dump_payload_dict(frappe_api: FrappeApi):
    payload = frappe_api._dump_payload({"key": {"key": "value"}})
    assert payload == {"key": '{"key": "value"}'}


def test_frappe_api_dump_payload_list(frappe_api: FrappeApi):
    payload = frappe_api._dump_payload({"key": ["value1", "value2"]})
    assert payload == {"key": '["value1", "value2"]'}


@responses.activate
def test_frappe_api_handle_response_not_json(frappe_api: FrappeApi):
    exp_resp = "some NOT json"
    responses.add(responses.GET, "https://example.com", body=exp_resp)
    response = requests.get("https://example.com")
    with pytest.raises(ValueError, match="some NOT json"):
        frappe_api._handle_response(response)


@responses.activate
def test_frappe_api_handle_response_exc(frappe_api: FrappeApi):
    exp_resp = "some exc"
    responses.add(responses.GET, "https://example.com", json={"exc": f'["{exp_resp}"]'})
    response = requests.get("https://example.com")
    with pytest.raises(FrappeException, match=exp_resp):
        frappe_api._handle_response(response)


@responses.activate
@pytest.mark.parametrize("key", ("message", "data"))
def test_frappe_api_handle_response_message_data(frappe_api: FrappeApi, key: str):
    exp_resp = "some response"
    responses.add(responses.GET, "https://example.com", json={key: exp_resp})
    response = requests.get("https://example.com")
    assert frappe_api._handle_response(response) == exp_resp


@responses.activate
def test_frappe_api_handle_response_not_implemented(frappe_api: FrappeApi):
    responses.add(
        responses.GET, "https://example.com", json={"randomkey": "randomvalue"}
    )
    response = requests.get("https://example.com")
    with pytest.raises(NotImplementedError):
        frappe_api._handle_response(response)


@responses.activate
def test_frappe_api_post(monkeypatch: pytest.MonkeyPatch, frappe_api: FrappeApi):
    exp_resp = "some response"
    exp_payload = {"key": "value"}

    class MockFrappeApi(FrappeApi):
        def _dump_payload(self, payload: dict[str, Any]):
            assert payload == exp_payload
            return super()._dump_payload(payload)

    monkeypatch.setattr(comfort_browser_ext, "FrappeApi", MockFrappeApi)
    responses.add(responses.POST, frappe_api.url, json={"message": exp_resp})
    assert frappe_api.post(**exp_payload)


class SendSalesOrderToServerArgs(TypedDict):
    customer_name: str
    vk_url: str
    item_codes: list[str]


@pytest.fixture
def send_sales_order_to_server_args():
    return SendSalesOrderToServerArgs(
        customer_name="John Johnson",
        vk_url="https://vk.com/im?sel=1",
        item_codes=["00370713"],
    )


def test_send_sales_order_to_server(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
    send_sales_order_to_server_args: SendSalesOrderToServerArgs,
):
    mock_get_config: Callable[[str], Config] = lambda directory: config
    monkeypatch.setattr(comfort_browser_ext, "get_config", mock_get_config)

    exp_msg = f"{config.url}/sales-order/SO-2021-00001"

    def mock_post(self: FrappeApi, **data: Any):
        new_data = dict(send_sales_order_to_server_args)
        new_data["cmd"] = "comfort.integrations.browser_ext.process_sales_order"
        assert data == new_data
        return exp_msg

    monkeypatch.setattr(FrappeApi, "post", mock_post)
    assert (
        _send_sales_order_to_server(
            config,
            send_sales_order_to_server_args["customer_name"],
            send_sales_order_to_server_args["vk_url"],
            send_sales_order_to_server_args["item_codes"],
        )
        == exp_msg
    )


def test_update_token(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
):
    mock_get_config: Callable[[str], Config] = lambda directory: config
    monkeypatch.setattr(comfort_browser_ext, "get_config", mock_get_config)
    exp_token = "mytoken"  # nosec

    def mock_post(self: FrappeApi, **data: Any) -> dict[Any, Any]:  # type: ignore
        assert data["cmd"] == "comfort.integrations.browser_ext.update_token"
        assert data["token"] == exp_token
        return {}

    monkeypatch.setattr(FrappeApi, "post", mock_post)
    assert update_token(config, exp_token) == 0

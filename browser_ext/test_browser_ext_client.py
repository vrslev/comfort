from __future__ import annotations

import pathlib
import re
from configparser import ConfigParser
from typing import Any, Callable, TypedDict

import comfort_browser_ext
import pytest
import sentry_sdk
import sentry_sdk.utils
from comfort_browser_ext import (
    PACKAGE_NAME,
    Config,
    CustomFrappeClient,
    get_config,
    get_item_codes,
    init_sentry,
    parse_args,
    send_to_server,
)


@pytest.fixture
def html() -> str:
    return '<h5 class="im-page--history-new-bar im-page--history-new-bar_days _im_bar_date _im_bar_2242021 " data-date="1619105444"><span>сегодня</span></h5><div class="im-mess-stack _im_mess_stack " data-peer="258788324" data-admin=""> <div class="im-mess-stack--photo"> <div class="nim-peer nim-peer_small fl_l"> <div class="nim-peer--photo-w"> <div class="nim-peer--photo"> <a target="_blank" class="im_grid" href="/id258788324"><img alt="Иван" src="https://sun9-52.userapi.com/s/v1/if1/bMcX5KGbAhudv1OS6vRJywK9GNxBPwMKl8yEppErOWWuD4nS2OzdmrY0bQo1MOtzOzC_jHQw.jpg?size=100x0&amp;quality=96&amp;crop=582,319,1340,1340&amp;ava=1"></a> </div> </div> </div> </div> <div class="im-mess-stack--content"> <div class="im-mess-stack--info"> <div class="im-mess-stack--pname"> <a href="/id258788324" class="im-mess-stack--lnk" title="" target="_blank">Иван</a> <span class="im-mess-stack--tools"> <a href="/gim51200237?sel=258788324&amp;msgid=38585" class="_im_mess_link">18:30</a></span> </div> </div> <ul class="ui_clean_list im-mess-stack--mess _im_stack_messages"> <li class="im-mess _im_mess im-mess_was_edited _im_mess_38585" aria-hidden="false" data-ts="1619105444" data-msgid="38585" data-peer="258788324"><div class="im-mess--actions"> <span role="link" aria-label="Переслать" class="im-mess--forward _im_mess_forward"></span> <span role="link" aria-label="Ответить" class="im-mess--reply _im_mess_reply"></span> <span role="link" aria-label="Редактировать" class="im-mess--edit _im_mess_edit"></span> <span role="link" aria-label="Важное сообщение" class="im-mess--fav _im_mess_fav"></span> </div> <div class="im-mess--check fl_l"></div> <div class="im-mess--text wall_module _im_log_body"><a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fhugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-serebristyy-s99326231%2F&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-serebristyy-s99326231/">https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka..</a> - 2 штуки <a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fhugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-belyy-s09326198%2F&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka-dvoynoy-gardinnyy-karniz-kombinaciya-belyy-s09326198/">https://www.ikea.com/ru/ru/p/hugad-hugad-raecka-rekka..</a> - 2 штуки <a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fsyrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-belyy-00370713%2F-&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-belyy-00370713/-">https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kol..</a> 4 упаковки <a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Friktig-riktig-kryuchok-gardinnyy-30370702%2F&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/riktig-riktig-kryuchok-gardinnyy-30370702/">https://www.ikea.com/ru/ru/p/riktig-riktig-kryuchok-g..</a> - 4 упаковки <a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fsyrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-serebristyy-80370337%2F&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kolco-s-zazhimom-i-kryuchkom-serebristyy-80370337/">https://www.ikea.com/ru/ru/p/syrlig-sirlig-gardin-kol..</a> - 4 упаковки <a href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;cc_key=" target="_blank" rel="nofollow noopener" title="https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-goryachee-probka-20372829/-">https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-g..</a> 1 упаковка<div class="_im_msg_media38585"><div class="im_msg_media im_msg_media_link"> <div class="media_link media_link--sized media_link--photo"> <a class="media_link__media" style="padding-top: 44.692737430168%;" href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;el=snippet" target="_blank" rel="nofollow noopener"> <img class="media_link__photo " src="https://sun9-72.userapi.com/impg/G8IP0O96dXJIPa33HRNbuN71LEMIF0w_F5A_yQ/lYJqogdZJDo.jpg?size=1074x480&amp;quality=96&amp;sign=089aa3bfd3d0b21ece3342e1cfa41592&amp;type=share" alt="ХИТ Подставка под горячее - пробка - IKEA"> <button class="page_media_link__bookmark_button" data-state="" data-add="Сохранить в закладках" data-remove="Удалить из закладок" data-link-url="https://www.ikea.com/ru/ru/p/heat-hit-podstavka-pod-goryachee-probka-20372829/-" data-link-img="2000015489_457329657" data-link-title="ХИТ Подставка под горячее - пробка - IKEA" onmouseover="bookmarkTooltip(this)" onclick="bookmarkLink(event, this, c7b28164c29e311a0e);"></button> </a> <div class="media_link__label"> <div class="media_link__info"> <a class="media_link__title" href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;el=snippet" target="_blank" rel="nofollow noopener">ХИТ Подставка под горячее - пробка - IKEA</a> <a class="media_link__subtitle" href="/away.php?to=https%3A%2F%2Fwww.ikea.com%2Fru%2Fru%2Fp%2Fheat-hit-podstavka-pod-goryachee-probka-20372829%2F-&amp;el=snippet" target="_blank" rel="nofollow noopener">www.ikea.com</a> </div> </div> </div> </div></div> <span class="im-mess--lbl-was-edited _im_edit_time" data-time="1619105604">(ред.)</span></div> <span tabindex="0" role="link" aria-label="Выделить сообщение" class="blind_label im-mess--blind-select _im_mess_blind_label_select"></span> <span class="blind_label im-mess--blind-read _im_mess_blind_unread_marker"></span> <span class="im-mess--marker _im_mess_marker"></span> </li> </ul> </div> </div><div class="im-mess-stack _im_mess_stack " data-peer="-51200237" data-admin="57223676"> <div class="im-mess-stack--photo"> <div class="nim-peer nim-peer_small fl_l"> <div class="nim-peer--photo-w"> <div class="nim-peer--photo"> <a target="_blank" class="im_grid" href="/ikeaseverodvinsk"><img alt="Название группы" src="https://sun9-72.userapi.com/s/v1/ig1/VkrIZEb_lNls1nXNBMs849Njr1aYSubS3nHg0PRAU8eerzt_DxVQNgWBMkDSx1Kz21EzYX7t.jpg?size=100x0&amp;quality=96&amp;crop=0,0,2048,2048&amp;ava=1"></a> </div> </div> </div> </div> <div class="im-mess-stack--content"> <div class="im-mess-stack--info"> <div class="im-mess-stack--pname"> <a href="/ikeaseverodvinsk" class="im-mess-stack--lnk" title="" target="_blank">Название группы</a></div></div></div></div>'


@pytest.fixture
def config():
    return Config(  # nosec
        url="https://example.com",
        api_key="rjtklewjt1290ij",
        api_secret="djkj2rl2jr3",
        sentry_dsn="https://public@sentry.example.com/1",
    )


class SendToServerArgs(TypedDict):
    customer_name: str
    vk_url: str
    item_codes: list[str]


@pytest.fixture
def send_to_server_args():
    return SendToServerArgs(
        customer_name="John Johnson",
        vk_url="https://vk.com/im?sel=1",
        item_codes=["00370713"],
    )


def test_get_item_codes(html: str):
    assert not set(get_item_codes(html)) ^ {
        "00370713",
        "09326198",
        "20372829",
        "30370702",
        "80370337",
        "99326231",
    }


def test_get_config(tmp_path: pathlib.Path, config: Config):
    dir_path_str = tmp_path.as_posix()
    file_path = tmp_path.joinpath("config.ini")

    empty_config = f"""[{PACKAGE_NAME}]
url =
api_key =
api_secret =
sentry_dsn =

"""
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


def test_send_to_server(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
    send_to_server_args: SendToServerArgs,
):
    mock_get_config: Callable[[str], Config] = lambda directory: config
    monkeypatch.setattr(comfort_browser_ext, "get_config", mock_get_config)

    exp_msg = f"{config.url}/sales-order/SO-2021-00001"

    def mock_post_json(
        self: CustomFrappeClient, method: str, data: dict[str, Any] = {}  # type: ignore
    ) -> Any:
        assert method == "comfort.integrations.browser_ext.main"
        assert data == send_to_server_args
        return exp_msg

    monkeypatch.setattr(
        comfort_browser_ext.CustomFrappeClient, "post_json", mock_post_json
    )
    assert (
        send_to_server(
            config,
            send_to_server_args["customer_name"],
            send_to_server_args["vk_url"],
            send_to_server_args["item_codes"],
        )
        == exp_msg
    )


def test_init_sentry(monkeypatch: pytest.MonkeyPatch, config: Config):
    def mock_init(dsn: str, release: str, **kwargs: Any):
        assert dsn == config.sentry_dsn
        assert len(re.findall(PACKAGE_NAME + r"@\d+\.\d+\.\d+", release)) == 1

    monkeypatch.setattr(sentry_sdk, "init", mock_init)
    init_sentry(config)
    assert sentry_sdk.utils.MAX_STRING_LENGTH == 8192


def test_parse_args(html: str, send_to_server_args: SendToServerArgs):
    parsed_args = parse_args(
        [send_to_server_args["customer_name"], send_to_server_args["vk_url"], html]
    )
    assert parsed_args.customer_name == send_to_server_args["customer_name"]
    assert parsed_args.vk_url == send_to_server_args["vk_url"]
    assert parsed_args.html == html

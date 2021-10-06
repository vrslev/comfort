from __future__ import annotations

from typing import Any

import pytest
import responses
from ikea_api.errors import IkeaApiError

from comfort.integrations.kvartiroteka import Kvartiroteka


@pytest.fixture
def kvartiroteka_url():
    return "https://www.ikea.com/ru/ru/campaigns/kvartiroteka/#/p-3/three-room-83/tryohkomnatnaya-kvartira-dlya-semi/living-room/"


@pytest.fixture
def rooms() -> list[dict[str, Any]]:
    return [
        {
            "id": 1288,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 621,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1289,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 622,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1290,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 623,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1291,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 624,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1292,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 625,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1293,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 626,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
        {
            "id": 1294,
            "color": "#E3A631",
            "design_id": 204,
            "room_id": 627,
            "order": None,
            "budget": [],
            "budget_default": None,
        },
    ]


def test_kvartiroteka_init():
    api = Kvartiroteka()
    assert api._endpoint == "https://kvartiroteka.ikea.ru/data/_/items"
    assert api._token == None
    assert api._session.headers["Accept"] == "application/json, text/plain, */*"
    assert api._session.headers["Content-Type"] == "application/json;charset=utf-8"


def test_parse_design_id_passes(kvartiroteka_url: str):
    api = Kvartiroteka()
    api._parse_design_id(kvartiroteka_url)
    assert api._design_id == "tryohkomnatnaya-kvartira-dlya-semi"


@pytest.mark.parametrize(
    "url",
    (
        "https://www.ikea.com/ru/ru/campaigns/kvartiroteka/#/p-3/three-room-83",
        "https://www.ikea.com/ru/ru",
        "https://example.com",
    ),
)
def test_parse_design_id_raises(url: str):
    api = Kvartiroteka()
    with pytest.raises(IkeaApiError, match=f"Invalid Kvartiroteka url: {url}"):
        api._parse_design_id(url)


@responses.activate
def test_get_rooms(kvartiroteka_url: str, rooms: list[dict[str, Any]]):
    api = Kvartiroteka()
    api._parse_design_id(kvartiroteka_url)
    responses.add(
        method=responses.GET,
        url=f"{api._endpoint}/design_room?filter%5Bdesign_id.url%5D%5Beq%5D={api._design_id}",
        json={"data": rooms},
        match_querystring=True,
    )
    api._get_rooms()
    assert api._rooms == rooms


@responses.activate
def test_get_images(kvartiroteka_url: str, rooms: list[dict[str, Any]]):
    api = Kvartiroteka()
    api._parse_design_id(kvartiroteka_url)
    api._rooms = rooms[:1]
    responses.add(
        method=responses.GET,
        url=f"{api._endpoint}/block?fields=views.view_id.image.%2A&limit=-1&filter%5Broom_id%5D%5Beq%5D=621&filter%5Bdesign_id%5D%5Beq%5D=204",
        json={
            "data": [
                {"views": []},
                {
                    "views": [
                        {
                            "view_id": {
                                "image": {
                                    "id": 17039,
                                    "storage": "local",
                                    "filename": "Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
                                    "title": "Post 04 213 P 3 3 B1 Balcony Cam004 1080x1920 Result",
                                    "type": "image/jpeg",
                                    "uploaded_by": 38,
                                    "uploaded_on": "2021-02-28T09:25:46+00:00",
                                    "charset": "binary",
                                    "filesize": 259950,
                                    "width": 1080,
                                    "height": 1920,
                                    "duration": None,
                                    "embed": None,
                                    "folder": None,
                                    "description": "",
                                    "location": "",
                                    "tags": [],
                                    "metadata": None,
                                    "data": {
                                        "full_url": "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
                                        "url": "/uploads/_/originals/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
                                        "thumbnails": [
                                            {
                                                "url": "https://kvartiroteka.ikea.ru/data/thumbnail/_/200/200/crop/good/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
                                                "relative_url": "/thumbnail/_/200/200/crop/good/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
                                                "dimension": "200x200",
                                                "width": 200,
                                                "height": 200,
                                            }
                                        ],
                                        "embed": None,
                                    },
                                }
                            }
                        },
                        {
                            "view_id": {
                                "image": {
                                    "id": 17040,
                                    "storage": "local",
                                    "filename": "Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
                                    "title": "Post 05 213 P 3 3 B1 Balcony Cam005 1080x1920 Result",
                                    "type": "image/jpeg",
                                    "uploaded_by": 38,
                                    "uploaded_on": "2021-02-28T09:25:52+00:00",
                                    "charset": "binary",
                                    "filesize": 236205,
                                    "width": 1080,
                                    "height": 1920,
                                    "duration": None,
                                    "embed": None,
                                    "folder": None,
                                    "description": "",
                                    "location": "",
                                    "tags": [],
                                    "metadata": None,
                                    "data": {
                                        "full_url": "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
                                        "url": "/uploads/_/originals/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
                                        "thumbnails": [
                                            {
                                                "url": "https://kvartiroteka.ikea.ru/data/thumbnail/_/200/200/crop/good/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
                                                "relative_url": "/thumbnail/_/200/200/crop/good/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
                                                "dimension": "200x200",
                                                "width": 200,
                                                "height": 200,
                                            }
                                        ],
                                        "embed": None,
                                    },
                                }
                            }
                        },
                    ]
                },
                {"views": []},
                {"views": []},
                {
                    "views": [
                        {
                            "view_id": {
                                "image": {
                                    "id": 17041,
                                    "storage": "local",
                                    "filename": "Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
                                    "title": "Post 01 213 P 3 3 B1 Balcony Cam001 1920x1920 Result",
                                    "type": "image/jpeg",
                                    "uploaded_by": 38,
                                    "uploaded_on": "2021-02-28T09:25:59+00:00",
                                    "charset": "binary",
                                    "filesize": 440062,
                                    "width": 1920,
                                    "height": 1920,
                                    "duration": None,
                                    "embed": None,
                                    "folder": None,
                                    "description": "",
                                    "location": "",
                                    "tags": [],
                                    "metadata": None,
                                    "data": {
                                        "full_url": "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
                                        "url": "/uploads/_/originals/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
                                        "thumbnails": [
                                            {
                                                "url": "https://kvartiroteka.ikea.ru/data/thumbnail/_/200/200/crop/good/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
                                                "relative_url": "/thumbnail/_/200/200/crop/good/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
                                                "dimension": "200x200",
                                                "width": 200,
                                                "height": 200,
                                            }
                                        ],
                                        "embed": None,
                                    },
                                }
                            }
                        },
                        {
                            "view_id": {
                                "image": {
                                    "id": 17042,
                                    "storage": "local",
                                    "filename": "Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
                                    "title": "Post 03 213 P 3 3 B1 Balcony Cam003 1920x1920 Result",
                                    "type": "image/jpeg",
                                    "uploaded_by": 38,
                                    "uploaded_on": "2021-02-28T09:26:05+00:00",
                                    "charset": "binary",
                                    "filesize": 395020,
                                    "width": 1920,
                                    "height": 1920,
                                    "duration": None,
                                    "embed": None,
                                    "folder": None,
                                    "description": "",
                                    "location": "",
                                    "tags": [],
                                    "metadata": None,
                                    "data": {
                                        "full_url": "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
                                        "url": "/uploads/_/originals/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
                                        "thumbnails": [
                                            {
                                                "url": "https://kvartiroteka.ikea.ru/data/thumbnail/_/200/200/crop/good/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
                                                "relative_url": "/thumbnail/_/200/200/crop/good/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
                                                "dimension": "200x200",
                                                "width": 200,
                                                "height": 200,
                                            }
                                        ],
                                        "embed": None,
                                    },
                                }
                            }
                        },
                    ]
                },
                {
                    "views": [
                        {
                            "view_id": {
                                "image": {
                                    "id": 17043,
                                    "storage": "local",
                                    "filename": "Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
                                    "title": "Post 02 213 P 3 3 B1 Balcony Cam002 1920x1920 Result",
                                    "type": "image/jpeg",
                                    "uploaded_by": 38,
                                    "uploaded_on": "2021-02-28T09:26:11+00:00",
                                    "charset": "binary",
                                    "filesize": 438858,
                                    "width": 1920,
                                    "height": 1920,
                                    "duration": None,
                                    "embed": None,
                                    "folder": None,
                                    "description": "",
                                    "location": "",
                                    "tags": [],
                                    "metadata": None,
                                    "data": {
                                        "full_url": "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
                                        "url": "/uploads/_/originals/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
                                        "thumbnails": [
                                            {
                                                "url": "https://kvartiroteka.ikea.ru/data/thumbnail/_/200/200/crop/good/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
                                                "relative_url": "/thumbnail/_/200/200/crop/good/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
                                                "dimension": "200x200",
                                                "width": 200,
                                                "height": 200,
                                            }
                                        ],
                                        "embed": None,
                                    },
                                }
                            }
                        }
                    ]
                },
                {"views": []},
            ],
            "public": True,
        },
        match_querystring=True,
    )
    api._get_images()
    assert api._images == [
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
    ]

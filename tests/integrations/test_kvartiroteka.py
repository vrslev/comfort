from __future__ import annotations

from typing import Any

import pytest

from comfort.integrations.kvartiroteka import (
    parse_design_id_from_url,
    parse_images_from_blocks,
)


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


def test_parse_design_id_passes(kvartiroteka_url: str):
    v = parse_design_id_from_url(kvartiroteka_url)
    assert v == "tryohkomnatnaya-kvartira-dlya-semi"


@pytest.mark.parametrize(
    "url",
    (
        "https://www.ikea.com/ru/ru/campaigns/kvartiroteka/#/p-3/three-room-83",
        "https://www.ikea.com/ru/ru",
        "https://example.com",
    ),
)
def test_parse_design_id_raises(url: str):
    with pytest.raises(RuntimeError, match=f"Invalid Kvartiroteka url: {url}"):
        parse_design_id_from_url(url)


block_response: dict[str, Any] = {
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
}


def test_parse_images_from_blocks():
    assert list(parse_images_from_blocks(block_response)) == [
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_04_213_P-3_3_B1_Balcony_Cam004_1080x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_05_213_P-3_3_B1_Balcony_Cam005_1080x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_01_213_P-3_3_B1_Balcony_Cam001_1920x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_03_213_P-3_3_B1_Balcony_Cam003_1920x1920_result.jpg",
        "https://kvartiroteka.ikea.ru/data/uploads/_/originals/Post_02_213_P-3_3_B1_Balcony_Cam002_1920x1920_result.jpg",
    ]

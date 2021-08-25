from comfort.comfort_core.hooks.metadata import load_metadata


def test_load_metadata():
    for value in load_metadata():
        assert isinstance(value, str)

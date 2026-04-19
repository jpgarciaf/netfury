from ocr_url_json.service import _infer_isp_key_from_url


def test_infer_isp_key_from_known_host() -> None:
    assert (
        _infer_isp_key_from_url("https://www.netlife.ec/assets/banner.png")
        == "netlife"
    )


def test_infer_isp_key_from_unknown_host() -> None:
    assert (
        _infer_isp_key_from_url("https://imagenes.ejemplo.com/banner.png")
        == "imagenes"
    )

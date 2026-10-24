from services.source_image import first_source_image


def test_first_source_image_is_tied_to_source_page():
    html = '<article><img src="data:image/png;base64,no"><img src="/news/hero.webp"></article><meta property="og:image" content="https://other.example/cover.jpg">'
    assert first_source_image(html, "https://official.example/story") == "https://official.example/news/hero.webp"
    assert first_source_image('<img src="javascript:alert(1)">', "https://official.example/story") == ""

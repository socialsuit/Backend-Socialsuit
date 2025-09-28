# services/tests/test_post_customizer.py

from services.post_customizer import customize

def test_customize_post():
    content = "This is a test post."
    platform = "Twitter"
    customized = customize(content, platform)
    print("Customized Post:", customized)

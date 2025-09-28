from services.smart_schedule import smart_schedule

def test_smart_schedule_instagram_post():
    result = smart_schedule(
        platform="instagram",
        content_type="post",
        timezone="Asia/Karachi"
    )

    assert "optimal_time" in result
    assert "time_until_post" in result
    assert "metadata" in result
    assert "confidence_score" in result["metadata"]
    assert result["platform"] == "instagram"
    assert result["content_type"] == "post"
    assert isinstance(result["peak_hours_available"], list)
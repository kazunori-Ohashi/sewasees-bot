from mybot.prompt import build_prompt

def test_build_prompt():
    txt = "サンプルテキスト"
    prompt = build_prompt(txt)
    assert "{{POINT}}" in prompt
    assert "{{REASON}}" in prompt
    assert "{{EXAMPLE}}" in prompt 
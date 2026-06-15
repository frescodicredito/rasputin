"""Entrypoint smoke tests.

These exercise a *real import* of the server module (running the @mcp.tool
decorators), which catches import-time errors that a bare `py_compile` would
miss. The CI runs the same import across the OS/Python matrix.
"""

import asyncio


def test_server_module_imports():
    import rasputin.server as srv

    assert srv.mcp is not None
    assert srv.mcp.name == "rasputin"


def test_server_registers_all_tools():
    import rasputin.server as srv

    tools = asyncio.run(srv.mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "rasputin_ask",
        "rasputin_council",
        "rasputin_followup",
        "rasputin_sessions",
    }


def test_reject_forbidden_blocks_claude_models():
    from rasputin.server import _reject_forbidden

    assert _reject_forbidden(["anthropic/claude-opus-4"]) is not None
    assert _reject_forbidden(["gemini/gemini-flash-latest", "claude-3-5-sonnet"]) is not None
    assert _reject_forbidden(["gemini/gemini-flash-latest", "openai/gpt-5"]) is None


def test_build_message_wraps_untrusted_document():
    from rasputin.server import _build_message

    out = _build_message("review this", context=None, file_content="secret doc text")
    assert "<UNTRUSTED_DOCUMENT>" in out
    assert "</UNTRUSTED_DOCUMENT>" in out
    assert "secret doc text" in out


def test_rasputin_ask_sanitizes_single_model_error(monkeypatch):
    import rasputin.server as srv
    from rasputin.sessions import SessionManager

    class FakeCtx:
        lifespan_context = {
            "config": {
                "defaults": {
                    "temperature": 0.7,
                    "timeout_per_model": 30,
                    "max_output_tokens": 4096,
                    "max_file_chars": 1000,
                }
            },
            "sessions": SessionManager(ttl_minutes=60),
        }

    async def boom(**kwargs):
        # A raw exception carrying sensitive-looking detail.
        raise Exception("connect to https://api.openai.com failed token=sk-secret123 reqid=abc")

    monkeypatch.setattr(srv, "query_model", boom)

    result = asyncio.run(
        srv.rasputin_ask(message="hi", model="openai/gpt-5-mini", ctx=FakeCtx())
    )
    assert "error" in result
    assert "openai/gpt-5-mini" in result["error"]
    # raw detail must not leak through
    assert "sk-secret123" not in result["error"]
    assert "api.openai.com" not in result["error"]

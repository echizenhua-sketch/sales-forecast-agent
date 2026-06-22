"""
AI服务测试
"""

import pytest
from app.services.ai_service import AIService


class TestAIService:
    """AI服务测试"""

    @pytest.fixture
    def service(self, monkeypatch):
        """创建服务实例"""
        monkeypatch.setenv("AI_API_BASE", "http://model.local")
        monkeypatch.setenv("AI_API_KEY", "test-key")

        def fake_model_call(self, session_id, user_message, system_prompt, context):
            return self._generate_fallback_response(user_message, context)

        monkeypatch.setattr(AIService, "_call_minimax_api", fake_model_call)
        return AIService()

    @pytest.fixture
    def sample_context(self):
        """示例上下文"""
        return {
            "task_summary": {
                "total_supply": 1240500,
                "total_sar": 1180200,
                "total_gap": 60300,
                "service_level": 95.5,
                "target_service_level": 98.0,
                "critical_risk_count": 5,
                "high_risk_count": 12,
                "medium_risk_count": 8,
            }
        }

    def test_chat_basic(self, service):
        """测试基本对话"""
        response = service.chat("test_session", "你好")

        assert response["success"] is True
        assert "message" in response
        assert len(response["message"]) > 0
        print("PASS: 基本对话测试通过")

    def test_chat_with_context(self, service, sample_context):
        """测试带上下文的对话"""
        response = service.chat("test_session_2", "有哪些风险？", sample_context)

        assert response["success"] is True
        assert "message" in response
        assert "风险" in response["message"]
        print("PASS: 带上下文对话测试通过")

    def test_chat_risk_analysis(self, service, sample_context):
        """测试风险分析"""
        response = service.chat("test_session_3", "分析一下风险情况", sample_context)

        assert response["success"] is True
        assert "5" in response["message"] or "极高风险" in response["message"]
        print("PASS: 风险分析测试通过")

    def test_chat_gap_analysis(self, service, sample_context):
        """测试缺口分析"""
        response = service.chat("test_session_4", "缺口多少？", sample_context)

        assert response["success"] is True
        # 接受带逗号的数字格式
        assert "60" in response["message"] and "300" in response["message"]
        print("PASS: 缺口分析测试通过")

    def test_chat_service_level(self, service, sample_context):
        """测试满足率分析"""
        response = service.chat("test_session_5", "满足率如何？", sample_context)

        assert response["success"] is True
        assert "95.5" in response["message"] or "满足率" in response["message"]
        print("PASS: 满足率分析测试通过")

    def test_chat_suggestions(self, service, sample_context):
        """测试优化建议"""
        response = service.chat("test_session_6", "给我一些优化建议", sample_context)

        assert response["success"] is True
        assert "建议" in response["message"]
        print("PASS: 优化建议测试通过")

    def test_conversation_history(self, service):
        """测试会话历史"""
        session_id = "test_session_history"

        # 发送多条消息
        service.chat(session_id, "第一条消息")
        service.chat(session_id, "第二条消息")

        # 获取历史
        history = service.get_conversation_history(session_id)

        assert len(history) >= 4  # 2条用户消息 + 2条AI回复
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"
        print("PASS: 会话历史测试通过")

    def test_clear_conversation(self, service):
        """测试清除会话"""
        session_id = "test_session_clear"

        # 发送消息
        service.chat(session_id, "测试消息")

        # 清除会话
        service.clear_conversation(session_id)

        # 验证已清除
        history = service.get_conversation_history(session_id)
        assert len(history) == 0
        print("PASS: 清除会话测试通过")

    def test_help_message(self, service):
        """测试帮助信息"""
        response = service.chat("test_session_help", "怎么用？")

        assert response["success"] is True
        assert "帮" in response["message"] or "使用" in response["message"]
        print("PASS: 帮助信息测试通过")

    def test_chat_calls_configured_model(self, monkeypatch, sample_context):
        """配置模型后必须真实调用模型接口"""
        captured = {}

        monkeypatch.setenv("AI_API_BASE", "http://model.local")
        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.setenv("AI_MODEL", "test-model")

        def fake_post(url, headers, json, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            captured["timeout"] = timeout

            class FakeResponse:
                status_code = 200
                text = '{"content":[{"text":"模型真实回复"}]}'

                def json(self):
                    return {"content": [{"text": "模型真实回复"}]}

            return FakeResponse()

        monkeypatch.setattr("app.services.ai_service.requests.post", fake_post)

        service = AIService()
        response = service.chat("model_session", "分析一下风险", sample_context)

        assert response["success"] is True
        assert response["message"] == "模型真实回复"
        assert response["type"] == "llm_generate"
        assert response["model"] == "test-model"
        assert captured["url"] == "http://model.local/v1/messages"
        assert captured["headers"]["Authorization"] == "Bearer test-key"
        assert captured["json"]["model"] == "test-model"

    def test_chat_extracts_text_after_thinking_block(self, monkeypatch, sample_context):
        """兼容 minimax-m3 先返回 thinking 块再返回 text 块的结构"""
        monkeypatch.setenv("AI_API_BASE", "http://model.local")
        monkeypatch.setenv("AI_API_KEY", "test-key")
        monkeypatch.setenv("AI_MODEL", "minimax-m3")

        def fake_post(url, headers, json, timeout):
            class FakeResponse:
                status_code = 200
                text = '{"content":[{"type":"thinking","thinking":"内部推理"},{"type":"text","text":"这是最终回答"}]}'

                def json(self):
                    return {
                        "content": [
                            {"type": "thinking", "thinking": "内部推理"},
                            {"type": "text", "text": "这是最终回答"},
                        ]
                    }

            return FakeResponse()

        monkeypatch.setattr("app.services.ai_service.requests.post", fake_post)

        service = AIService()
        response = service.chat("thinking_session", "你好", sample_context)

        assert response["success"] is True
        assert response["message"] == "这是最终回答"
        assert response["type"] == "llm_generate"

    def test_chat_extracts_openai_choices_content(self, monkeypatch, sample_context):
        """兼容 OpenAI Chat Completions 风格响应"""
        monkeypatch.setenv("AI_API_BASE", "http://model.local")
        monkeypatch.setenv("AI_API_KEY", "test-key")

        def fake_post(url, headers, json, timeout):
            class FakeResponse:
                status_code = 200
                text = '{"choices":[{"message":{"content":"OpenAI格式回答"}}]}'

                def json(self):
                    return {
                        "choices": [
                            {"message": {"role": "assistant", "content": "OpenAI格式回答"}}
                        ]
                    }

            return FakeResponse()

        monkeypatch.setattr("app.services.ai_service.requests.post", fake_post)

        service = AIService()
        response = service.chat("choices_session", "你好", sample_context)

        assert response["success"] is True
        assert response["message"] == "OpenAI格式回答"
        assert response["type"] == "llm_generate"

    def test_chat_without_model_config_does_not_fake_success(self, monkeypatch):
        """未配置模型时不能用预设回答伪装成模型回复"""
        from app.core.config import get_settings

        monkeypatch.delenv("AI_API_BASE", raising=False)
        monkeypatch.delenv("AI_API_KEY", raising=False)
        monkeypatch.delenv("AI_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        monkeypatch.setenv("AI_API_BASE", "")
        monkeypatch.setenv("AI_API_KEY", "")
        monkeypatch.setenv("AI_MODEL", "")
        monkeypatch.setattr(
            "app.services.ai_service.get_settings",
            lambda: get_settings().__class__(
                ai_api_base="",
                ai_api_key="",
                ai_model="MiniMax-M3",
                anthropic_base_url="",
                anthropic_auth_token="",
            ),
        )

        service = AIService()
        response = service.chat("missing_config_session", "你好")

        assert response["success"] is False
        assert response["type"] == "llm_unconfigured"
        assert "未配置" in response["message"]

    def test_chat_model_error_does_not_fallback_to_rule_answer(self, monkeypatch):
        """模型调用失败时不能静默降级为规则回答"""
        monkeypatch.setenv("AI_API_BASE", "http://model.local")
        monkeypatch.setenv("AI_API_KEY", "test-key")

        def fake_post(url, headers, json, timeout):
            class FakeResponse:
                status_code = 500
                text = "upstream error"

                def json(self):
                    return {"error": "upstream error"}

            return FakeResponse()

        monkeypatch.setattr("app.services.ai_service.requests.post", fake_post)

        service = AIService()
        response = service.chat("model_error_session", "你好")

        assert response["success"] is False
        assert response["type"] == "llm_error"
        assert "模型调用失败" in response["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

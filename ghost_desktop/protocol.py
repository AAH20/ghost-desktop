"""
Standardized Computer-Use Protocol Adapters (Anthropic, OpenAI Operator, JSON-RPC 2.0).
Provides native compliance with modern multimodal agent tool calling specs.
"""

from typing import Dict, List, Optional, Tuple, Any
from .models import ComputerAction, ActionType, ActionResult
from .display import VirtualDisplay


class ProtocolAdapter:
    """Translates model-agnostic computer-use commands and builds tool schemas."""

    @staticmethod
    def get_anthropic_tool_schema(width: int = 1280, height: int = 800, display_number: int = 1) -> Dict[str, Any]:
        """Anthropic Computer Use (computer_20241022) tool definition."""
        return {
            "name": "computer",
            "type": "computer_20241022",
            "display_width_px": width,
            "display_height_px": height,
            "display_number": display_number,
        }

    @staticmethod
    def parse_anthropic_call(input_dict: Dict[str, Any]) -> ComputerAction:
        """Parse Anthropic computer-use tool invocation into ComputerAction."""
        raw_action = input_dict.get("action", "screenshot")
        coord = input_dict.get("coordinate")
        text = input_dict.get("text")

        # Map string to ActionType
        try:
            act_type = ActionType(raw_action)
        except ValueError:
            act_type = ActionType.SCREENSHOT

        coordinate = tuple(coord) if coord and len(coord) == 2 else None

        return ComputerAction(
            action=act_type,
            coordinate=coordinate,
            text=text,
            key=input_dict.get("key") or text
        )

    @staticmethod
    def format_anthropic_response(result: ActionResult) -> Dict[str, Any]:
        """Format ActionResult to Anthropic tool_result block."""
        if result.action == "screenshot" and result.screenshot_base64:
            return {
                "type": "tool_result",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": result.screenshot_base64
                        }
                    }
                ]
            }
        else:
            status_text = result.output or (result.error if not result.success else "Action completed successfully")
            return {
                "type": "tool_result",
                "content": [
                    {
                        "type": "text",
                        "text": status_text
                    }
                ],
                "is_error": not result.success
            }

    @staticmethod
    def handle_jsonrpc(request: Dict[str, Any], display: VirtualDisplay) -> Dict[str, Any]:
        """Process JSON-RPC 2.0 computer use request."""
        req_id = request.get("id", 1)
        method = request.get("method")
        params = request.get("params", {})

        if method == "computer.action":
            action = ProtocolAdapter.parse_anthropic_call(params)
            res = display.execute_action(action)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "success": res.success,
                    "action": res.action,
                    "output": res.output,
                    "error": res.error,
                    "has_screenshot": bool(res.screenshot_base64),
                    "cursor": res.cursor_position,
                    "execution_time_ms": res.execution_time_ms
                }
            }
        elif method == "computer.screenshot":
            b64 = display.capture_base64()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "format": "png",
                    "width": display.config.width,
                    "height": display.config.height,
                    "image_base64": b64
                }
            }
        elif method == "computer.get_cursor":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "x": display.cursor_pos[0],
                    "y": display.cursor_pos[1]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method '{method}' not found"
                }
            }

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import jsonschema
import yaml

from .base_tool import BaseTool

logger = logging.getLogger("chat_bukkigo.core.registry")


class ToolRegistry:
    """Registry tự động khám phá, nạp và điều phối thực thi các Tool."""

    def __init__(self, tools_dir: Optional[Union[str, Path]] = None):
        if tools_dir:
            self.tools_dir = Path(tools_dir)
        else:
            self.tools_dir = Path(__file__).resolve().parent.parent.parent.parent / "tools"
        self._tools: Dict[str, BaseTool] = {}

    def discover_and_register(self) -> None:
        """Quét thư mục tools/ để tìm và đăng ký các tool hợp lệ."""
        if not self.tools_dir.exists():
            logger.warning("Thư mục tools '%s' không tồn tại.", self.tools_dir)
            return

        for item in self.tools_dir.iterdir():
            if not item.is_dir():
                continue

            yaml_path = item / "tool.yaml"
            py_path = item / "tool.py"

            if not (yaml_path.exists() and py_path.exists()):
                continue

            try:
                self._load_tool(item.name, yaml_path, py_path)
            except Exception as e:
                logger.error("Không thể tải tool từ '%s': %s", item.name, e, exc_info=True)

    def _load_tool(self, dir_name: str, yaml_path: Path, py_path: Path) -> None:
        with open(yaml_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        tool_name = config.get("name")
        if not tool_name:
            raise ValueError(f"Thiếu trường 'name' trong {yaml_path}")

        # Nạp động module python
        spec = importlib.util.spec_from_file_location(f"tools.{dir_name}.tool", py_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Không thể tạo spec cho {py_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Tìm class kế thừa BaseTool
        tool_cls = None
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseTool) and obj is not BaseTool:
                tool_cls = obj
                break

        if tool_cls is None:
            raise TypeError(f"Không tìm thấy class kế thừa BaseTool trong {py_path}")

        tool_instance = tool_cls(config)
        self._tools[tool_name] = tool_instance
        logger.info("Đã đăng ký tool: '%s' từ %s", tool_name, dir_name)

    def register_tool(self, tool: BaseTool) -> None:
        """Đăng ký thủ công một instance tool."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def has_tools(self) -> bool:
        return len(self._tools) > 0

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả schemas của các tool đã đăng ký cho OpenAI Function Calling."""
        return [tool.get_tool_schema() for tool in self._tools.values()]

    def validate_arguments(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Validate arguments gửi từ LLM theo JSON schema của tool."""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Lỗi: Không tìm thấy tool '{tool_name}'."

        schema = tool.parameters
        try:
            jsonschema.validate(instance=arguments, schema=schema)
            return None
        except jsonschema.ValidationError as err:
            return f"Schema Validation Error: {err.message}"

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Thực thi tool với arguments, có timeout và bắt lỗi an toàn."""
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' không tồn tại."

        # Kiểm tra validation
        val_err = self.validate_arguments(tool_name, arguments)
        if val_err:
            return f"Error: {val_err}"

        try:
            result = await asyncio.wait_for(tool.execute(**arguments), timeout=tool.timeout)
            if isinstance(result, (dict, list)):
                import json
                return json.dumps(result, ensure_ascii=False)
            return str(result)
        except asyncio.TimeoutError:
            logger.error("Tool '%s' chạy quá thời gian chờ (%.1fs).", tool_name, tool.timeout)
            return f"Error: Tool '{tool_name}' đã hết thời gian chờ ({tool.timeout}s)."
        except Exception as e:
            logger.exception("Lỗi khi thực thi tool '%s'", tool_name)
            return f"Error: Lỗi khi chạy tool '{tool_name}': {e}"

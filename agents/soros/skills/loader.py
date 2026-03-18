# -*- coding: utf-8 -*-
"""
Skills Loader - 技能动态加载器
==============================
借鉴 OPENCLAW 框架，每个 Skill 包含：
- instruction.md: 技能描述和行为规范
- functions.py: 可调用的工具函数

Loader 负责动态加载和管理所有 Skills
"""

import json
import importlib.util
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable


class Skill:
    """单个技能"""
    
    def __init__(self, skill_dir: Path):
        self.dir = skill_dir
        self.id = skill_dir.name
        self.name = self._load_name()
        self.instruction = self._load_instruction()
        self.functions = self._load_functions()
        self.tools = self._get_tool_names()
    
    def _load_name(self) -> str:
        """加载技能名称"""
        meta_file = self.dir / "meta.json"
        if meta_file.exists():
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("name", self.id)
        return self.id
    
    def _load_instruction(self) -> str:
        """加载技能指令"""
        inst_file = self.dir / "instruction.md"
        if inst_file.exists():
            with open(inst_file, encoding="utf-8") as f:
                return f.read()
        return ""
    
    def _load_functions(self) -> Dict[str, Callable]:
        """加载可执行函数"""
        functions = {}
        func_file = self.dir / "functions.py"
        
        if func_file.exists():
            # 动态导入模块
            spec = importlib.util.spec_from_file_location("skill_functions", func_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 获取以 _func_ 开头的函数
            for name in dir(module):
                if name.startswith("_func_"):
                    functions[name[6:]] = getattr(module, name)
        
        return functions
    
    def _get_tool_names(self) -> List[str]:
        """获取技能关联的工具名称"""
        meta_file = self.dir / "meta.json"
        if meta_file.exists():
            with open(meta_file, encoding="utf-8") as f:
                meta = json.load(f)
                return meta.get("tools", [])
        return []
    
    def execute(self, func_name: str, **kwargs) -> Any:
        """执行技能函数"""
        func = self.functions.get(func_name)
        if func:
            return func(**kwargs)
        return {"error": f"Unknown function: {func_name}"}
    
    def get_instruction_for_llm(self) -> str:
        """获取用于 LLM 的格式化指令"""
        return f"## 技能: {self.name}\n\n{self.instruction}"


class SkillLoader:
    """技能加载器 - 管理所有 Skills"""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, Skill] = {}
        self._load_all()
    
    def _load_all(self):
        """加载所有技能"""
        if not self.skills_dir.exists():
            return
        
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                try:
                    skill = Skill(item)
                    self.skills[skill.id] = skill
                except Exception as e:
                    print(f"Failed to load skill {item.name}: {e}")
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def get_all_instructions(self) -> str:
        """获取所有技能的合并指令"""
        parts = ["# 可用技能"]
        for skill_id, skill in self.skills.items():
            parts.append(f"\n{skill.get_instruction_for_llm()}")
        return "\n".join(parts)
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """获取所有技能函数"""
        tools = {}
        for skill in self.skills.values():
            for func_name, func in skill.functions.items():
                tools[f"{skill.id}.{func_name}"] = func
        return tools
    
    def list_skills(self) -> List[Dict]:
        """列出所有技能"""
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "tools": skill.tools,
                "has_functions": len(skill.functions) > 0
            }
            for skill in self.skills.values()
        ]


# 全局实例
_loader: Optional[SkillLoader] = None


def get_skill_loader(skills_dir: Path = None) -> SkillLoader:
    """获取技能加载器实例"""
    global _loader
    if _loader is None:
        if skills_dir is None:
            skills_dir = Path(__file__).parent / "skills"
        _loader = SkillLoader(skills_dir)
    return _loader


def reload_skills():
    """重新加载所有技能"""
    global _loader
    _loader = None
    return get_skill_loader()

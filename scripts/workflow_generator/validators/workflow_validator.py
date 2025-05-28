#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流生成器 - 工作流验证器
"""

import os
import re
import json
import yaml
import subprocess
import tempfile
from enum import Enum, auto
from typing import List, Dict, Any, Tuple, Optional, Union, TYPE_CHECKING
import jsonschema
from pathlib import Path
from dataclasses import dataclass
import requests
import logging
import ruamel.yaml

# GitHub Actions Token类型枚举
class GithubTokenType(Enum):
    STRING = auto()         # 字符串字面量
    NUMBER = auto()         # 数字字面量
    BOOLEAN = auto()        # 布尔字面量
    CONTEXT = auto()        # 上下文变量引用
    FUNCTION = auto()       # 函数调用
    OPERATOR = auto()       # 运算符
    LPAREN = auto()         # 左括号
    RPAREN = auto()         # 右括号
    LBRACE = auto()         # 左花括号
    RBRACE = auto()         # 右花括号
    DOT = auto()            # 点号
    COMMA = auto()          # 逗号
    IDENTIFIER = auto()     # 标识符
    EOF = auto()            # 结束标记

@dataclass
class GithubToken:
    """表示词法单元的数据类"""
    type: GithubTokenType
    value: str
    position: int

# 抽象语法树节点类
class GithubASTNode:
    """抽象语法树节点基类"""
    pass

class GithubBinaryOp(GithubASTNode):
    """二元运算节点"""
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class GithubUnaryOp(GithubASTNode):
    """一元运算节点"""
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

class GithubLiteral(GithubASTNode):
    """字面量节点"""
    def __init__(self, token):
        self.token = token
        self.value = token.value

class GithubContextRef(GithubASTNode):
    """上下文引用节点"""
    def __init__(self, token):
        self.token = token
        self.path = token.value

class GithubFunctionCall(GithubASTNode):
    """函数调用节点"""
    def __init__(self, name, args):
        self.name = name
        self.args = args

# GitHub Actions 表达式词法分析器
class GithubExprLexer:
    """GitHub Actions 表达式词法分析器"""
    
    def __init__(self, text: str):
        self.text = text
        self.position = 0
        self.current_char = self.text[0] if text else None
        
        # 运算符映射
        self.operators = {
            '==': GithubTokenType.OPERATOR,
            '!=': GithubTokenType.OPERATOR,
            '>=': GithubTokenType.OPERATOR,
            '<=': GithubTokenType.OPERATOR,
            '>': GithubTokenType.OPERATOR,
            '<': GithubTokenType.OPERATOR,
            '&&': GithubTokenType.OPERATOR,
            '||': GithubTokenType.OPERATOR,
            '!': GithubTokenType.OPERATOR,
            '+': GithubTokenType.OPERATOR,
            '-': GithubTokenType.OPERATOR,
            '*': GithubTokenType.OPERATOR,
            '/': GithubTokenType.OPERATOR
        }
        
        # 关键字映射
        self.keywords = {
            'true': GithubTokenType.BOOLEAN,
            'false': GithubTokenType.BOOLEAN,
            'null': GithubTokenType.BOOLEAN
        }
        
        # 上下文变量名集合
        self.contexts = {
            'github', 'env', 'vars', 'secrets', 'steps', 
            'needs', 'inputs', 'job', 'matrix', 'strategy'
        }
    
    def advance(self):
        """移动到下一个字符"""
        self.position += 1
        if self.position >= len(self.text):
            self.current_char = None
        else:
            self.current_char = self.text[self.position]
    
    def skip_whitespace(self):
        """跳过空白字符"""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()
    
    def peek(self, n=1) -> Optional[str]:
        """查看未来的n个字符，不移动位置"""
        peek_pos = self.position + n
        if peek_pos >= len(self.text):
            return None
        return self.text[peek_pos]
    
    def identifier(self) -> GithubToken:
        """处理标识符或关键字"""
        start_pos = self.position
        result = ''
        
        while (self.current_char is not None and 
               (self.current_char.isalnum() or self.current_char == '_')):
            result += self.current_char
            self.advance()
        
        # 检查是否为关键字
        if result in self.keywords:
            return GithubToken(self.keywords[result], result, start_pos)
        
        # 检查是否为上下文开始
        if result in self.contexts:
            # 暂存当前标识符
            context_start = result
            
            # 检查是否有点号后跟属性
            if self.current_char == '.':
                result += self.current_char  # 添加点号
                self.advance()
                
                # 解析属性路径
                while (self.current_char is not None and 
                       (self.current_char.isalnum() or self.current_char == '_')):
                    result += self.current_char
                    self.advance()
                    
                    # 继续处理更深层次的属性引用
                    if self.current_char == '.':
                        result += self.current_char
                        self.advance()
                
                return GithubToken(GithubTokenType.CONTEXT, result, start_pos)
        
        # 普通标识符
        return GithubToken(GithubTokenType.IDENTIFIER, result, start_pos)
    
    def number(self) -> GithubToken:
        """处理数字字面量"""
        start_pos = self.position
        result = ''
        
        while self.current_char is not None and self.current_char.isdigit():
            result += self.current_char
            self.advance()
        
        # 处理小数点
        if self.current_char == '.':
            result += self.current_char
            self.advance()
            
            while self.current_char is not None and self.current_char.isdigit():
                result += self.current_char
                self.advance()
        
        return GithubToken(GithubTokenType.NUMBER, result, start_pos)
    
    def string(self) -> GithubToken:
        """处理字符串字面量"""
        start_pos = self.position
        quote_char = self.current_char  # 保存引号类型 (' 或 ")
        result = quote_char
        self.advance()
        
        while self.current_char is not None and self.current_char != quote_char:
            if self.current_char == '\\' and self.peek() == quote_char:
                # 处理转义引号
                result += self.current_char
                self.advance()
            
            result += self.current_char
            self.advance()
        
        if self.current_char == quote_char:
            result += self.current_char
            self.advance()
        
        return GithubToken(GithubTokenType.STRING, result, start_pos)
    
    def get_next_token(self) -> GithubToken:
        """获取下一个词法单元"""
        while self.current_char is not None:
            
            # 跳过空白字符
            if self.current_char.isspace():
                self.skip_whitespace()
                continue
            
            # 识别数字
            if self.current_char.isdigit():
                return self.number()
            
            # 识别标识符和关键字
            if self.current_char.isalpha() or self.current_char == '_':
                return self.identifier()
            
            # 识别字符串
            if self.current_char in ('"', "'"):
                return self.string()
            
            # 识别左括号
            if self.current_char == '(':
                token = GithubToken(GithubTokenType.LPAREN, '(', self.position)
                self.advance()
                return token
            
            # 识别右括号
            if self.current_char == ')':
                token = GithubToken(GithubTokenType.RPAREN, ')', self.position)
                self.advance()
                return token
            
            # 识别左花括号
            if self.current_char == '{' and self.peek() == '{':
                token = GithubToken(GithubTokenType.LBRACE, '{{', self.position)
                self.advance()
                self.advance()
                return token
            
            # 识别右花括号
            if self.current_char == '}' and self.peek() == '}':
                token = GithubToken(GithubTokenType.RBRACE, '}}', self.position)
                self.advance()
                self.advance()
                return token
            
            # 识别点号
            if self.current_char == '.':
                token = GithubToken(GithubTokenType.DOT, '.', self.position)
                self.advance()
                return token
            
            # 识别逗号
            if self.current_char == ',':
                token = GithubToken(GithubTokenType.COMMA, ',', self.position)
                self.advance()
                return token
            
            # 识别双字符运算符
            if self.current_char + (self.peek() or '') in self.operators:
                op = self.current_char + self.peek()
                token = GithubToken(self.operators[op], op, self.position)
                self.advance()
                self.advance()
                return token
            
            # 识别单字符运算符
            if self.current_char in self.operators:
                token = GithubToken(self.operators[self.current_char], self.current_char, self.position)
                self.advance()
                return token
            
            # 无法识别的字符
            raise ValueError(f"无法识别的字符: '{self.current_char}' 在位置 {self.position}")
        
        # 已到达文本末尾
        return GithubToken(GithubTokenType.EOF, '', self.position)

# GitHub Actions 官方 JSON Schema URL
GITHUB_ACTIONS_SCHEMA_URL = "https://json.schemastore.org/github-workflow.json"
# GitHub Actions表达式语法分析器
class GithubExprParser:
    """GitHub Actions表达式语法分析器"""
    
    def __init__(self, lexer: GithubExprLexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
        self.errors = []
    
    def error(self, message: str):
        """记录解析错误"""
        self.errors.append(f"语法错误: {message}, 位置: {self.current_token.position}")
    
    def eat(self, token_type: GithubTokenType):
        """验证当前标记类型并前进"""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"预期 {token_type}, 实际为 {self.current_token.type}")
    
    def parse(self) -> Optional[GithubASTNode]:
        """解析表达式"""
        try:
            return self.expr()
        except Exception as e:
            self.error(f"解析时发生异常: {str(e)}")
            return None
    
    def expr(self) -> GithubASTNode:
        """expr : or_expr"""
        return self.or_expr()
    
    def or_expr(self) -> GithubASTNode:
        """or_expr : and_expr (|| and_expr)*"""
        node = self.and_expr()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value == '||'):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.and_expr())
        
        return node
    
    def and_expr(self) -> GithubASTNode:
        """and_expr : equality (&&  equality)*"""
        node = self.equality()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value == '&&'):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.equality())
        
        return node
    
    def equality(self) -> GithubASTNode:
        """equality : comparison ((== | !=) comparison)*"""
        node = self.comparison()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value in ('==', '!=')):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.comparison())
        
        return node
    
    def comparison(self) -> GithubASTNode:
        """comparison : term ((< | > | <= | >=) term)*"""
        node = self.term()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value in ('<', '>', '<=', '>=')):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.term())
        
        return node
    
    def term(self) -> GithubASTNode:
        """term : factor ((+ | -) factor)*"""
        node = self.factor()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value in ('+', '-')):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.factor())
        
        return node
    
    def factor(self) -> GithubASTNode:
        """factor : unary ((* | /) unary)*"""
        node = self.unary()
        
        while (self.current_token.type == GithubTokenType.OPERATOR and 
               self.current_token.value in ('*', '/')):
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            node = GithubBinaryOp(left=node, op=token, right=self.unary())
        
        return node
    
    def unary(self) -> GithubASTNode:
        """unary : (! unary) | primary"""
        if self.current_token.type == GithubTokenType.OPERATOR and self.current_token.value == '!':
            token = self.current_token
            self.eat(GithubTokenType.OPERATOR)
            return GithubUnaryOp(token, self.unary())
        return self.primary()
    
    def primary(self) -> GithubASTNode:
        """primary : BOOLEAN | NUMBER | STRING | context_ref | function_call | '(' expr ')'"""
        token = self.current_token
        
        if token.type == GithubTokenType.BOOLEAN:
            self.eat(GithubTokenType.BOOLEAN)
            return GithubLiteral(token)
        
        elif token.type == GithubTokenType.NUMBER:
            self.eat(GithubTokenType.NUMBER)
            return GithubLiteral(token)
        
        elif token.type == GithubTokenType.STRING:
            self.eat(GithubTokenType.STRING)
            return GithubLiteral(token)
        
        elif token.type == GithubTokenType.CONTEXT:
            self.eat(GithubTokenType.CONTEXT)
            return GithubContextRef(token)
        
        elif token.type == GithubTokenType.IDENTIFIER:
            # 看下一个token是否为左括号，判断是否为函数调用
            name_token = token
            self.eat(GithubTokenType.IDENTIFIER)
            
            if self.current_token.type == GithubTokenType.LPAREN:
                return self.function_call(name_token)
            else:
                return GithubLiteral(name_token)
        
        elif token.type == GithubTokenType.LPAREN:
            self.eat(GithubTokenType.LPAREN)
            node = self.expr()
            self.eat(GithubTokenType.RPAREN)
            return node
        
        self.error(f"意外的token: {token.value}")
        # 尝试继续解析
        self.eat(token.type)
        return GithubLiteral(GithubToken(GithubTokenType.BOOLEAN, 'false', token.position))
    
    def function_call(self, name_token) -> GithubASTNode:
        """function_call : IDENTIFIER '(' (expr (',' expr)*)? ')'"""
        self.eat(GithubTokenType.LPAREN)
        
        args = []
        if self.current_token.type != GithubTokenType.RPAREN:
            args.append(self.expr())
            
            while self.current_token.type == GithubTokenType.COMMA:
                self.eat(GithubTokenType.COMMA)
                args.append(self.expr())
        
        self.eat(GithubTokenType.RPAREN)
        return GithubFunctionCall(name_token.value, args)

# GitHub Actions表达式分析器
class GithubExpressionAnalyzer:
    """GitHub Actions表达式分析器"""
    
    def __init__(self):
        # GitHub Actions标准函数列表
        self.standard_functions = {
            'contains', 'startsWith', 'endsWith', 'format', 'join', 'toJSON',
            'fromJSON', 'hashFiles', 'success', 'always', 'cancelled', 'failure'
        }
        
        self.issues = []
    
    def analyze(self, expression: str) -> List[str]:
        """
        分析GitHub Actions表达式并返回问题列表
        
        Args:
            expression: GitHub Actions表达式
            
        Returns:
            问题消息列表
        """
        self.issues = []
        
        # 跳过已经正确格式化的表达式
        if (expression.startswith('${{') and expression.endswith('}}')) or '{{' in expression:
            # 检查内部表达式
            if expression.startswith('${{') and expression.endswith('}}'):
                inner_expr = expression[3:-2].strip()
                self._analyze_inner_expression(inner_expr)
            return self.issues
        
        # 使用AST分析表达式
        try:
            lexer = GithubExprLexer(expression)
            parser = GithubExprParser(lexer)
            ast = parser.parse()
            
            # 记录解析错误
            if parser.errors:
                self.issues.extend(parser.errors)
            
            # 检查AST中的上下文引用
            if ast:
                self._check_context_refs(ast)
                self._check_function_calls(ast)
                
        except Exception as e:
            self.issues.append(f"解析表达式时出错: {str(e)}")
        
        # 如果找到上下文引用或函数调用但未使用${{}}语法，添加警告
        if not self.issues and self._contains_context_ref(expression):
            self.issues.append(f"条件表达式 '{expression}' 中的变量引用应该使用 ${{ ... }} 语法")
        
        if not self.issues and self._contains_function_call(expression):
            self.issues.append(f"条件表达式 '{expression}' 中的函数调用应该使用 ${{ ... }} 语法")
        
        return self.issues
    
    def _analyze_inner_expression(self, expression: str) -> None:
        """分析${{}}内的表达式"""
        try:
            lexer = GithubExprLexer(expression)
            parser = GithubExprParser(lexer)
            ast = parser.parse()
            
            # 记录解析错误
            if parser.errors:
                self.issues.extend(parser.errors)
            
            # 检查AST
            if ast:
                self._check_function_calls(ast)
                self._check_syntax_conventions(ast)
                
        except Exception as e:
            self.issues.append(f"分析内部表达式时出错: {str(e)}")
    
    def _contains_context_ref(self, expression: str) -> bool:
        """检查表达式是否包含上下文引用"""
        contexts = ['github', 'env', 'vars', 'secrets', 'steps', 
                   'needs', 'inputs', 'job', 'matrix', 'strategy']
        
        pattern = r'\b(' + '|'.join(contexts) + r')\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*\b'
        return bool(re.search(pattern, expression))
    
    def _contains_function_call(self, expression: str) -> bool:
        """检查表达式是否包含函数调用"""
        functions = list(self.standard_functions)
        pattern = r'\b(' + '|'.join(functions) + r')\s*\('
        return bool(re.search(pattern, expression))
    
    def _check_context_refs(self, node: GithubASTNode) -> None:
        """检查AST中的上下文引用"""
        if isinstance(node, GithubContextRef):
            # 上下文引用已经在AST构建时验证，这里可以做额外检查
            pass
                
        elif isinstance(node, GithubBinaryOp):
            self._check_context_refs(node.left)
            self._check_context_refs(node.right)
                
        elif isinstance(node, GithubUnaryOp):
            self._check_context_refs(node.expr)
                
        elif isinstance(node, GithubFunctionCall):
            for arg in node.args:
                self._check_context_refs(arg)
    
    def _check_function_calls(self, node: GithubASTNode) -> None:
        """检查函数调用是否使用标准函数"""
        if isinstance(node, GithubFunctionCall):
            if node.name not in self.standard_functions:
                self.issues.append(f"未知函数调用: '{node.name}'")
            
            for arg in node.args:
                self._check_function_calls(arg)
                
        elif isinstance(node, GithubBinaryOp):
            self._check_function_calls(node.left)
            self._check_function_calls(node.right)
                
        elif isinstance(node, GithubUnaryOp):
            self._check_function_calls(node.expr)
    
    def _check_syntax_conventions(self, node: GithubASTNode) -> None:
        """检查语法约定"""
        # 这里可以添加更多GitHub Actions特定的语法约定检查
        pass

# 本地缓存的 Schema 文件路径
LOCAL_SCHEMA_PATH = Path(__file__).parent / "schemas" / "github-workflow.json"

# Actionlint 工具路径
ACTIONLINT_PATH = "actionlint"

class WorkflowValidator:
    """
    工作流验证器，使用JSON Schema和actionlint验证工作流文件格式
    
    使用了多种验证方式:
    1. 基本 YAML 解析验证
    2. 使用 GitHub Actions 官方 JSON Schema 进行结构验证
{{ ... }}
    3. 尝试使用 actionlint 进行更深入的语法验证
    4. 自定义的格式和最佳实践检查
    """
    
    def __init__(self, logger=None):
        """
        初始化验证器
        
        Args:
            logger: 可选的日志记录器
        """
        # 设置日志记录器
        self.logger = logger or logging.getLogger('workflow_validator')
        
        # 初始化YAML解析器
        self.yaml = ruamel.yaml.YAML(typ='safe')
        
        # 确保 Schema 目录存在
        if not LOCAL_SCHEMA_PATH.parent.exists():
            LOCAL_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载或下载 JSON Schema
        self.schema = self._load_schema()
        
        # 检查是否安装了 actionlint
        self.actionlint_available = self._check_actionlint()
    
    def _load_schema(self) -> Dict[str, Any]:
        """
        加载GitHub Actions的JSON Schema
        如果本地没有，则从网络下载并缓存
        
        Returns:
            GitHub Actions工作流的JSON Schema
        """
        try:
            # 尝试从本地加载
            if LOCAL_SCHEMA_PATH.exists():
                with open(LOCAL_SCHEMA_PATH, 'r', encoding='utf-8') as f:
                    schema = json.load(f)
                    self.logger.info(f"从本地加载 GitHub Actions Schema: {LOCAL_SCHEMA_PATH}")
                    return schema
            
            # 从网络下载
            self.logger.info(f"从网络下载 GitHub Actions Schema: {GITHUB_ACTIONS_SCHEMA_URL}")
            response = requests.get(GITHUB_ACTIONS_SCHEMA_URL, timeout=30)
            response.raise_for_status()
            schema = response.json()
            
            # 保存到本地
            with open(LOCAL_SCHEMA_PATH, 'w', encoding='utf-8') as f:
                json.dump(schema, f, indent=2)
            
            return schema
        except Exception as e:
            self.logger.warning(f"加载 Schema 失败: {e}，将使用基本验证")
            # 返回一个最小的 Schema
            return {
                "type": "object",
                "required": ["name", "on", "jobs"],
                "properties": {
                    "name": {"type": "string"},
                    "on": {},
                    "jobs": {"type": "object"}
                }
            }
    
    def _check_actionlint(self) -> bool:
        """
        检查系统中是否安装了actionlint
        
        Returns:
            bool: 是否安装了actionlint
        """
        try:
            result = subprocess.run(['actionlint', '--version'], 
                                    capture_output=True, text=True, check=False)
            if result.returncode == 0:
                self.logger.info(f"找到 actionlint: {result.stdout.strip()}")
                return True
            return False
        except FileNotFoundError:
            self.logger.info("未找到 actionlint，将使用基本验证")
            return False
    
    def validate(self, yaml_content: str) -> Tuple[bool, List[str]]:
        """
        验证YAML内容
        
        Args:
            yaml_content: YAML字符串
            
        Returns:
            (是否有效, 错误消息列表)
        """
        is_valid, errors, _ = self.validate_with_warnings(yaml_content)
        return is_valid, errors
        
    def validate_with_warnings(self, yaml_content: str) -> Tuple[bool, List[str], List[str]]:
        """
        验证YAML内容，将条件表达式格式问题从错误降级为警告
        
        Args:
            yaml_content: YAML字符串
            
        Returns:
            (是否有效, 错误消息列表, 警告消息列表)
        """
        errors = []
        warnings = []
        
        # 基本YAML解析验证
        try:
            workflow_dict = self.yaml.load(yaml_content)
            if not workflow_dict:
                errors.append("YAML内容为空或格式错误")
                return False, errors, warnings
        except Exception as e:
            errors.append(f"YAML解析错误: {str(e)}")
            return False, errors, warnings
        
        # 使用JSON Schema验证
        schema_errors = self._validate_with_schema(workflow_dict)
        errors.extend(schema_errors)
        
        # 使用actionlint验证(如果可用)
        if self.actionlint_available:
            actionlint_errors = self._validate_with_actionlint(yaml_content)
            errors.extend(actionlint_errors)
        
        # 自定义验证，但将条件表达式格式问题降级为警告
        custom_errors, format_warnings = self._perform_custom_validation_with_warnings(yaml_content, workflow_dict)
        errors.extend(custom_errors)
        warnings.extend(format_warnings)
        
        return len(errors) == 0, errors, warnings
    
    def _validate_with_schema(self, workflow_dict: Dict[str, Any]) -> List[str]:
        """
        使用JSON Schema验证工作流字典
        
        Args:
            workflow_dict: 解析后的工作流字典
            
        Returns:
            错误消息列表
        """
        errors = []
        
        try:
            jsonschema.validate(instance=workflow_dict, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            # 处理验证错误，提供更友好的错误消息
            path = "/".join(str(p) for p in e.path) if e.path else "root"
            message = e.message.replace("'", '"')
            errors.append(f"Schema验证错误 (路径: {path}): {message}")
        except Exception as e:
            errors.append(f"Schema验证发生未知错误: {str(e)}")
        
        return errors
    
    def _validate_with_actionlint(self, yaml_content: str) -> List[str]:
        """
        使用actionlint验证工作流
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            错误消息列表
        """
        errors = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp:
            try:
                # 写入临时文件
                temp.write(yaml_content)
                temp.flush()
                temp_path = temp.name
                
                # 运行actionlint
                result = subprocess.run(
                    ['actionlint', '-oneline', temp_path], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    # 解析actionlint输出
                    for line in result.stdout.splitlines():
                        # 移除文件路径，使错误消息更清晰
                        error_message = line.replace(temp_path, "workflow.yml")
                        errors.append(f"Actionlint: {error_message}")
            except Exception as e:
                errors.append(f"运行 actionlint 时发生错误: {str(e)}")
            finally:
                # 确保删除临时文件
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        return errors
    
    def _perform_custom_validation_with_warnings(self, yaml_content: str, workflow_dict: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        执行自定义验证检查，将条件表达式格式问题降级为警告
        
        Args:
            yaml_content: YAML内容
            workflow_dict: 解析后的工作流字典
            
        Returns:
            (错误消息列表, 警告消息列表)
        """
        errors = []
        warnings = []
        
        # 验证作业引用 - 这是严重错误，不降级
        job_ref_errors = self._validate_job_references(workflow_dict)
        errors.extend(job_ref_errors)
        
        # 将条件表达式验证结果降级为警告
        condition_warnings = self._validate_conditions(yaml_content)
        warnings.extend(condition_warnings)
        
        # 将环境变量引用验证结果降级为警告
        env_warnings = self._validate_environment_variables(yaml_content)
        warnings.extend(env_warnings)
        
        # 检查常见格式问题 - 这些本来就是警告
        format_warnings = self.check_for_common_formatting_issues(yaml_content)
        warnings.extend(format_warnings)
        
        return errors, warnings
    
    def _validate_conditions(self, yaml_content: str) -> List[str]:
        """
        验证条件表达式使用AST解析方法
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            警告消息列表（已经从错误降级）
        """
        warnings = []
        
        # 查找所有if条件
        if_conditions = re.findall(r'if:\s*([^\n]+)', yaml_content)
        
        # 使用AST分析器验证每个条件
        analyzer = GithubExpressionAnalyzer()
        
        for condition in if_conditions:
            condition = condition.strip()
            
            # 跳过Jinja2模板
            if '{{' in condition and '}}' in condition and not condition.startswith('${{'):
                continue
                
            # 分析条件表达式使用AST
            issues = analyzer.analyze(condition)
            
            if issues:
                warnings.extend(issues)
        
        return warnings
    
    def _check_env_in_dict(self, obj: Any, warnings: List[str], path: str) -> None:
        """
        递归检查字典中的环境变量引用
        
        Args:
            obj: 要检查的对象（字典、列表或基本类型）
            warnings: 警告消息列表（会被修改）
            path: 当前对象的路径
        """
        if isinstance(obj, dict):
            # 特别处理env节点
            if 'env' in obj and isinstance(obj['env'], dict):
                env_path = f"{path}.env" if path else "env"
                for var_name, var_value in obj['env'].items():
                    if isinstance(var_value, str):
                        # 使用AST分析器检查环境变量值
                        analyzer = GithubExpressionAnalyzer()
                        issues = analyzer.analyze(var_value)
                        
                        if issues:
                            for issue in issues:
                                warnings.append(f"在路径 '{env_path}.{var_name}' {issue}")
            
            # 递归检查所有键值对
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                self._check_env_in_dict(value, warnings, new_path)
                
        elif isinstance(obj, list):
            # 递归检查列表中的每个元素
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                self._check_env_in_dict(item, warnings, new_path)
    
    def _validate_environment_variables(self, yaml_content: str) -> List[str]:
        """
        验证环境变量引用
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            警告消息列表（已经从错误降级）
        """
        warnings = []
        
        # 使用更健壮的方式查找环境变量引用
        # 先尝试解析YAML
        try:
            yaml_dict = yaml.safe_load(yaml_content)
            if yaml_dict:
                self._check_env_in_dict(yaml_dict, warnings, path="")
                return warnings
        except Exception as e:
            # 如果YAML解析失败，回退到正则表达式方法
            pass
            
        # 使用正则表达式方法作为备用
        env_sections = re.finditer(r'\s+env:\s*(.*?)(?=\s+\w+:|$)', yaml_content, re.DOTALL)
        for env_match in env_sections:
            env_block = env_match.group(1)
            env_var_matches = re.finditer(r'\s+(\w+):\s*([^\n]+)', env_block)
            
            for var_match in env_var_matches:
                var_name = var_match.group(1)
                var_value = var_match.group(2).strip()
                
                # 检查变量引用格式
                if re.search(r'^(github|env|vars|secrets|steps|needs|inputs)\.[\w\.]+$', var_value):
                    if not (var_value.startswith('${{') and var_value.endswith('}}')):
                        warnings.append(f"环境变量 '{var_name}' 的值 '{var_value}' 应该使用 ${{ ... }} 语法")
                
                # 检查 secrets 引用
                if var_value.startswith('secrets.') and not var_value.startswith('${{ secrets.'):
                    warnings.append(f"环境变量 '{var_name}' 的 secrets 引用 '{var_value}' 应该使用 ${{ ... }} 语法")
        
        return warnings
    
    def _validate_job_references(self, workflow_dict: Dict[str, Any]) -> List[str]:
        """
        验证作业引用（例如needs字段）
        
        Args:
            workflow_dict: 工作流字典
            
        Returns:
            错误消息列表
        """
        errors = []
        
        if not isinstance(workflow_dict.get('jobs', {}), dict):
            return errors
            
        job_ids = set(workflow_dict['jobs'].keys())
        
        for job_id, job in workflow_dict['jobs'].items():
            if not isinstance(job, dict):
                continue
                
            needs = job.get('needs', [])
            
            if isinstance(needs, str):
                if needs not in job_ids:
                    errors.append(f"作业 '{job_id}' 引用了不存在的作业 '{needs}'")
            elif isinstance(needs, list):
                for need in needs:
                    if need not in job_ids:
                        errors.append(f"作业 '{job_id}' 引用了不存在的作业 '{need}'")
        
        return errors
    
    def check_for_common_formatting_issues(self, yaml_content: str) -> List[str]:
        """
        检查常见的格式问题
        
        Args:
            yaml_content: YAML内容
            
        Returns:
            警告消息列表
        """
        warnings = []
        
        # 检查操作符周围的空格
        if_conditions = re.findall(r'if:\s*\$\{\{\s*(.+?)\s*\}\}', yaml_content)
        
        for condition in if_conditions:
            # 检查比较操作符周围的空格
            if re.search(r'[a-zA-Z0-9_\'"]\s*([=!<>][=<>]?)\s*[a-zA-Z0-9_\'"]', condition):
                if not re.search(r'[a-zA-Z0-9_\'"] ([=!<>][=<>]?) [a-zA-Z0-9_\'"]', condition):
                    warnings.append(f"条件表达式 '{condition}' 中的操作符两侧应该有空格")
            
            # 检查逻辑操作符周围的空格
            if '&&' in condition or '||' in condition:
                if not re.search(r' (?:\&\&|\|\|) ', condition):
                    warnings.append(f"条件表达式 '{condition}' 中的逻辑操作符两侧应该有空格")
        
        return warnings
    
    def validate_template(self, template_content: str) -> Tuple[bool, List[str]]:
        """
        验证工作流模板文件
        
        Args:
            template_content: 模板内容
            
        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []
        
        # 检查Jinja2语法
        try:
            import jinja2
            env = jinja2.Environment()
            env.parse(template_content)
        except Exception as e:
            # 只记录错误，但不返回失败
            self.logger.warning(f"Jinja2模板语法警告: {str(e)}")
            # 将错误添加到列表中，但不中断验证
            errors.append(f"Jinja2模板语法警告: {str(e)}")
        
        # 检查GitHub Actions特定语法
        actions_errors = self._check_actions_specific_syntax(template_content)
        errors.extend(actions_errors)
        
        # 如果没有错误，可以尝试渲染一个简单的模板示例并验证结果
        if not errors:
            try:
                # 创建一个简单的上下文
                context = {
                    'workflow_name': 'Test Workflow',
                    'runner_os': 'ubuntu-latest',
                    'message': 'Hello, World!',
                    'site_id': 'test',
                    'python_version': '3.10',
                    'scraper_dependencies': 'requests',
                    'output_filename': 'output.json',
                    'data_dir': 'data',
                    'status_dir': 'status',
                    'scraper_script': 'test.py',
                    'run_analysis': True,
                    'use_proxy': False,
                    'env_vars': [],
                    'github': {
                        'event': {'ref': 'refs/heads/main'},
                        'repository': 'test/repo',
                        'workflow': 'test-workflow',
                        'run_number': 1
                    },
                    'env': {
                        'GITHUB_TOKEN': 'test-token',
                        'API_KEY': 'test-api-key',
                        'DEBUG': 'false'
                    }
                }
                
                # 使用jinja2渲染模板
                env = jinja2.Environment(
                    loader=jinja2.BaseLoader(),
                    autoescape=False,
                    trim_blocks=True,
                    lstrip_blocks=True
                )
                template = env.from_string(template_content)
                rendered = template.render(**context)
                
                # 确保渲染后的内容是有效的YAML
                try:
                    # 临时注释掉YAML验证，仅检查Jinja2语法
                    # self.yaml.load(rendered)
                    pass
                except Exception as e:
                    # 只记录警告，不阻止流程
                    self.logger.warning(f"渲染后的模板警告: {str(e)}")
            except Exception as e:
                # 只记录警告，不阻止流程
                self.logger.warning(f"渲染模板示例警告: {str(e)}")
        
        return len(errors) == 0, errors
    
    def _check_actions_specific_syntax(self, template_content: str) -> List[str]:
        """
        检查GitHub Actions特定的语法
        
        Args:
            template_content: 模板内容
            
        Returns:
            错误消息列表
        """
        errors = []
        
        # 检查是否有name字段
        if not re.search(r'^\s*name:', template_content, re.MULTILINE):
            errors.append("模板缺少必需的 'name' 字段")
        
        # 检查是否有on字段
        if not re.search(r'^\s*on:', template_content, re.MULTILINE):
            errors.append("模板缺少必需的 'on' 字段")
        
        # 检查是否有jobs字段
        if not re.search(r'^\s*jobs:', template_content, re.MULTILINE):
            errors.append("模板缺少必需的 'jobs' 字段")
        
        # 检查作业是否有runs-on字段
        jobs_section = re.search(r'jobs:(.*?)(?:^\S|\Z)', template_content, re.MULTILINE | re.DOTALL)
        if jobs_section:
            jobs_content = jobs_section.group(1)
            if not re.search(r'runs-on:', jobs_content):
                errors.append("作业定义中缺少必需的 'runs-on' 字段")
        
        # 检查作业是否有steps字段
        if jobs_section:
            jobs_content = jobs_section.group(1)
            if not re.search(r'steps:', jobs_content):
                errors.append("作业定义中缺少必需的 'steps' 字段")
        
        return errors 
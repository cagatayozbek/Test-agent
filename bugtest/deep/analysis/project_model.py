import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

@dataclass
class FunctionInfo:
    name: str
    module_path: str
    args: list[str]
    return_annotation: Optional[str]
    line_range: tuple[int, int]
    decorators: list[str]
    docstring: Optional[str]
    complexity: int  # approximately structural risk score
    calls: list[str]

@dataclass
class ClassInfo:
    name: str
    module_path: str
    line_range: tuple[int, int]
    methods: list[FunctionInfo]
    bases: list[str]

@dataclass
class ImportInfo:
    module: str
    names: list[str]
    is_relative: bool

@dataclass
class ModuleInfo:
    path: str
    imports: list[ImportInfo]
    functions: list[FunctionInfo]
    classes: list[ClassInfo]

@dataclass
class ProjectSnapshot:
    modules: dict[str, ModuleInfo]
    root_path: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_all_functions(self) -> list[FunctionInfo]:
        functions = []
        for mod in self.modules.values():
            functions.extend(mod.functions)
            for cls in mod.classes:
                functions.extend(cls.methods)
        return functions

    def summary(self) -> str:
        num_mods = len(self.modules)
        num_cls = sum(len(m.classes) for m in self.modules.values())
        num_funcs = len(self.get_all_functions())
        return f"Project with {num_mods} modules, {num_cls} classes, and {num_funcs} functions."


class ASTVisitor(ast.NodeVisitor):
    def __init__(self, module_path: str):
        self.module_path = module_path
        self.imports = []
        self.functions = []
        self.classes = []

    def _get_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.BoolOp)):
                complexity += 1
        return complexity

    def _get_calls(self, node: ast.AST) -> list[str]:
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return calls
        
    def _get_args(self, args: ast.arguments) -> list[str]:
        arg_names = []
        for arg in args.posonlyargs + args.args + args.kwonlyargs:
            arg_names.append(arg.arg)
        if args.vararg:
            arg_names.append(f"*{args.vararg.arg}")
        if args.kwarg:
            arg_names.append(f"**{args.kwarg.arg}")
        return arg_names

    def _extract_function(self, node: ast.FunctionDef) -> FunctionInfo:
        decorators = [ast.unparse(d) if hasattr(ast, 'unparse') else str(d) for d in node.decorator_list]
        return_ann = ast.unparse(node.returns) if hasattr(ast, 'unparse') and node.returns else None
        
        return FunctionInfo(
            name=node.name,
            module_path=self.module_path,
            args=self._get_args(node.args),
            return_annotation=return_ann,
            line_range=(node.lineno, node.end_lineno or node.lineno),
            decorators=decorators,
            docstring=ast.get_docstring(node),
            complexity=self._get_complexity(node),
            calls=self._get_calls(node)
        )

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportInfo(module=alias.name, names=[], is_relative=False))
        self.generic_visit(node)
        
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module if node.module else ""
        names = [alias.name for alias in node.names]
        self.imports.append(ImportInfo(module=module, names=names, is_relative=node.level > 0))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append(self._extract_function(node))
        # Skip generic visit so we don't treat nested functions as top level yet
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.functions.append(self._extract_function(node))

    def visit_ClassDef(self, node: ast.ClassDef):
        methods = []
        for body_item in node.body:
            if isinstance(body_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function(body_item))
                
        bases = [ast.unparse(b) if hasattr(ast, 'unparse') else str(b) for b in node.bases]
        self.classes.append(ClassInfo(
            name=node.name,
            module_path=self.module_path,
            line_range=(node.lineno, node.end_lineno or node.lineno),
            methods=methods,
            bases=bases
        ))
        
    def visit_Assign(self, node: ast.Assign):
        self.generic_visit(node)


class ProjectModel:
    """AST-tabanlı proje analiz motoru."""
    
    def __init__(self, workspace: str):
        self.workspace = Path(workspace)
    
    def analyze(self) -> ProjectSnapshot:
        """Workspace'teki tüm .py dosyalarını parse et."""
        modules = {}
        
        for path in self.workspace.rglob("*.py"):
            # Skip heavy directories and hidden folders
            ignore_parts = {".venv", "venv", "node_modules", ".git", "__pycache__", "site-packages"}
            if any(part in ignore_parts for part in path.parts):
                continue
                
            try:
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
            except Exception:
                continue
                
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError:
                continue
                
            # Compute relative module path for identification
            rel_path = path.relative_to(self.workspace)
            visitor = ASTVisitor(module_path=str(rel_path))
            visitor.visit(tree)
            
            mod_info = ModuleInfo(
                path=str(rel_path),
                imports=visitor.imports,
                functions=visitor.functions,
                classes=visitor.classes,
            )
            modules[str(rel_path)] = mod_info
            
        return ProjectSnapshot(modules=modules, root_path=str(self.workspace))

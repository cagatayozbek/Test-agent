from collections import defaultdict
from .project_model import ProjectSnapshot

class DependencyGraph:
    """Modül bağımlılık ve fonksiyon çağrı grafiği."""
    
    def __init__(self, snapshot: ProjectSnapshot):
        self.snapshot = snapshot
        # module_path -> set of external module names it imports
        self._import_graph: dict[str, set[str]] = defaultdict(set)
        # external module -> set of module_paths that import it
        self._reverse_graph: dict[str, set[str]] = defaultdict(set)
        self._build()
    
    def _build(self):
        for module_path, mod_info in self.snapshot.modules.items():
            for imp in mod_info.imports:
                target_mod = imp.module
                if target_mod:
                    self._import_graph[module_path].add(target_mod)
                    self._reverse_graph[target_mod].add(module_path)
    
    def get_import_graph(self) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self._import_graph.items()}
        
    def get_dependents(self, module_name: str) -> set[str]:
        """Bu modülü import eden modüller (etki alanı)."""
        return self._reverse_graph.get(module_name, set())

    def get_impact_set(self, changed_module: str) -> set[str]:
        """Değişiklik etki analizi — transitive closure."""
        visited = set()
        queue = [changed_module]
        while queue:
            current = queue.pop(0)
            if current not in visited:
                visited.add(current)
                for dependent in self.get_dependents(current):
                    if dependent not in visited:
                        queue.append(dependent)
        
        return visited

    def to_prompt_context(self) -> str:
        """LLM'e gönderilebilecek özet. Statik sınırlarla kısıtlıdır."""
        lines = ["STATIC DEPENDENCY MAP (Note: Dynamic imports are not caught):"]
        for mod, imports in self._import_graph.items():
            if imports:
                lines.append(f"  - {mod} depends on: {', '.join(imports)}")
        if len(lines) == 1:
            return "STATIC DEPENDENCY MAP: No explicit internal dependencies found."
        return "\n".join(lines)

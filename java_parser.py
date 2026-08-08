
"""
Java Source Code Parser and Metric Calculator
Based on: "An automatic code smell detection plugin using code metrics analysis"
"""
import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict


@dataclass
class MethodInfo:
    name: str
    return_type: str
    parameters: List[Tuple[str, str]]  # (type, name)
    modifiers: List[str]
    body: str
    start_line: int
    end_line: int
    loc: int = 0
    cyclo: int = 0
    max_nesting: int = 0
    noav: int = 0
    # Coupling metrics
    cint: int = 0
    cdisp: float = 0.0
    cm: int = 0
    cc: int = 0
    atfd: int = 0
    fdp: int = 0
    laa: float = 0.0
    # For internal analysis
    _local_vars: Set[str] = field(default_factory=set)
    _accessed_fields: Set[str] = field(default_factory=set)
    _foreign_accesses: List[Tuple[str, str]] = field(default_factory=list)
    _method_calls: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class FieldInfo:
    name: str
    type: str
    modifiers: List[str]
    line: int


@dataclass
class ClassInfo:
    name: str
    package: str
    modifiers: List[str]
    parent_class: Optional[str]
    interfaces: List[str]
    fields: List[FieldInfo] = field(default_factory=list)
    methods: List[MethodInfo] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0
    # Metrics
    loc: int = 0
    nom: int = 0
    nopm: int = 0
    nopam: int = 0
    wmc: int = 0
    tcc: float = 0.0
    woc: float = 0.0
    nas: int = 0
    pnas: float = 0.0
    nprotm: int = 0
    bur: float = 0.0
    bovr: float = 0.0
    amw: float = 0.0
    nopa: int = 0
    noam: int = 0
    # Smells detected
    smells: List[Dict] = field(default_factory=list)


class JavaParser:
    def __init__(self):
        self.classes: List[ClassInfo] = []
        self.all_methods_calls: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.method_to_class: Dict[str, str] = {}

    def remove_comments(self, source: str) -> str:
        """Remove Java comments while preserving line numbers."""
        source = re.sub(r'//.*$', '', source, flags=re.MULTILINE)
        def replace_multiline(match):
            text = match.group(0)
            return '\n' * text.count('\n')
        source = re.sub(r'/\*.*?\*/', replace_multiline, source, flags=re.DOTALL)
        return source

    def parse_file(self, filepath: str, source: str) -> List[ClassInfo]:
        """Parse a Java source file and extract classes with metrics."""
        source = self.remove_comments(source)
        lines = source.split('\n')

        package_match = re.search(r'package\s+([\w.]+);', source)
        package = package_match.group(1) if package_match else "default"

        classes = self._extract_classes(source, lines, package)

        for cls in classes:
            self._calculate_class_metrics(cls, lines)

        self.classes.extend(classes)
        return classes

    def _extract_classes(self, source: str, lines: List[str], package: str) -> List[ClassInfo]:
        """Extract class declarations and their contents."""
        classes = []

        class_pattern = re.compile(
            r'((?:public\s+|private\s+|protected\s+|abstract\s+|final\s+)*)'
            r'class\s+(\w+)\s*'
            r'(?:extends\s+(\w+))?\s*'
            r'(?:implements\s+([\w\s,]+))?\s*\{',
            re.DOTALL
        )

        for match in class_pattern.finditer(source):
            modifiers_str = match.group(1) or ""
            class_name = match.group(2)
            parent = match.group(3)
            interfaces_str = match.group(4)

            modifiers = modifiers_str.strip().split() if modifiers_str.strip() else []
            interfaces = [i.strip() for i in interfaces_str.split(',')] if interfaces_str else []

            start_pos = match.start()
            start_line = source[:start_pos].count('\n') + 1

            body_start = match.end() - 1
            brace_count = 0
            body_end = body_start
            for i in range(body_start, len(source)):
                if source[i] == '{':
                    brace_count += 1
                elif source[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        body_end = i
                        break

            end_line = source[:body_end].count('\n') + 1
            class_body = source[body_start:body_end+1]

            cls = ClassInfo(
                name=class_name,
                package=package,
                modifiers=modifiers,
                parent_class=parent,
                interfaces=interfaces,
                start_line=start_line,
                end_line=end_line
            )

            cls.fields = self._extract_fields(class_body, start_line)
            cls.methods = self._extract_methods(class_body, start_line)

            classes.append(cls)

        return classes

    def _extract_fields(self, class_body: str, class_start_line: int) -> List[FieldInfo]:
        """Extract field declarations from class body."""
        fields = []
        field_pattern = re.compile(
            r'((?:public\s+|private\s+|protected\s+|static\s+|final\s+|transient\s+|volatile\s+)*)'
            r'(\w+(?:<[^>]+>)?(?:\[\])?)\s+'
            r'(\w+(?:\s*,\s*\w+)*)'
            r'(?:\s*=\s*[^;]+)?;'
        )

        for match in field_pattern.finditer(class_body):
            modifiers_str = match.group(1) or ""
            field_type = match.group(2).strip()
            names_str = match.group(3)

            modifiers = modifiers_str.strip().split() if modifiers_str.strip() else []
            names = [n.strip() for n in names_str.split(',')]

            line_offset = class_body[:match.start()].count('\n')
            line = class_start_line + line_offset

            for name in names:
                fields.append(FieldInfo(
                    name=name,
                    type=field_type,
                    modifiers=modifiers,
                    line=line
                ))

        return fields

    def _extract_methods(self, class_body: str, class_start_line: int) -> List[MethodInfo]:
        """Extract method declarations from class body."""
        methods = []

        method_pattern = re.compile(
            r'((?:public\s+|private\s+|protected\s+|static\s+|abstract\s+|final\s+|synchronized\s+)*)'
            r'(\w+(?:<[^>]+>)?(?:\[\])?)\s+'
            r'(\w+)\s*'
            r'\(([^)]*)\)\s*'
            r'(?:throws\s+[\w\s,]+)?\s*'
            r'(\{;)',
            re.DOTALL
        )

        for match in method_pattern.finditer(class_body):
            modifiers_str = match.group(1) or ""
            return_type = match.group(2).strip()
            method_name = match.group(3)
            params_str = match.group(4)
            body_start_char = match.group(5)

            if body_start_char == ';':
                continue

            modifiers = modifiers_str.strip().split() if modifiers_str.strip() else []
            parameters = self._parse_parameters(params_str)

            start_pos = match.start()
            start_line = class_start_line + class_body[:start_pos].count('\n')

            body_begin = match.end() - 1
            brace_count = 0
            body_end = body_begin
            for i in range(body_begin, len(class_body)):
                if class_body[i] == '{':
                    brace_count += 1
                elif class_body[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        body_end = i
                        break

            end_line = class_start_line + class_body[:body_end].count('\n')
            body = class_body[body_begin:body_end+1]

            methods.append(MethodInfo(
                name=method_name,
                return_type=return_type,
                parameters=parameters,
                modifiers=modifiers,
                body=body,
                start_line=start_line,
                end_line=end_line
            ))

        return methods

    def _parse_parameters(self, params_str: str) -> List[Tuple[str, str]]:
        """Parse method parameters."""
        params = []
        if not params_str.strip():
            return params

        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[-2]
                param_name = parts[-1]
                params.append((param_type, param_name))

        return params

    def _calculate_method_metrics(self, method: MethodInfo):
        """Calculate metrics for a single method."""
        body_lines = method.body.split('\n')

        method.loc = sum(1 for line in body_lines 
                        if line.strip() and not re.match(r'^[\s{}]*$', line.strip()))

        cyclo = 1
        current_nesting = 0
        max_nesting = 0

        control_patterns = [
            (r'\bif\b', True),
            (r'\bfor\b', True),
            (r'\bwhile\b', True),
            (r'\bdo\b', True),
            (r'\bcase\b', False),
            (r'\bcatch\b', True),
            (r'\belse\s+if\b', False),
            (r'\?\s*[^;]+\s*:', False),
        ]

        for line in body_lines:
            stripped = line.strip()

            open_braces = line.count('{')
            close_braces = line.count('}')

            for _ in range(open_braces):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)

            for pattern, increases_nesting in control_patterns:
                matches = re.findall(pattern, stripped)
                cyclo += len(matches)

            cyclo += len(re.findall(r'(?<!&)&(?!&)', stripped))
            cyclo += len(re.findall(r'\|\|(?!\|)', stripped))

            for _ in range(close_braces):
                current_nesting = max(0, current_nesting - 1)

        method.cyclo = cyclo
        method.max_nesting = max_nesting

        local_vars = set()
        param_names = [p[1] for p in method.parameters]
        local_vars.update(param_names)

        var_pattern = re.compile(r'\b(?:int|long|float|double|boolean|char|byte|short|String|var|\w+)\s+(\w+)\s*[;=]')
        for match in var_pattern.finditer(method.body):
            local_vars.add(match.group(1))

        method._local_vars = local_vars

        self._analyze_method_body(method)

        method.noav = len(local_vars) + len(method._accessed_fields)

    def _analyze_method_body(self, method: MethodInfo):
        """Analyze method body for field accesses and method calls."""
        method_call_pattern = re.compile(r'(\w+)\.(\w+)\s*\(')
        simple_call_pattern = re.compile(r'\b(\w+)\s*\(')

        for line in method.body.split('\n'):
            for match in method_call_pattern.finditer(line):
                obj = match.group(1)
                called_method = match.group(2)
                method._method_calls.append((obj, called_method))

                if called_method.startswith('get') or called_method.startswith('set'):
                    method._foreign_accesses.append((obj, called_method))

            for match in simple_call_pattern.finditer(line):
                called = match.group(1)
                if called not in ['if', 'for', 'while', 'switch', 'catch', 'return']:
                    method._method_calls.append(('', called))

    def _calculate_class_metrics(self, cls: ClassInfo, all_lines: List[str]):
        """Calculate class-level metrics."""
        cls.loc = cls.end_line - cls.start_line + 1
        cls.nom = len(cls.methods)

        for method in cls.methods:
            self._calculate_method_metrics(method)

        cls.wmc = sum(m.cyclo for m in cls.methods)
        cls.amw = cls.wmc / cls.nom if cls.nom > 0 else 0

        cls.nopa = sum(1 for f in cls.fields if 'public' in f.modifiers)
        cls.noam = sum(1 for m in cls.methods 
                      if m.name.startswith('get') or m.name.startswith('set'))
        cls.nopm = sum(1 for m in cls.methods if 'public' in m.modifiers)

        cls.nprotm = sum(1 for f in cls.fields if 'protected' in f.modifiers)
        cls.nprotm += sum(1 for m in cls.methods if 'protected' in m.modifiers)

        functional_methods = sum(1 for m in cls.methods 
                                  if 'public' in m.modifiers 
                                  and m.name != cls.name
                                  and not m.name.startswith('get')
                                  and not m.name.startswith('set'))
        cls.woc = functional_methods / cls.nopm if cls.nopm > 0 else 0

        if cls.parent_class:
            cls.nas = sum(1 for m in cls.methods 
                         if 'public' in m.modifiers 
                         and m.name not in ['toString', 'equals', 'hashCode', 'clone'])
        else:
            cls.nas = cls.nopm

        cls.pnas = cls.nas / cls.nopm if cls.nopm > 0 else 0

        if cls.parent_class:
            override_candidates = sum(1 for m in cls.methods 
                                     if m.name in ['toString', 'equals', 'hashCode', 'clone'])
            cls.bovr = override_candidates / cls.nom if cls.nom > 0 else 0
        else:
            cls.bovr = 1.0

        if cls.parent_class:
            inherited_uses = sum(1 for m in cls.methods if 'super.' in m.body)
            cls.bur = inherited_uses / cls.nom if cls.nom > 0 else 0
        else:
            cls.bur = 1.0

        cls.tcc = self._calculate_tcc(cls)

        for method in cls.methods:
            key = f"{cls.name}.{method.name}"
            self.method_to_class[key] = cls.name

    def _calculate_tcc(self, cls: ClassInfo) -> float:
        """Calculate Tight Class Cohesion."""
        if len(cls.methods) < 2:
            return 1.0

        field_names = {f.name for f in cls.fields}
        method_fields = []

        for method in cls.methods:
            accessed = set()
            for line in method.body.split('\n'):
                for field in field_names:
                    if field in line:
                        accessed.add(field)
            method_fields.append(accessed)

        connected_pairs = 0
        total_pairs = 0

        for i in range(len(method_fields)):
            for j in range(i + 1, len(method_fields)):
                total_pairs += 1
                if method_fields[i] & method_fields[j]:
                    connected_pairs += 1

        return connected_pairs / total_pairs if total_pairs > 0 else 0

    def calculate_cross_reference_metrics(self):
        """Calculate metrics that require analyzing all classes together."""
        all_classes = {cls.name: cls for cls in self.classes}

        for cls in self.classes:
            for method in cls.methods:
                foreign_classes = set()
                foreign_accesses = 0
                local_accesses = 0

                for obj, called in method._method_calls:
                    if obj and obj != 'this' and obj not in ['System', 'String', 'Math']:
                        if called.startswith('get') or called.startswith('set'):
                            foreign_accesses += 1
                            foreign_classes.add(obj)
                    elif not obj and called.startswith(('get', 'set')):
                        local_accesses += 1

                method.atfd = foreign_accesses
                method.fdp = len(foreign_classes)

                total_accesses = local_accesses + foreign_accesses
                method.laa = local_accesses / total_accesses if total_accesses > 0 else 1.0

                external_calls = [(obj, called) for obj, called in method._method_calls 
                                 if obj and obj != 'this' and obj not in ['System', 'String', 'Math']]
                unique_calls = set(called for _, called in external_calls)
                unique_classes = set(obj for obj, _ in external_calls if obj)

                method.cint = len(unique_calls)
                method.cdisp = len(unique_classes) / method.cint if method.cint > 0 else 0

        method_callers = defaultdict(list)

        for cls in self.classes:
            for method in cls.methods:
                caller_key = f"{cls.name}.{method.name}"
                for obj, called in method._method_calls:
                    if obj and obj in all_classes:
                        target_key = f"{obj}.{called}"
                        method_callers[target_key].append(caller_key)
                    elif not obj:
                        target_key = f"{cls.name}.{called}"
                        method_callers[target_key].append(caller_key)

        for cls in self.classes:
            for method in cls.methods:
                key = f"{cls.name}.{method.name}"
                callers = method_callers.get(key, [])
                method.cm = len(callers)
                caller_classes = set(c.split('.')[0] for c in callers)
                method.cc = len(caller_classes)

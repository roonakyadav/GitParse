"""
Dependency mapping for code repositories.

Builds dependency graphs by analyzing import statements and relationships.
Creates adjacency lists for dependency visualization and analysis.
"""

import logging
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

# Try to import networkx for advanced graph operations
try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger.warning("networkx not available - using basic dependency mapping")


def build_dependency_map(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a dependency map from parsed files.
    
    Args:
        files: List of parsed file dictionaries
        
    Returns:
        Dictionary containing dependency information and graph structure
    """
    logger.info(f"Building dependency map for {len(files)} files")
    
    # Initialize data structures
    dependency_map = defaultdict(set)  # file -> dependencies
    reverse_dependency_map = defaultdict(set)  # dependency -> files that depend on it
    language_dependencies = defaultdict(set)  # language -> dependencies
    
    # Process each file
    for file_info in files:
        file_path = file_info.get('path', '')
        parsed_data = file_info.get('parsed_data', {})
        language = parsed_data.get('language', 'text')
        
        # Extract dependencies from imports
        dependencies = _extract_dependencies(parsed_data, language, file_path)
        
        # Build maps
        for dep in dependencies:
            dependency_map[file_path].add(dep)
            reverse_dependency_map[dep].add(file_path)
            language_dependencies[language].add(dep)
    
    # Create graph structure
    graph_data = _build_graph_structure(dependency_map, reverse_dependency_map)
    
    # Analyze dependency metrics
    metrics = _calculate_dependency_metrics(dependency_map, reverse_dependency_map)
    
    result = {
        'dependency_map': {k: list(v) for k, v in dependency_map.items()},
        'reverse_dependency_map': {k: list(v) for k, v in reverse_dependency_map.items()},
        'language_dependencies': {k: list(v) for k, v in language_dependencies.items()},
        'graph': graph_data,
        'metrics': metrics,
        'total_files': len(files),
        'total_dependencies': sum(len(deps) for deps in dependency_map.values())
    }
    
    logger.info(f"Dependency map built: {result['total_dependencies']} total dependencies")
    return result


def _extract_dependencies(parsed_data: Dict[str, Any], language: str, file_path: str) -> Set[str]:
    """Extract dependencies from parsed file data."""
    dependencies = set()
    
    imports = parsed_data.get('imports', [])
    
    if language == 'python':
        dependencies.update(_extract_python_dependencies(imports, file_path))
    elif language in ['javascript', 'typescript']:
        dependencies.update(_extract_js_dependencies(imports, file_path))
    elif language == 'java':
        dependencies.update(_extract_java_dependencies(imports, file_path))
    elif language == 'go':
        dependencies.update(_extract_go_dependencies(imports, file_path))
    else:
        # Generic extraction
        dependencies.update(_extract_generic_dependencies(imports, file_path))
    
    return dependencies


def _extract_python_dependencies(imports: List[Dict[str, Any]], file_path: str) -> Set[str]:
    """Extract Python dependencies."""
    dependencies = set()
    
    for imp in imports:
        module = imp.get('module', '')
        if module:
            # Handle relative imports
            if module.startswith('.'):
                # Convert relative import to potential file path
                parts = file_path.split('/')
                if len(parts) > 1:
                    base_path = '/'.join(parts[:-1])
                    level = len(module) - len(module.lstrip('.'))
                    if level > 0:
                        base_path = '/'.join(parts[:-level])
                    dependencies.add(f"{base_path}/{module.lstrip('.')}")
            else:
                # Standard library or third-party import
                dependencies.add(module)
    
    return dependencies


def _extract_js_dependencies(imports: List[Dict[str, Any]], file_path: str) -> Set[str]:
    """Extract JavaScript/TypeScript dependencies."""
    dependencies = set()
    
    for imp in imports:
        module = imp.get('module', '')
        if module:
            if module.startswith('./') or module.startswith('../'):
                # Relative import - convert to file path
                base_path = '/'.join(file_path.split('/')[:-1])
                dependencies.add(f"{base_path}/{module}")
            elif not module.startswith('http'):
                # Node module or local module
                dependencies.add(module)
    
    return dependencies


def _extract_java_dependencies(imports: List[Dict[str, Any]], file_path: str) -> Set[str]:
    """Extract Java dependencies."""
    dependencies = set()
    
    for imp in imports:
        module = imp.get('module', '')
        if module:
            # Java packages are dot-separated
            if module.startswith('java.') or module.startswith('javax.'):
                # Standard library
                dependencies.add(module)
            else:
                # Third-party or local package
                dependencies.add(module)
    
    return dependencies


def _extract_go_dependencies(imports: List[Dict[str, Any]], file_path: str) -> Set[str]:
    """Extract Go dependencies."""
    dependencies = set()
    
    for imp in imports:
        if isinstance(imp, dict):
            modules = imp.get('modules', [])
            for module in modules:
                module = module.strip('"')
                if module:
                    dependencies.add(module)
        else:
            # Single import
            module = str(imp).strip('"')
            if module:
                dependencies.add(module)
    
    return dependencies


def _extract_generic_dependencies(imports: List[Dict[str, Any]], file_path: str) -> Set[str]:
    """Extract dependencies for unsupported languages."""
    dependencies = set()
    
    for imp in imports:
        if isinstance(imp, dict):
            module = imp.get('module') or imp.get('raw', '')
        else:
            module = str(imp)
        
        if module:
            dependencies.add(module)
    
    return dependencies


def _build_graph_structure(dependency_map: Dict[str, Set[str]], 
                        reverse_dependency_map: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Build graph structure for dependency visualization."""
    
    # Build adjacency list
    adjacency = {k: list(v) for k, v in dependency_map.items()}
    
    # Calculate graph metrics
    all_nodes = set(dependency_map.keys()) | set(reverse_dependency_map.keys())
    
    # Find circular dependencies
    circular_deps = _find_circular_dependencies(dependency_map)
    
    # Find top-level files (nothing depends on them)
    top_level = [node for node in all_nodes if not reverse_dependency_map.get(node)]
    
    # Find leaf files (they don't depend on anything)
    leaf_files = [node for node in all_nodes if not dependency_map.get(node)]
    
    graph_data = {
        'adjacency': adjacency,
        'nodes': list(all_nodes),
        'edges': [],
        'circular_dependencies': circular_deps,
        'top_level_files': top_level,
        'leaf_files': leaf_files
    }
    
    # Build edge list
    for source, targets in dependency_map.items():
        for target in targets:
            graph_data['edges'].append({
                'source': source,
                'target': target,
                'type': 'dependency'
            })
    
    # Use networkx for advanced analysis if available
    if NETWORKX_AVAILABLE:
        try:
            G = nx.DiGraph()
            G.add_nodes_from(all_nodes)
            G.add_edges_from([(source, target) for source, targets in dependency_map.items() for target in targets])
            
            # Calculate centrality measures
            graph_data['networkx_metrics'] = {
                'density': nx.density(G),
                'is_connected': nx.is_weakly_connected(G),
                'strongly_connected_components': len(list(nx.strongly_connected_components(G))),
                'average_clustering': nx.average_clustering(G.to_undirected()),
                'in_degree_centrality': dict(nx.in_degree_centrality(G)),
                'out_degree_centrality': dict(nx.out_degree_centrality(G))
            }
        except Exception as e:
            logger.warning(f"NetworkX analysis failed: {e}")
    
    return graph_data


def _find_circular_dependencies(dependency_map: Dict[str, Set[str]]) -> List[List[str]]:
    """Find circular dependencies using DFS."""
    circular_deps = []
    visited = set()
    rec_stack = set()
    path = []
    
    def dfs(node):
        if node in rec_stack:
            # Found a cycle
            cycle_start = path.index(node)
            circular_deps.append(path[cycle_start:] + [node])
            return
        
        if node in visited:
            return
        
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for neighbor in dependency_map.get(node, []):
            dfs(neighbor)
        
        path.pop()
        rec_stack.remove(node)
    
    for node in dependency_map:
        if node not in visited:
            dfs(node)
    
    return circular_deps


def _calculate_dependency_metrics(dependency_map: Dict[str, Set[str]], 
                              reverse_dependency_map: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Calculate dependency metrics."""
    
    total_files = len(dependency_map)
    total_dependencies = sum(len(deps) for deps in dependency_map.values())
    
    # Calculate dependency statistics
    dependency_counts = [len(deps) for deps in dependency_map.values()]
    reverse_dependency_counts = [len(deps) for deps in reverse_dependency_map.values()]
    
    metrics = {
        'total_files': total_files,
        'total_dependencies': total_dependencies,
        'average_dependencies_per_file': total_dependencies / total_files if total_files > 0 else 0,
        'max_dependencies': max(dependency_counts) if dependency_counts else 0,
        'min_dependencies': min(dependency_counts) if dependency_counts else 0,
        'files_with_no_dependencies': dependency_counts.count(0),
        'most_dependent_files': _get_top_dependent_files(dependency_map, 5),
        'most_required_files': _get_top_required_files(reverse_dependency_map, 5)
    }
    
    return metrics


def _get_top_dependent_files(dependency_map: Dict[str, Set[str]], top_n: int = 5) -> List[Dict[str, Any]]:
    """Get files that depend on the most other files."""
    sorted_files = sorted(dependency_map.items(), key=lambda x: len(x[1]), reverse=True)
    return [
        {
            'file': file_path,
            'dependency_count': len(deps),
            'dependencies': list(deps)
        }
        for file_path, deps in sorted_files[:top_n]
    ]


def _get_top_required_files(reverse_dependency_map: Dict[str, Set[str]], top_n: int = 5) -> List[Dict[str, Any]]:
    """Get files that are most depended upon by other files."""
    sorted_files = sorted(reverse_dependency_map.items(), key=lambda x: len(x[1]), reverse=True)
    return [
        {
            'file': file_path,
            'required_by_count': len(deps),
            'required_by': list(deps)
        }
        for file_path, deps in sorted_files[:top_n]
    ]


def get_dependency_summary(dependency_map: Dict[str, Any]) -> str:
    """Generate a human-readable summary of the dependency map."""
    metrics = dependency_map.get('metrics', {})
    
    summary = f"""
Dependency Analysis Summary:
- Total files: {metrics.get('total_files', 0)}
- Total dependencies: {metrics.get('total_dependencies', 0)}
- Average dependencies per file: {metrics.get('average_dependencies_per_file', 0):.2f}
- Files with no dependencies: {metrics.get('files_with_no_dependencies', 0)}
- Circular dependencies found: {len(dependency_map.get('graph', {}).get('circular_dependencies', []))}
"""
    
    return summary.strip()

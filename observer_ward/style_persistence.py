"""
Style Persistence Module

Handles reading and writing styles to commentator_styles.py
using AST parsing for safe file manipulation.
"""

import ast
import json
import logging
from pathlib import Path
from typing import Dict, Optional


class StylePersistence:
    """Manager for loading and saving styles to the styles file."""
    
    def __init__(self, styles_file: Path):
        """
        Initialize the persistence manager.
        
        Args:
            styles_file: Path to commentator_styles.py
        """
        self.styles_file = styles_file
    
    def load_styles(self) -> Dict[str, Dict[str, str]]:
        """
        Load styles from the Python file.
        
        Returns:
            Dictionary of styles {style_name: {"role": "system", "content": "..."}}
        """
        try:
            with open(self.styles_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file as AST
            tree = ast.parse(content)
            
            # Find STYLES assignment
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == 'STYLES':
                            # Found STYLES dict, evaluate it
                            return self._extract_dict_from_node(node.value)
            
            logging.warning("STYLES dict not found in file")
            return {}
            
        except Exception as e:
            logging.error(f"Failed to load styles: {e}")
            return {}
    
    def save_styles(self, styles: Dict[str, Dict[str, str]]) -> bool:
        """
        Save styles back to the Python file.
        
        Args:
            styles: Dictionary of styles to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read current file to preserve structure
            with open(self.styles_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find STYLES dict start and end
            start_idx = None
            end_idx = None
            brace_count = 0
            in_styles = False
            
            for i, line in enumerate(lines):
                if 'STYLES = {' in line or 'STYLES={' in line:
                    start_idx = i
                    in_styles = True
                    brace_count = line.count('{') - line.count('}')
                    if brace_count == 0:
                        end_idx = i
                        break
                elif in_styles:
                    brace_count += line.count('{') - line.count('}')
                    if brace_count == 0:
                        end_idx = i
                        break
            
            if start_idx is None:
                logging.error("Could not find STYLES dict in file")
                return False
            
            # Generate new STYLES dict
            new_styles_text = self._generate_styles_dict(styles)
            
            # Replace the section
            new_lines = (
                lines[:start_idx] +
                [new_styles_text] +
                lines[end_idx + 1:]
            )
            
            # Write back to file
            with open(self.styles_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to save styles: {e}")
            return False
    
    def validate_style(self, name: str, content: str) -> Optional[str]:
        """
        Validate style data.
        
        Args:
            name: Style name
            content: Style content
            
        Returns:
            Error message if invalid, None if valid
        """
        if not name or not name.strip():
            return "Style name cannot be empty"
        
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Style name must be alphanumeric (underscores and hyphens allowed)"
        
        if not content or not content.strip():
            return "Style content cannot be empty"
        
        return None
    
    def _extract_dict_from_node(self, node) -> Dict:
        """Extract dictionary from AST Dict node."""
        if not isinstance(node, ast.Dict):
            return {}
        
        result = {}
        for key_node, value_node in zip(node.keys, node.values):
            if isinstance(key_node, ast.Constant):
                key = key_node.value
                
                # Handle nested dict for style structure
                if isinstance(value_node, ast.Dict):
                    nested = {}
                    for nk, nv in zip(value_node.keys, value_node.values):
                        if isinstance(nk, ast.Constant) and isinstance(nv, ast.Constant):
                            nested[nk.value] = nv.value
                    result[key] = nested
        
        return result
    
    def _generate_styles_dict(self, styles: Dict[str, Dict[str, str]]) -> str:
        """
        Generate Python code for STYLES dict.
        
        Args:
            styles: Dictionary of styles
            
        Returns:
            Python code as string
        """
        lines = ["STYLES = {\n"]
        
        for style_name, style_data in styles.items():
            role = style_data.get("role", "system")
            content = style_data.get("content", "")
            
            # Skip styles with empty content (deleted styles)
            if not content or not content.strip():
                continue
            
            # Escape triple quotes in content for safety
            content_escaped = content.replace('\\', '\\\\').replace('"""', r'\"\"\"')
            
            lines.append(f'    "{style_name}": {{\n')
            lines.append(f'        "role": "{role}",\n')
            lines.append(f'        "content": """{content_escaped}"""\n')
            lines.append(f'    }},\n')
        
        lines.append("}\n")
        
        return ''.join(lines)
    
    def load_favorites(self) -> list:
        """
        Load favorites from JSON file.
        
        Returns:
            List of favorite style names
        """
        favorites_file = self.styles_file.parent / ".favorites.json"
        try:
            if favorites_file.exists():
                with open(favorites_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("favorites", [])
        except Exception as e:
            logging.error(f"Failed to load favorites: {e}")
        return []
    
    def save_favorites(self, favorites: list) -> bool:
        """
        Save favorites to JSON file.
        
        Args:
            favorites: List of favorite style names
            
        Returns:
            True if successful
        """
        favorites_file = self.styles_file.parent / ".favorites.json"
        try:
            with open(favorites_file, 'w', encoding='utf-8') as f:
                json.dump({"favorites": favorites}, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to save favorites: {e}")
            return False
    
    def toggle_favorite(self, style_name: str, favorites: list) -> list:
        """
        Toggle favorite status of a style.
        
        Args:
            style_name: Name of the style
            favorites: Current favorites list
            
        Returns:
            Updated favorites list
        """
        new_favorites = favorites.copy()
        if style_name in new_favorites:
            new_favorites.remove(style_name)
        else:
            new_favorites.append(style_name)
        return new_favorites
    
    def export_styles(self, styles: Dict[str, Dict[str, str]], export_path: Optional[Path] = None) -> Optional[Path]:
        """
        Export styles to JSON file.
        
        Args:
            styles: Dictionary of styles to export
            export_path: Optional custom export path
            
        Returns:
            Path to exported file, or None if failed
        """
        try:
            from datetime import datetime
            
            if export_path is None:
                # Create exports directory
                exports_dir = self.styles_file.parent / "exports"
                exports_dir.mkdir(exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = exports_dir / f"styles_export_{timestamp}.json"
            
            # Prepare export data
            export_data = {
                "version": "1.0",
                "export_date": datetime.now().isoformat(),
                "styles": styles
            }
            
            # Write to file
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return export_path
            
        except Exception as e:
            logging.error(f"Failed to export styles: {e}")
            return None
    
    def import_styles(self, import_path: Path, merge: bool = True) -> Optional[Dict[str, Dict[str, str]]]:
        """
        Import styles from JSON export file.
        
        Args:
            import_path: Path to import file
            merge: If True, merge with existing; if False, replace
            
        Returns:
            Merged/imported styles dict, or None if failed
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            imported_styles = import_data.get("styles", {})
            
            if merge:
                # Load existing styles
                existing = self.load_styles()
                # Merge (skip conflicts - don't overwrite existing)
                for name, data in imported_styles.items():
                    if name not in existing:
                        existing[name] = data
                return existing
            else:
                return imported_styles
                
        except Exception as e:
            logging.error(f"Failed to import styles: {e}")
            return None
    
    def load_stats(self) -> dict:
        """
        Load usage statistics from JSON file.
        
        Returns:
            Statistics dict with style usage data
        """
        stats_file = self.styles_file.parent / ".stats.json"
        try:
            if stats_file.exists():
                with open(stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load stats: {e}")
        return {"styles": {}}
    
    def save_stats(self, stats: dict) -> bool:
        """
        Save statistics to JSON file.
        
        Args:
            stats: Statistics dictionary
            
        Returns:
            True if successful
        """
        stats_file = self.styles_file.parent / ".stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logging.error(f"Failed to save stats: {e}")
            return False
    
    def record_usage(self, style_name: str) -> None:
        """
        Record that a style was just used.
        
        Args:
            style_name: Name of the style that was used
        """
        from datetime import datetime
        
        stats = self.load_stats()
        if "styles" not in stats:
            stats["styles"] = {}
        
        if style_name not in stats["styles"]:
            stats["styles"][style_name] = {"count": 0, "last_used": None}
        
        stats["styles"][style_name]["count"] += 1
        stats["styles"][style_name]["last_used"] = datetime.now().isoformat()
        
        self.save_stats(stats)
    
    def get_top_styles(self, n: int = 5) -> list:
        """
        Get top N most used styles.
        
        Args:
            n: Number of top styles to return
            
        Returns:
            List of (style_name, count) tuples, sorted by count descending
        """
        stats = self.load_stats()
        style_stats = stats.get("styles", {})
        
        items = [(name, data.get("count", 0)) for name, data in style_stats.items()]
        items.sort(key=lambda x: x[1], reverse=True)
        return items[:n]


# Global instance
_styles_file = Path(__file__).parent.parent / "commentator_styles.py"
STYLE_MANAGER = StylePersistence(_styles_file)

"""
Prompt management with templates and versioning.
"""
from typing import Dict, Optional, List
from pathlib import Path
import json
import logging
from dataclasses import dataclass, asdict


@dataclass
class PromptTemplate:
    """Template for building prompts with multiple sections."""
    
    name: str
    sections: Dict[str, str]  # section_name -> template_text
    version: str = "1.0"
    description: str = ""
    
    def render(self, **variables) -> str:
        """
        Render template with variables.
        
        Args:
            **variables: Variables to substitute in template
            
        Returns:
            Rendered prompt string
        """
        result = []
        for section_name, template in self.sections.items():
            try:
                rendered = template.format(**variables)
                if rendered.strip():
                    result.append(rendered)
            except KeyError as e:
                logging.warning(f"Missing variable in template {self.name}, section {section_name}: {e}")
                result.append(template)  # Use unrendered template as fallback
        
        return "\n\n".join(result)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PromptTemplate':
        """Create from dictionary."""
        return cls(**data)


class PromptManager:
    """
    Manages system prompts with templates and versioning.
    
    Features:
    - Template-based prompt construction
    - Dynamic section composition
    - Load templates from JSON files
    - Version management
    """
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize prompt manager.
        
        Args:
            prompts_dir: Directory containing prompt template files
        """
        if prompts_dir:
            self.prompts_dir = Path(prompts_dir)
        else:
            self.prompts_dir = Path(__file__).parent
        
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default prompt templates."""
        
        # Main analysis prompt template
        self.templates['analysis'] = PromptTemplate(
            name='analysis',
            version='1.0',
            description='Main template for image analysis with persona and history',
            sections={
                'persona': 'PERSONA: {persona_instruction}',
                'context': '{persona_context}',
                'task': """[YOUR PRIMARY TASK]:
Analyze THIS image you are seeing RIGHT NOW.
- Focus on what's happening on the screen at this moment
- Comment on the PRESENT, not the past
- React to what you see currently

⚠️ IMPORTANT: If the screen content looks similar to before:
- DO NOT mention the same elements again
- Find NEW aspects: different colors, layout changes, text snippets
- Change your perspective entirely rather than repeating observations""",
                'history': """[WHAT YOU ALREADY SAID - NEVER REPEAT]:
{history_display}""",
                'anti_repetition': """⚠️ WARNING - DO NOT:
1. Copy ANY full sentence or phrase from above verbatim
2. Use the same metaphors
3. Repeat the same sentence structure
4. Use identical opening words

✓ YOU MUST:
- Express COMPLETELY NEW sentences
- Find DIFFERENT metaphors and imagery
- Vary your opening each time
- Change the perspective even if the screen is similar
- Use fresh vocabulary and phrasing""",
                'user_message': '[USER MESSAGE]: {user_message}\n(Answer the user while maintaining your persona and reacting to the screen)',
                'output_format': """OUTPUT FORMAT: Return a JSON object with the following fields:
- comment: The commentary text (in the requested style/language).
- mood_update: One word describing your new emotional state (e.g., 'angry', 'happy', 'bored', 'excited').
- intensity: 'low', 'medium', or 'high'.
Ensure the JSON is valid. Do not wrap in markdown code blocks."""
            }
        )
        
        # Simple chat template (without image analysis)
        self.templates['chat'] = PromptTemplate(
            name='chat',
            version='1.0',
            description='Simple chat template for text-only interactions',
            sections={
                'persona': '{persona_instruction}',
                'history': 'Previous conversation:\n{history_display}',
                'user_message': 'User: {user_message}',
                'instruction': 'Respond naturally while maintaining your persona.'
            }
        )
    
    def load_from_file(self, filepath: Path) -> bool:
        """
        Load prompt template from JSON file.
        
        Args:
            filepath: Path to JSON template file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle single template or list of templates
            templates_data = data if isinstance(data, list) else [data]
            
            for template_data in templates_data:
                template = PromptTemplate.from_dict(template_data)
                self.templates[template.name] = template
                logging.info(f"Loaded prompt template: {template.name} v{template.version}")
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load prompt template from {filepath}: {e}")
            return False
    
    def load_all_from_directory(self, directory: Optional[Path] = None):
        """
        Load all JSON template files from directory.
        
        Args:
            directory: Directory to scan (uses self.prompts_dir if None)
        """
        search_dir = Path(directory) if directory else self.prompts_dir
        
        if not search_dir.exists():
            logging.warning(f"Prompts directory not found: {search_dir}")
            return
        
        loaded_count = 0
        for json_file in search_dir.glob("*.json"):
            if self.load_from_file(json_file):
                loaded_count += 1
        
        logging.info(f"Loaded {loaded_count} template files from {search_dir}")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            PromptTemplate or None if not found
        """
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self.templates.keys())
    
    def build_analysis_prompt(
        self,
        persona_instruction: str = "",
        persona_context: str = "",
        history_display: str = "",
        user_message: str = "",
        include_anti_repetition: bool = True,
        template_name: str = "analysis"
    ) -> str:
        """
        Build analysis prompt from template.
        
        Args:
            persona_instruction: Persona/style instruction
            persona_context: Current persona state context
            history_display: Formatted history string
            user_message: Optional user message
            include_anti_repetition: Include anti-repetition warnings
            template_name: Name of template to use
            
        Returns:
            Complete prompt string
        """
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # Build sections dynamically based on what's provided
        sections_to_include = {}
        
        if persona_instruction:
            sections_to_include['persona'] = template.sections.get('persona', '')
        
        if persona_context:
            sections_to_include['context'] = template.sections.get('context', '')
        
        # Task section is always included
        if 'task' in template.sections:
            sections_to_include['task'] = template.sections['task']
        
        if history_display:
            sections_to_include['history'] = template.sections.get('history', '')
            if include_anti_repetition and 'anti_repetition' in template.sections:
                sections_to_include['anti_repetition'] = template.sections['anti_repetition']
        
        if user_message:
            sections_to_include['user_message'] = template.sections.get('user_message', '')
        
        # Output format is always included
        if 'output_format' in template.sections:
            sections_to_include['output_format'] = template.sections['output_format']
        
        # Render each section
        result = []
        for key, section_template in sections_to_include.items():
            try:
                rendered = section_template.format(
                    persona_instruction=persona_instruction,
                    persona_context=persona_context,
                    history_display=history_display,
                    user_message=user_message
                )
                if rendered.strip():
                    result.append(rendered)
            except KeyError as e:
                logging.warning(f"Missing variable in section {key}: {e}")
                result.append(section_template)
        
        return "\n\n".join(result)
    
    def save_template(self, template: PromptTemplate, filepath: Path):
        """
        Save template to JSON file.
        
        Args:
            template: Template to save
            filepath: Output file path
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)
            logging.info(f"Saved template '{template.name}' to {filepath}")
        except Exception as e:
            logging.error(f"Failed to save template: {e}")
    
    def export_all_templates(self, output_file: Path):
        """
        Export all templates to single JSON file.
        
        Args:
            output_file: Path to output file
        """
        try:
            all_templates = [t.to_dict() for t in self.templates.values()]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_templates, f, ensure_ascii=False, indent=2)
            logging.info(f"Exported {len(all_templates)} templates to {output_file}")
        except Exception as e:
            logging.error(f"Failed to export templates: {e}")
    
    def __repr__(self) -> str:
        """String representation."""
        return f"PromptManager(templates={len(self.templates)}, dir={self.prompts_dir})"

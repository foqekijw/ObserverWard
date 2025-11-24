"""
UI Controller - Single Live Context Manager

This is the heart of the UI system. It manages:
- Single Live context (created once, never destroyed)
- Event loop (non-blocking)
- State transitions
- Screen rendering delegation
"""
from typing import Optional, Any
from rich.console import Console
from rich.live import Live

from .state import UIState, UIContext
from .events import EventDispatcher, Event, EventType
from ..keymap import KeyMap


class UIController:
    """
    Central UI controller with single Live context.
    
    All rendering happens through live.update() - no other screen manipulation.
    """
    
    def __init__(self, console: Console):
        self.console = console
        self.context = UIContext()
        self.dispatcher = EventDispatcher()
        self.live: Optional[Live] = None
        self._running = False
    
    def run(self) -> UIContext:
        """
        Main event loop - runs until state reaches CONFIRMED or CANCELLED
        
        Returns:
            UIContext with results
        """
        import time
        
        # Create single Live context
        self.live = Live(
            console=self.console,
            auto_refresh=False, # Disable background thread
            screen=True,
            transient=False
        )
        
        self._running = True
        needs_redraw = True
        
        with self.live:
            while self._running and self.context.state not in (UIState.CONFIRMED, UIState.CANCELLED):
                loop_start = time.monotonic()
                
                # Render current screen only if needed
                if needs_redraw:
                    renderable = self._render_current_screen()
                    self.live.update(renderable, refresh=True) # Manual refresh
                    needs_redraw = False
                
                # Get event (non-blocking)
                event = self.dispatcher.get_event(timeout=0.0)
                
                if event:
                    self._handle_event(event)
                    needs_redraw = True
                
                # Sleep to maintain ~30 FPS
                elapsed = time.monotonic() - loop_start
                sleep_time = max(0, 0.033 - elapsed)
                time.sleep(sleep_time)
        
        return self.context
    
    def stop(self):
        """Stop the event loop"""
        self._running = False
    
    def _render_current_screen(self):
        """Delegate rendering to appropriate screen"""
        from ..screens import style_selection, settings, number_input, style_manager, style_editor, confirmation, text_input
        
        if self.context.state == UIState.STYLE_SELECTION:
            return style_selection.render(self.context)
        
        elif self.context.state == UIState.STYLE_MANAGER:
            if self.context.style_manager_data:
                return style_manager.render(self.console, self.context.style_manager_data)
            return Text("No style manager data", style="red")
        
        elif self.context.state == UIState.STYLE_EDITOR:
            return style_editor.render(self.context)
        
        elif self.context.state == UIState.CONFIRMATION:
            return confirmation.render(self.context)
        
        elif self.context.state == UIState.SETTINGS:
            return settings.render(self.context)
        
        elif self.context.state == UIState.NUMBER_INPUT:
            return number_input.render(self.context)
            
        elif self.context.state == UIState.TEXT_INPUT:
            return text_input.render(self.context)
        
        else:
            from rich.text import Text
            return Text("Unknown state")
    
    def _handle_event(self, event: Event):
        """Route events to appropriate handlers"""
        if event.type == EventType.KEYBOARD:
            self._handle_keyboard(event.key)
        # TODO: Handle mouse events
    
    def _handle_keyboard(self, key: str):
        """Handle keyboard events based on current state"""
        if self.context.state == UIState.STYLE_SELECTION:
            self._handle_style_selection_keys(key)
        
        elif self.context.state == UIState.STYLE_MANAGER:
            self._handle_style_manager_keys(key)
        
        elif self.context.state == UIState.STYLE_EDITOR:
            self._handle_style_editor_keys(key)
        
        elif self.context.state == UIState.CONFIRMATION:
            self._handle_confirmation_keys(key)
        
        elif self.context.state == UIState.SETTINGS:
            self._handle_settings_keys(key)
        
        elif self.context.state == UIState.NUMBER_INPUT:
            self._handle_number_input_keys(key)
            
        elif self.context.state == UIState.TEXT_INPUT:
            self._handle_text_input_keys(key)

    # ... (existing handlers) ...

    def _handle_text_input_keys(self, key: str):
        """Handle keys in text input screen"""
        data = self.context.text_input_data
        if not data:
            return
            
        if KeyMap.is_enter(key):
            # Confirm message
            self.context.user_message = data.current_value
            self.context.state = UIState.CONFIRMED
            
        elif key == KeyMap.ESC_KEY:
            # Cancel
            self.context.state = UIState.CANCELLED
            
        elif key == KeyMap.BACKSPACE_KEY:
            data.backspace()
            
        elif KeyMap.is_left(key):
            data.move_cursor_left()
            
        elif KeyMap.is_right(key):
            data.move_cursor_right()
            
        elif KeyMap.is_printable(key):
            data.insert_char(key)

    def transition_to_chat(self, history: list = None):
        """Transition directly to chat input"""
        from .state import TextInputData
        
        # Format history for display
        display_history = []
        if history:
            # Take last 5 messages
            for entry in history[-5:]:
                timestamp = entry.get("timestamp", "")
                comment = entry.get("comment", "")
                display_history.append(f"[{timestamp}] AI: {comment}")
        
        self.context.text_input_data = TextInputData(
            prompt="Type your message...",
            history=display_history
        )
        self.context.state = UIState.TEXT_INPUT
    
    def _handle_style_selection_keys(self, key: str):
        """Handle keys in style selection screen"""
        data = self.context.selection_data
        if not data:
            return
        
        if KeyMap.is_up(key):
            data.selected_index = max(0, data.selected_index - 1)
        
        elif KeyMap.is_down(key):
            data.selected_index = min(len(data.items) - 1, data.selected_index + 1)
        
        elif KeyMap.is_enter(key):
            # Confirm selection -> go to number input for interval
            selected = data.get_selected_item()
            if selected:
                self.context.selected_style = selected
                self._transition_to_number_input("Enter interval (seconds)", self.context.selected_interval)
        
        elif KeyMap.is_quit(key):
            self.context.state = UIState.CANCELLED
        
        elif KeyMap.is_settings(key):
            self.context.state = UIState.SETTINGS
        
        elif KeyMap.is_edit(key):
            # Enter style manager
            self._enter_style_manager()
        
        # Direct numeric selection
        elif key in data.items:
            idx = [item[0] for item in data.items].index(key)
            data.selected_index = idx
    
    def _handle_settings_keys(self, key: str):
        """Handle keys in settings screen"""
        data = self.context.settings_data
        if not data or not data.config:
            return
        
        if KeyMap.is_up(key):
            data.selected_index = max(0, data.selected_index - 1)
        
        elif KeyMap.is_down(key):
            data.selected_index = min(len(data.settings) - 1, data.selected_index + 1)
        
        elif KeyMap.is_enter(key):
            # Toggle or edit current setting
            _, name, attr, type_ = data.settings[data.selected_index]
            current = getattr(data.config, attr)
            
            if type_ == bool:
                setattr(data.config, attr, not current)
            elif type_ == int:
                # Transition to number input
                self._transition_to_number_input(f"Enter {name}", current, target_attr=attr)
        
        elif KeyMap.is_quit(key):
            # Back to style selection
            self.context.state = UIState.STYLE_SELECTION
    
    def _handle_number_input_keys(self, key: str):
        """Handle keys in number input screen"""
        data = self.context.number_input_data
        if not data:
            return
        
        if KeyMap.is_digit(key):
            data.append_digit(key)
        
        elif key == KeyMap.BACKSPACE_KEY:
            data.backspace()
        
        elif KeyMap.is_enter(key):
            if data.confirm():
                # Apply result and return to previous screen
                self._apply_number_input_result()
        
        elif key == KeyMap.ESC_KEY:
            # Cancel and return
            self._cancel_number_input()
    
    def _transition_to_number_input(self, prompt: str, default: int, target_attr: Optional[str] = None):
        """Transition to number input screen"""
        from .state import NumberInputData
        
        self.context.number_input_data = NumberInputData(
            prompt=prompt,
            default_value=default
        )
        # Store where to apply the result
        self.context.number_input_data._target_attr = target_attr
        self.context.number_input_data._previous_state = self.context.state
        self.context.state = UIState.NUMBER_INPUT
    
    def _apply_number_input_result(self):
        """Apply number input result and return to previous screen"""
        data = self.context.number_input_data
        if not data or data.result is None:
            return
        
        target_attr = getattr(data, '_target_attr', None)
        previous_state = getattr(data, '_previous_state', UIState.STYLE_SELECTION)
        
        if target_attr:
            # Apply to settings
            if self.context.settings_data and self.context.settings_data.config:
                setattr(self.context.settings_data.config, target_attr, data.result)
            self.context.state = UIState.SETTINGS
        else:
            # It's the interval
            self.context.selected_interval = data.result
            self.context.state = UIState.CONFIRMED
    
    def _cancel_number_input(self):
        """Cancel number input and return to previous screen"""
        data = self.context.number_input_data
        previous_state = getattr(data, '_previous_state', UIState.STYLE_SELECTION) if data else UIState.STYLE_SELECTION
        self.context.state = previous_state
    
    def _reload_style_selection(self):
        """Reload styles from file and update selection data"""
        try:
            # Import here to avoid circular dependency and get fresh data
            import importlib
            import sys
            
            # Reload the commentator_styles module to get updated styles
            if 'commentator_styles' in sys.modules:
                commentator_styles = sys.modules['commentator_styles']
                importlib.reload(commentator_styles)
                list_styles_func = getattr(commentator_styles, 'list_styles', None)
                
                if list_styles_func and self.context.selection_data:
                    # Rebuild menu_styles with key mapping
                    keys = list_styles_func()
                    new_items = []
                    new_mapping = {}
                    
                    for i, k in enumerate(keys, 1):
                        title = k.replace('_', ' ').title()
                        numeric_key = str(i)
                        new_items.append((numeric_key, title))
                        new_mapping[numeric_key] = k  # Map "1" -> "actual_style_name"
                    
                    # Update selection data
                    self.context.selection_data.items = new_items
                    # Update key mapping
                    self.context.style_key_mapping = new_mapping
                    
                    # Keep selected index valid
                    if self.context.selection_data.selected_index >= len(new_items):
                        self.context.selection_data.selected_index = max(0, len(new_items) - 1)
        except Exception as e:
            import logging
            logging.error(f"Failed to reload styles: {e}")
    
    def _enter_style_manager(self):
        """Enter style manager screen"""
        from ...style_persistence import STYLE_MANAGER
        from .state import StyleManagerData
        
        # Load styles and favorites
        styles = STYLE_MANAGER.load_styles()
        favorites = STYLE_MANAGER.load_favorites()
        
        # Sort: favorites first, then alphabetically
        all_names = sorted(styles.keys())
        fav_names = [n for n in all_names if n in favorites]
        other_names = [n for n in all_names if n not in favorites]
        style_names = fav_names + other_names
        
        self.context.style_manager_data = StyleManagerData(
            styles=styles,
            style_names=style_names,
            selected_index=0,
            favorites=favorites
        )
        self.context.state = UIState.STYLE_MANAGER
    
    def _handle_style_manager_keys(self, key: str):
        """Handle keys in style manager screen"""
        data = self.context.style_manager_data
        if not data:
            return
        
        if KeyMap.is_up(key):
            data.selected_index = max(0, data.selected_index - 1)
            data.message = ""
        
        elif KeyMap.is_down(key):
            data.selected_index = min(len(data.style_names) - 1, data.selected_index + 1)
            data.message = ""
        
        elif KeyMap.is_add(key):
            # Add new style
            self._enter_style_editor(is_new=True)
        
        elif KeyMap.is_edit(key):
            # Edit selected style
            if data.style_names:
                style_name = data.style_names[data.selected_index]
                self._enter_style_editor(is_new=False, style_name=style_name)
        
        elif KeyMap.is_copy(key):
            # Copy selected style
            if data.style_names:
                style_name = data.style_names[data.selected_index]
                self._copy_style(style_name)
        
        elif KeyMap.is_favorite(key):
            # Toggle favorite
            if data.style_names:
                style_name = data.style_names[data.selected_index]
                self._toggle_favorite(style_name)
        
        elif KeyMap.is_sort(key):
            # Toggle sort mode
            self._toggle_sort()
        
        elif KeyMap.is_delete(key):
            # Delete selected style - show confirmation first
            if data.style_names:
                style_name = data.style_names[data.selected_index]
                self._show_delete_confirmation(style_name)
        
        elif KeyMap.is_export(key):
            # Export all styles
            self._export_styles()
        
        elif KeyMap.is_import(key):
            # Import styles
            self._import_styles()
        
        elif key == KeyMap.ESC_KEY:
            # Back to style selection - reload styles from file
            self._reload_style_selection()
            self.context.state = UIState.STYLE_SELECTION
    
    def _handle_style_editor_keys(self, key: str):
        """Handle keys in style editor screen"""
        data = self.context.style_editor_data
        if not data:
            return
        
        # Tab to switch fields
        if KeyMap.is_tab(key):
            data.is_editing_name = not data.is_editing_name
            # Reset cursor position when switching
            if data.is_editing_name:
                data.cursor_position = len(data.style_name)
            else:
                data.cursor_position = len(data.content)
            data.error_message = ""
        
        # Enter to save when editing name, or insert newline when editing content
        elif KeyMap.is_enter(key):
            if data.is_editing_name:
                # Save when editing name
                self._save_style_from_editor()
            else:
                # Insert newline when editing content
                data.content = data.content[:data.cursor_position] + '\n' + data.content[data.cursor_position:]
                data.cursor_position += 1
                data.error_message = ""
        
        # ESC to save (changed from cancel)
        elif key == KeyMap.ESC_KEY:
            self._save_style_from_editor()
        
        # Backspace
        elif key == KeyMap.BACKSPACE_KEY:
            if data.is_editing_name:
                if data.cursor_position > 0:
                    data.style_name = data.style_name[:data.cursor_position-1] + data.style_name[data.cursor_position:]
                    data.cursor_position -= 1
            else:
                if data.cursor_position > 0:
                    data.content = data.content[:data.cursor_position-1] + data.content[data.cursor_position:]
                    data.cursor_position -= 1
            data.error_message = ""
        
        # Space handling
        elif key == ' ':
            if data.is_editing_name:
                # Don't allow space in style name
                data.error_message = "Style names cannot contain spaces"
            else:
                # Allow space in content
                data.content = data.content[:data.cursor_position] + ' ' + data.content[data.cursor_position:]
                data.cursor_position += 1
                data.error_message = ""
        
        # Arrow keys for cursor movement
        elif KeyMap.is_left(key):
            data.move_cursor_left()
        
        elif KeyMap.is_right(key):
            data.move_cursor_right()
        
        # Printable characters
        elif KeyMap.is_printable(key):
            data.insert_char(key)
            data.error_message = ""
    
    def _enter_style_editor(self, is_new: bool, style_name: str = ""):
        """Enter style editor screen"""
        from .state import StyleEditorData
        
        if is_new:
            self.context.style_editor_data = StyleEditorData(
                style_name="",
                original_name="",
                content="",
                is_new=True,
                is_editing_name=True
            )
        else:
            # Load existing style
            data = self.context.style_manager_data
            if data and style_name in data.styles:
                style_data = data.styles[style_name]
                content = style_data.get("content", "")
                
                self.context.style_editor_data = StyleEditorData(
                    style_name=style_name,
                    original_name=style_name,
                    content=content,
                    cursor_position=len(style_name),
                    is_new=False,
                    is_editing_name=True
                )
        
        self.context.state = UIState.STYLE_EDITOR
    
    def _save_style_from_editor(self):
        """Save style from editor"""
        from ...style_persistence import STYLE_MANAGER
        
        data = self.context.style_editor_data
        if not data:
            return
        
        # Validate
        error = STYLE_MANAGER.validate_style(data.style_name, data.content)
        if error:
            data.error_message = error
            return
        
        # Get current styles
        manager_data = self.context.style_manager_data
        if not manager_data:
            return
        
        styles = manager_data.styles.copy()
        
        # Remove old style if renaming
        if not data.is_new and data.original_name != data.style_name:
            if data.original_name in styles:
                del styles[data.original_name]
        
        # Add/update style
        styles[data.style_name] = {
            "role": "system",
            "content": data.content
        }
        
        # Save to file
        if STYLE_MANAGER.save_styles(styles):
            # Update manager data
            manager_data.styles = styles
            manager_data.style_names = sorted(styles.keys())
            manager_data.message = f"Successfully saved '{data.style_name}'"
            
            # Find the index of the newly saved style
            try:
                new_index = manager_data.style_names.index(data.style_name)
                manager_data.selected_index = new_index
            except ValueError:
                # Style not found, keep current index
                pass
            
            # Reload style selection to update main menu
            self._reload_style_selection()
            
            # Return to manager
            self.context.state = UIState.STYLE_MANAGER
        else:
            data.error_message = "Failed to save style to file"
    
    def _show_delete_confirmation(self, style_name: str):
        """Show confirmation dialog before deleting style"""
        from .state import ConfirmationData
        
        self.context.confirmation_data = ConfirmationData(
            prompt=f"Delete style '{style_name}'?",
            action_name=style_name,
            previous_state=UIState.STYLE_MANAGER
        )
        self.context.state = UIState.CONFIRMATION
    
    def _handle_confirmation_keys(self, key: str):
        """Handle keys in confirmation dialog"""
        data = self.context.confirmation_data
        if not data:
            return
        
        if key.lower() == 'y':
            # Confirmed - execute deletion
            data.confirmed = True
            self._execute_delete_style(data.action_name)
            self.context.state = data.previous_state
        
        elif key.lower() == 'n' or key == KeyMap.ESC_KEY:
            # Cancelled
            data.confirmed = False
            self.context.state = data.previous_state
    
    def _execute_delete_style(self, style_name: str):
        """Actually delete a style after confirmation"""
        from ...style_persistence import STYLE_MANAGER
        
        data = self.context.style_manager_data
        if not data:
            return
        
        # Remove from dict completely
        styles = data.styles.copy()
        if style_name in styles:
            del styles[style_name]
            
            # Save to file (will filter out deleted styles)
            if STYLE_MANAGER.save_styles(styles):
                # Reload to ensure sync
                data.styles = STYLE_MANAGER.load_styles()
                data.style_names = sorted(data.styles.keys())
                data.message = f"Deleted '{style_name}'"
                # Adjust selected index
                if data.style_names:
                    data.selected_index = min(data.selected_index, len(data.style_names) - 1)
                    data.selected_index = max(0, data.selected_index)
                else:
                    data.selected_index = 0
            else:
                data.message = f"Failed to delete '{style_name}'"
    
    def _copy_style(self, style_name: str):
        """Duplicate a style with _copy suffix"""
        from ...style_persistence import STYLE_MANAGER
        
        data = self.context.style_manager_data
        if not data or style_name not in data.styles:
            return
        
        # Find unique copy name
        base_name = style_name
        copy_num = 1
        new_name = f"{base_name}_copy"
        
        while new_name in data.styles:
            copy_num += 1
            new_name = f"{base_name}_copy_{copy_num}"
        
        # Copy style data
        styles = data.styles.copy()
        styles[new_name] = data.styles[style_name].copy()
        
        # Save
        if STYLE_MANAGER.save_styles(styles):
            # Reload and re-sort
            data.styles = STYLE_MANAGER.load_styles()
            all_names = sorted(data.styles.keys())
            fav_names = [n for n in all_names if n in data.favorites]
            other_names = [n for n in all_names if n not in data.favorites]
            data.style_names = fav_names + other_names
            
            # Select the new copy
            try:
                data.selected_index = data.style_names.index(new_name)
            except ValueError:
                pass
            
            data.message = f"Copied to '{new_name}'"
            self._reload_style_selection()
        else:
            data.message = f"Failed to copy '{style_name}'"
    
    def _toggle_favorite(self, style_name: str):
        """Toggle favorite status of a style"""
        from ...style_persistence import STYLE_MANAGER
        
        data = self.context.style_manager_data
        if not data:
            return
        
        # Toggle favorite
        new_favorites = STYLE_MANAGER.toggle_favorite(style_name, data.favorites)
        
        # Save favorites
        if STYLE_MANAGER.save_favorites(new_favorites):
            data.favorites = new_favorites
            
            # Re-sort with favorites first
            all_names = sorted(data.styles.keys())
            fav_names = [n for n in all_names if n in new_favorites]
            other_names = [n for n in all_names if n not in new_favorites]
            data.style_names = fav_names + other_names
            
            # Maintain selection on the same style
            try:
                data.selected_index = data.style_names.index(style_name)
            except ValueError:
                data.selected_index = 0
            
            status = "★ Starred" if style_name in new_favorites else "☆ Unstarred"
            data.message = f"{status}: '{style_name}'"
        else:
            data.message = "Failed to save favorites"
    
    def _export_styles(self):
        """Export all styles to JSON file"""
        from ...style_persistence import STYLE_MANAGER
        
        data = self.context.style_manager_data
        if not data:
            return
        
        export_path = STYLE_MANAGER.export_styles(data.styles)
        if export_path:
            data.message = f"Exported to {export_path.name}"
        else:
            data.message = "Export failed"
    
    def _import_styles(self):
        """Import styles from latest export file"""
        from ...style_persistence import STYLE_MANAGER
        from pathlib import Path
        
        data = self.context.style_manager_data
        if not data:
            return
        
        # Find latest export file
        exports_dir = STYLE_MANAGER.styles_file.parent / "exports"
        if not exports_dir.exists():
            data.message = "No exports folder found"
            return
        
        export_files = list(exports_dir.glob("styles_export_*.json"))
        if not export_files:
            data.message = "No export files found"
            return
        
        # Get latest file
        latest_export = max(export_files, key=lambda p: p.stat().st_mtime)
        
        # Import
        merged_styles = STYLE_MANAGER.import_styles(latest_export, merge=True)
        if merged_styles:
            # Save merged styles
            if STYLE_MANAGER.save_styles(merged_styles):
                # Reload
                data.styles = STYLE_MANAGER.load_styles()
                all_names = sorted(data.styles.keys())
                fav_names = [n for n in all_names if n in data.favorites]
                other_names = [n for n in all_names if n not in data.favorites]
                data.style_names = fav_names + other_names
                
                data.message = f"Imported from {latest_export.name}"
                self._reload_style_selection()
            else:
                data.message = "Failed to save imported styles"
        else:
            data.message = "Import failed"
    
    def _toggle_sort(self):
        """Toggle sort mode between A-Z and Z-A"""
        data = self.context.style_manager_data
        if not data:
            return
        
        # Toggle sort mode
        if data.sort_mode == "A-Z":
            data.sort_mode = "Z-A"
        else:
            data.sort_mode = "A-Z"
        
        # Re-sort: favorites first, then by mode
        all_names = sorted(data.styles.keys())
        if data.sort_mode == "Z-A":
            all_names.reverse()
        
        fav_names = [n for n in all_names if n in data.favorites]
        other_names = [n for n in all_names if n not in data.favorites]
        data.style_names = fav_names + other_names
        
        # Maintain selection if possible
        if data.selected_index >= len(data.style_names):
            data.selected_index = max(0, len(data.style_names) - 1)
        
        data.message = f"Sorted {data.sort_mode}"

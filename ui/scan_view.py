"""
ScanView component for DeepDel application.

This module provides a TreeView widget for displaying scan results
grouped by risk level with checkbox-like selection.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Dict, List, Optional

from modules.models import ClassificationResult, RiskLevel


class ScanView(ttk.Frame):
    """
    A TreeView-based widget for displaying scan results.

    Features:
    - Grouped by risk level (SAFE, SUGGEST, CAUTION)
    - Checkbox-like visual selection
    - Columns: Name, Size, Source, Risk
    - Event callbacks for selection and check changes
    """

    # Risk level display configuration
    RISK_CONFIG = {
        RiskLevel.SAFE: {
            "icon": "[+]",
            "label": "Safe to Delete",
            "tag": "safe",
            "foreground": "#228B22",  # Forest Green
        },
        RiskLevel.SUGGEST: {
            "icon": "[~]",
            "label": "Suggested Deletion",
            "tag": "suggest",
            "foreground": "#DAA520",  # Goldenrod
        },
        RiskLevel.CAUTION: {
            "icon": "[!]",
            "label": "Handle with Caution",
            "tag": "caution",
            "foreground": "#DC143C",  # Crimson
        },
    }

    def __init__(self, parent: tk.Widget, on_select: Optional[Callable] = None,
                 on_check: Optional[Callable] = None):
        """
        Initialize the ScanView widget.

        Args:
            parent: Parent tkinter widget
            on_select: Callback when an item is selected (receives path)
            on_check: Callback when an item's check state changes (receives path, checked)
        """
        super().__init__(parent)

        self.on_select_callback = on_select
        self.on_check_callback = on_check

        # Internal data storage
        self._results: Dict[str, ClassificationResult] = {}
        self._sizes: Dict[str, int] = {}  # path -> size in bytes
        self._checked_paths: set = set()
        self._tree_items: Dict[str, str] = {}  # path -> tree item id
        self._group_items: Dict[RiskLevel, str] = {}  # risk level -> group item id

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        # Title label
        title_label = ttk.Label(self, text="Scan Results", font=("", 11, "bold"))
        title_label.pack(fill=tk.X, padx=5, pady=(5, 2))

        # Create Treeview with scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbars
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        x_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Treeview
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("name", "size", "source", "risk"),
            show="tree headings",
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set,
            selectmode="browse",
        )

        # Configure columns
        self.tree.heading("#0", text="")  # Checkbox column
        self.tree.heading("name", text="Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("source", text="Source")
        self.tree.heading("risk", text="Risk")

        self.tree.column("#0", width=40, minwidth=40, stretch=False)
        self.tree.column("name", width=200, minwidth=100)
        self.tree.column("size", width=80, minwidth=60, anchor=tk.E)
        self.tree.column("source", width=120, minwidth=80)
        self.tree.column("risk", width=100, minwidth=60)

        self.tree.pack(fill=tk.BOTH, expand=True)

        # Configure scrollbars
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        # Configure tags for risk levels
        self.tree.tag_configure("safe", foreground=self.RISK_CONFIG[RiskLevel.SAFE]["foreground"])
        self.tree.tag_configure("suggest", foreground=self.RISK_CONFIG[RiskLevel.SUGGEST]["foreground"])
        self.tree.tag_configure("caution", foreground=self.RISK_CONFIG[RiskLevel.CAUTION]["foreground"])
        self.tree.tag_configure("group", font=("", 10, "bold"))

        # Bind events
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<space>", self._on_space_key)

    def _on_tree_select(self, event):
        """Handle tree selection event."""
        selection = self.tree.selection()
        if selection and self.on_select_callback:
            item_id = selection[0]
            # Check if this is a result item (not a group)
            for path, stored_id in self._tree_items.items():
                if stored_id == item_id:
                    self.on_select_callback(path)
                    return
            # If it's a group item, clear selection callback
            self.on_select_callback(None)

    def _on_double_click(self, event):
        """Handle double-click to toggle checkbox."""
        item_id = self.tree.identify_row(event.y)
        if item_id:
            self._toggle_item(item_id)

    def _on_space_key(self, event):
        """Handle space key to toggle checkbox."""
        selection = self.tree.selection()
        if selection:
            self._toggle_item(selection[0])

    def _toggle_item(self, item_id: str):
        """Toggle the checked state of an item."""
        # Find the path for this item
        path = None
        for p, stored_id in self._tree_items.items():
            if stored_id == item_id:
                path = p
                break

        if path is None:
            return  # Not a result item

        # Toggle state
        if path in self._checked_paths:
            self._checked_paths.discard(path)
            checked = False
        else:
            self._checked_paths.add(path)
            checked = True

        # Update display
        self._update_item_display(item_id, path, checked)

        # Update group item
        self._update_group_counts()

        # Callback
        if self.on_check_callback:
            self.on_check_callback(path, checked)

    def _update_item_display(self, item_id: str, path: str, checked: bool):
        """Update the display of an item based on its checked state."""
        result = self._results.get(path)
        if not result:
            return

        check_char = "[x]" if checked else "[ ]"
        risk_config = self.RISK_CONFIG[result.risk_level]

        # Get actual size if available
        size_bytes = self._sizes.get(path, 0)
        if size_bytes > 0:
            size_str = self._format_size(size_bytes)
        else:
            size_str = f"{result.confidence * 100:.0f}%"

        # Get folder name from path
        import os
        folder_name = os.path.basename(path) if path else result.source_name

        self.tree.item(
            item_id,
            text=check_char,
            values=(
                folder_name,
                size_str,
                result.source_name,
                risk_config["label"],
            ),
            tags=(risk_config["tag"],),
        )

    def _update_group_counts(self):
        """Update the group labels with checked counts."""
        for risk_level, group_id in self._group_items.items():
            total = sum(
                1 for r in self._results.values() if r.risk_level == risk_level
            )
            checked = sum(
                1 for path, r in self._results.items()
                if r.risk_level == risk_level and path in self._checked_paths
            )
            config = self.RISK_CONFIG[risk_level]
            self.tree.item(
                group_id,
                text=f"{config['icon']} {config['label']} ({checked}/{total})",
            )

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def set_results(self, results: List[ClassificationResult], sizes: Dict[str, int] = None):
        """
        Set the scan results to display.

        Args:
            results: List of ClassificationResult objects to display
            sizes: Optional dict mapping path to size in bytes
        """
        # Clear existing data
        self.clear()

        # Store results and sizes
        for result in results:
            self._results[result.path] = result

        if sizes:
            self._sizes = sizes

        # Create groups for each risk level
        for risk_level in [RiskLevel.SAFE, RiskLevel.SUGGEST, RiskLevel.CAUTION]:
            count = sum(1 for r in results if r.risk_level == risk_level)
            if count > 0:
                config = self.RISK_CONFIG[risk_level]
                group_id = self.tree.insert(
                    "",
                    tk.END,
                    text=f"{config['icon']} {config['label']} (0/{count})",
                    values=("", "", "", ""),
                    tags=("group",),
                    open=True,
                )
                self._group_items[risk_level] = group_id

        # Add items to their respective groups
        for result in results:
            self._add_result_item(result)

    def _add_result_item(self, result: ClassificationResult):
        """Add a single result item to the tree."""
        group_id = self._group_items.get(result.risk_level)
        if not group_id:
            return

        checked = result.selected
        if checked:
            self._checked_paths.add(result.path)

        check_char = "[x]" if checked else "[ ]"
        config = self.RISK_CONFIG[result.risk_level]

        # Get actual size if available, otherwise use confidence as percentage display
        size_bytes = self._sizes.get(result.path, 0)
        if size_bytes > 0:
            size_str = self._format_size(size_bytes)
        else:
            size_str = f"{result.confidence * 100:.0f}%"

        # Get folder name from path
        import os
        folder_name = os.path.basename(result.path) if result.path else result.source_name

        item_id = self.tree.insert(
            group_id,
            tk.END,
            text=check_char,
            values=(
                folder_name,
                size_str,
                result.source_name,
                config["label"],
            ),
            tags=(config["tag"],),
        )
        self._tree_items[result.path] = item_id

    def clear(self):
        """Clear all items from the tree."""
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Clear internal data
        self._results.clear()
        self._sizes.clear()
        self._checked_paths.clear()
        self._tree_items.clear()
        self._group_items.clear()

    def select_all(self):
        """Select all items."""
        for path in self._results:
            if path not in self._checked_paths:
                self._checked_paths.add(path)
                item_id = self._tree_items.get(path)
                if item_id:
                    self._update_item_display(item_id, path, True)

        self._update_group_counts()

    def deselect_all(self):
        """Deselect all items."""
        for path in list(self._checked_paths):
            self._checked_paths.discard(path)
            item_id = self._tree_items.get(path)
            if item_id:
                self._update_item_display(item_id, path, False)

        self._update_group_counts()

    def get_selected_paths(self) -> List[str]:
        """
        Get list of selected (checked) paths.

        Returns:
            List of paths that are checked
        """
        return list(self._checked_paths)

    def get_selected_results(self) -> List[ClassificationResult]:
        """
        Get list of ClassificationResult objects for selected items.

        Returns:
            List of ClassificationResult objects that are checked
        """
        return [
            self._results[path]
            for path in self._checked_paths
            if path in self._results
        ]

    def get_selection_stats(self) -> dict:
        """
        Get statistics about the current selection.

        Returns:
            Dictionary with keys: total, selected, size_bytes
        """
        # Use actual sizes if available, otherwise estimate from confidence
        total_size = 0
        for path in self._checked_paths:
            if path in self._sizes:
                total_size += self._sizes[path]
            elif path in self._results:
                # Estimate size from confidence (1-100 MB range)
                total_size += int(self._results[path].confidence * 10 * 1024 * 1024)

        return {
            "total": len(self._results),
            "selected": len(self._checked_paths),
            "size_bytes": total_size,
        }

    def select_path(self, path: str):
        """
        Programmatically select a specific path.

        Args:
            path: Path to select
        """
        if path in self._tree_items:
            item_id = self._tree_items[path]
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            if self.on_select_callback:
                self.on_select_callback(path)

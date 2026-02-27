"""
DetailPanel component for DeepDel application.

This module provides a panel for displaying detailed information
about a selected scan result item.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional

from modules.models import ClassificationResult, RiskLevel


class DetailPanel(ttk.Frame):
    """
    A panel for displaying detailed information about a selected item.

    Features:
    - Path, source, confidence, risk level display
    - Evidence chain list
    - AI analysis result (if available)
    - Action buttons: Open Directory, Ask AI
    """

    # Risk level display configuration
    RISK_CONFIG = {
        RiskLevel.SAFE: {
            "label": "Safe to Delete",
            "foreground": "#228B22",
            "icon": "[+]",
        },
        RiskLevel.SUGGEST: {
            "label": "Suggested Deletion",
            "foreground": "#DAA520",
            "icon": "[~]",
        },
        RiskLevel.CAUTION: {
            "label": "Handle with Caution",
            "foreground": "#DC143C",
            "icon": "[!]",
        },
    }

    def __init__(self, parent: tk.Widget, on_open_dir: Optional[Callable] = None,
                 on_ask_ai: Optional[Callable] = None):
        """
        Initialize the DetailPanel.

        Args:
            parent: Parent tkinter widget
            on_open_dir: Callback when "Open Directory" is clicked (receives path)
            on_ask_ai: Callback when "Ask AI" is clicked (receives path)
        """
        super().__init__(parent)

        self.on_open_dir_callback = on_open_dir
        self.on_ask_ai_callback = on_ask_ai
        self._current_result: Optional[ClassificationResult] = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI components."""
        # Title label
        title_label = ttk.Label(self, text="Details", font=("", 11, "bold"))
        title_label.pack(fill=tk.X, padx=5, pady=(5, 2))

        # Main frame with scrollbar
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create scrollable text widget
        self._create_scrollable_text(main_frame)

        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        # Open Directory button
        self.btn_open_dir = ttk.Button(
            button_frame,
            text="Open Directory",
            command=self._on_open_dir,
            state=tk.DISABLED,
        )
        self.btn_open_dir.pack(side=tk.LEFT, padx=(0, 5))

        # Ask AI button
        self.btn_ask_ai = ttk.Button(
            button_frame,
            text="Ask AI",
            command=self._on_ask_ai,
            state=tk.DISABLED,
        )
        self.btn_ask_ai.pack(side=tk.LEFT)

        # Initially show placeholder
        self._show_placeholder()

    def _create_scrollable_text(self, parent: tk.Widget):
        """Create a scrollable text widget for displaying details."""
        # Scrollbar
        y_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget
        self.text = tk.Text(
            parent,
            wrap=tk.WORD,
            state=tk.DISABLED,
            yscrollcommand=y_scroll.set,
            font=("Consolas", 10),
            background="#f5f5f5",
            relief=tk.FLAT,
        )
        self.text.pack(fill=tk.BOTH, expand=True)

        # Configure scrollbar
        y_scroll.config(command=self.text.yview)

        # Configure tags for formatting
        self.text.tag_configure("header", font=("Consolas", 10, "bold"))
        self.text.tag_configure("label", font=("Consolas", 10, "bold"))
        self.text.tag_configure("safe", foreground="#228B22")
        self.text.tag_configure("suggest", foreground="#DAA520")
        self.text.tag_configure("caution", foreground="#DC143C")
        self.text.tag_configure("evidence", foreground="#666666")
        self.text.tag_configure("ai_header", font=("Consolas", 10, "bold"),
                                foreground="#4169E1")
        self.text.tag_configure("ai_result", foreground="#4169E1")

    def _show_placeholder(self):
        """Show placeholder text when no item is selected."""
        self._set_text("Select an item from the scan results to view details.")

    def _set_text(self, text: str, tags: tuple = ()):
        """Set the text widget content."""
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        if tags:
            self.text.insert(tk.END, text, tags)
        else:
            self.text.insert(tk.END, text)
        self.text.config(state=tk.DISABLED)

    def _clear_text(self):
        """Clear the text widget."""
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        self.text.config(state=tk.DISABLED)

    def _append_text(self, text: str, tags: tuple = ()):
        """Append text to the text widget."""
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, text, tags)
        self.text.config(state=tk.DISABLED)

    def set_result(self, result: Optional[ClassificationResult]):
        """
        Display details for a ClassificationResult.

        Args:
            result: ClassificationResult to display, or None to clear
        """
        self._current_result = result

        if result is None:
            self._show_placeholder()
            self.btn_open_dir.config(state=tk.DISABLED)
            self.btn_ask_ai.config(state=tk.DISABLED)
            return

        # Enable buttons
        self.btn_open_dir.config(state=tk.NORMAL)
        self.btn_ask_ai.config(state=tk.NORMAL)

        # Build the detail view
        self._clear_text()
        self._build_detail_view(result)

    def _build_detail_view(self, result: ClassificationResult):
        """Build the detailed view for a result."""
        # Path section
        self._append_text("Path:\n", ("label",))
        self._append_text(f"  {result.path}\n\n")

        # Source section
        self._append_text("Source:\n", ("label",))
        self._append_text(f"  {result.source_name}\n\n")

        # Confidence section
        self._append_text("Confidence:\n", ("label",))
        confidence_pct = result.confidence * 100
        self._append_text(f"  {confidence_pct:.1f}%\n\n")

        # Risk Level section
        self._append_text("Risk Level:\n", ("label",))
        risk_config = self.RISK_CONFIG[result.risk_level]
        self._append_text(f"  {risk_config['icon']} {risk_config['label']}\n\n",
                         (risk_config['tag'],))

        # Evidence Chain section
        if result.evidence_chain:
            self._append_text("Evidence Chain:\n", ("label",))
            for evidence in result.evidence_chain:
                self._append_text(f"  * {evidence}\n", ("evidence",))
            self._append_text("\n")

        # AI Analysis section (if available)
        if result.ai_result:
            self._append_text("=" * 40 + "\n", ("ai_result",))
            self._append_text("AI Analysis:\n", ("ai_header",))
            self._append_text(f"  Suggestion: {result.ai_result.suggestion}\n", ("ai_result",))
            self._append_text(f"  Confidence: {result.ai_result.confidence * 100:.1f}%\n", ("ai_result",))
            self._append_text(f"\n  Reason:\n", ("ai_result",))
            self._append_text(f"    {result.ai_result.reason}\n", ("ai_result",))

            if result.ai_result.risk_points:
                self._append_text(f"\n  Risk Points:\n", ("ai_result",))
                for risk in result.ai_result.risk_points:
                    self._append_text(f"    - {risk}\n", ("ai_result",))

    def _on_open_dir(self):
        """Handle Open Directory button click."""
        if self._current_result and self.on_open_dir_callback:
            self.on_open_dir_callback(self._current_result.path)
        elif self._current_result:
            # Default behavior: open with file manager
            self._open_in_explorer(self._current_result.path)

    def _on_ask_ai(self):
        """Handle Ask AI button click."""
        if self._current_result and self.on_ask_ai_callback:
            self.on_ask_ai_callback(self._current_result.path)

    def _open_in_explorer(self, path: str):
        """Open a path in the system file explorer."""
        if os.path.exists(path):
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["explorer", path])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", path])
            else:  # Linux
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showwarning("Path Not Found", f"The path does not exist:\n{path}")

    def update_ai_result(self, result: ClassificationResult):
        """
        Update the display with new AI analysis result.

        Args:
            result: ClassificationResult with updated ai_result
        """
        if self._current_result and self._current_result.path == result.path:
            self._current_result = result
            self._clear_text()
            self._build_detail_view(result)

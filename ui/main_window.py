"""
MainWindow for DeepDel application.

This module provides the main application window with toolbar, scan view,
detail panel, and action buttons.
"""

import os
import threading
from tkinter import ttk, messagebox
from typing import Dict, List, Optional

import tkinter as tk

from config import Config, get_config, reload_config
from modules.models import (
    AIAnalysisResult,
    ClassificationResult,
    IdentificationResult,
    ProgramStatus,
    RiskLevel,
    ScanResult,
)
from modules.scanner import Scanner
from modules.identifier import Identifier
from modules.classifier import Classifier
from modules.cleaner import Cleaner
from modules.ai_analyzer import AIAnalyzer
from modules.learner import Learner
from ui.scan_view import ScanView
from ui.settings_dialog import show_settings_dialog
from ui.detail_panel import DetailPanel


class MainWindow:
    """
    Main application window for DeepDel.

    Features:
    - Top toolbar with scan controls
    - Left panel: ScanView (scan results tree)
    - Right panel: DetailPanel (selected item details)
    - Bottom: Statistics and action buttons
    - Threading for non-blocking scans
    - Real-time progress updates
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the MainWindow.

        Args:
            config: Configuration object. If None, uses get_config().
        """
        self.config = config or get_config()

        # Create main window
        self.root = tk.Tk()
        self.root.title("DeepDel - 深度清理工具")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # Initialize modules
        self.scanner = Scanner(self.config)
        self.identifier = Identifier(rules_dir="rules", db_path="data/learner.db")
        self.learner = self.identifier.learner  # Shared learner instance

        # Initialize AI analyzer if enabled
        self.ai_analyzer: Optional[AIAnalyzer] = None
        if self.config.ai_enabled:
            try:
                self.ai_analyzer = AIAnalyzer(self.config)
            except Exception:
                pass  # AI analyzer is optional

        # Initialize classifier with optional AI analyzer
        self.classifier = Classifier(self.config, ai_analyzer=self.ai_analyzer)
        self.cleaner = Cleaner(self.config)

        # State variables
        self._scan_thread: Optional[threading.Thread] = None
        self._is_scanning = False
        self._scan_results: List[ScanResult] = []
        self._classified_results: Dict[str, ClassificationResult] = {}
        self._total_scanned = 0
        self._total_size = 0

        # Build UI
        self._setup_styles()
        self._build_ui()
        self._setup_close_handler()

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()

        # Configure button styles
        style.configure("Toolbar.TButton", padding=(10, 5))
        style.configure("Action.TButton", padding=(15, 5))

        # Configure frame styles
        style.configure("Toolbar.TFrame", background="#f0f0f0")
        style.configure("Status.TFrame", background="#e0e0e0")

    def _build_ui(self):
        """Build the main UI layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top toolbar
        self._build_toolbar(main_frame)

        # Middle section (left panel + right panel)
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel - Scan View
        left_frame = ttk.LabelFrame(middle_frame, text="扫描结果")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))

        self.scan_view = ScanView(
            left_frame,
            on_select=self._on_item_selected,
            on_check=self._on_item_checked,
        )
        self.scan_view.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Right panel - Detail Panel
        right_frame = ttk.LabelFrame(middle_frame, text="详细信息")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))

        self.detail_panel = DetailPanel(
            right_frame,
            on_open_dir=self._on_open_directory,
            on_ask_ai=self._on_ask_ai,
        )
        self.detail_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bottom section
        self._build_bottom_panel(main_frame)

    def _build_toolbar(self, parent: tk.Widget):
        """Build the top toolbar."""
        toolbar_frame = ttk.Frame(parent, style="Toolbar.TFrame")
        toolbar_frame.pack(fill=tk.X, padx=5, pady=5)

        # Left side - Action buttons
        button_frame = ttk.Frame(toolbar_frame)
        button_frame.pack(side=tk.LEFT)

        self.btn_start = ttk.Button(
            button_frame,
            text="开始扫描",
            style="Toolbar.TButton",
            command=self._start_scan,
        )
        self.btn_start.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_stop = ttk.Button(
            button_frame,
            text="停止",
            style="Toolbar.TButton",
            command=self._stop_scan,
            state=tk.DISABLED,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_settings = ttk.Button(
            button_frame,
            text="扫描设置",
            style="Toolbar.TButton",
            command=self._open_settings,
        )
        self.btn_settings.pack(side=tk.LEFT)

        # Right side - Progress
        progress_frame = ttk.Frame(toolbar_frame)
        progress_frame.pack(side=tk.RIGHT)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=200,
            mode="determinate",
        )
        self.progress_bar.pack(side=tk.LEFT, padx=(0, 5))

        self.status_label = ttk.Label(progress_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT)

    def _build_bottom_panel(self, parent: tk.Widget):
        """Build the bottom panel with statistics and action buttons."""
        bottom_frame = ttk.Frame(parent, style="Status.TFrame")
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)

        # Left side - Statistics
        stats_frame = ttk.Frame(bottom_frame)
        stats_frame.pack(side=tk.LEFT, padx=10, pady=5)

        self.stats_label = ttk.Label(
            stats_frame,
            text="已选中: 0 项 | 可释放: 0 B",
        )
        self.stats_label.pack(side=tk.LEFT)

        # Right side - Action buttons
        action_frame = ttk.Frame(bottom_frame)
        action_frame.pack(side=tk.RIGHT, padx=10, pady=5)

        self.btn_select_all = ttk.Button(
            action_frame,
            text="全选",
            style="Action.TButton",
            command=self._select_all,
        )
        self.btn_select_all.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_deselect_all = ttk.Button(
            action_frame,
            text="全不选",
            style="Action.TButton",
            command=self._deselect_all,
        )
        self.btn_deselect_all.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_delete = ttk.Button(
            action_frame,
            text="删除选中",
            style="Action.TButton",
            command=self._delete_selected,
        )
        self.btn_delete.pack(side=tk.LEFT)

    def _setup_close_handler(self):
        """Set up window close handler."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        """Handle window close event."""
        if self._is_scanning:
            if messagebox.askyesno(
                "扫描进行中",
                "正在扫描中，确定要停止扫描并退出吗？",
            ):
                self.scanner.stop()
                self.root.destroy()
        else:
            self.root.destroy()

    # ==================== Scan Operations ====================

    def _start_scan(self):
        """Start the scan operation in a background thread."""
        if self._is_scanning:
            return

        # Clear previous results
        self.scan_view.clear()
        self._scan_results.clear()
        self._classified_results.clear()
        self._total_scanned = 0
        self._total_size = 0

        # Update UI state
        self._set_scanning_state(True)
        self._update_status("正在扫描...")

        # Start scan in background thread
        self._scan_thread = threading.Thread(
            target=self._run_scan,
            daemon=True,
        )
        self._scan_thread.start()

    def _run_scan(self):
        """Run the scan operation (called in background thread)."""
        try:
            # Get expanded scan paths
            scan_paths = self.config.get_expanded_scan_paths()

            if not scan_paths:
                self.root.after(0, lambda: self._update_status("未配置扫描路径"))
                self.root.after(0, lambda: self._set_scanning_state(False))
                return

            total_paths = len(scan_paths)
            for idx, path in enumerate(scan_paths):
                if not self._is_scanning:
                    break

                # Update progress
                progress = (idx / total_paths) * 100
                self.root.after(0, lambda p=progress: self._update_progress(p))
                self.root.after(
                    0,
                    lambda path=path: self._update_status(f"正在扫描: {path}"),
                )

                # Scan the path
                for result in self.scanner.scan_path(path):
                    if not self._is_scanning:
                        break

                    self._scan_results.append(result)
                    self._total_scanned += 1
                    self._total_size += result.size_bytes

                    # Identify and classify the result using the pipeline
                    classified = self._identify_and_classify(result)
                    self._classified_results[result.path] = classified

                    # Update UI on main thread
                    self.root.after(
                        0,
                        lambda r=classified: self._add_scan_result(r),
                    )

            # Scan complete
            self.root.after(0, self._scan_complete)

        except Exception as e:
            self.root.after(0, lambda: self._handle_scan_error(str(e)))

    def _identify_and_classify(self, scan_result: ScanResult) -> ClassificationResult:
        """
        Identify and classify a scan result using the full pipeline.

        Args:
            scan_result: The scan result to process.

        Returns:
            ClassificationResult with full identification and classification.
        """
        # Step 1: Identify the source
        id_result = self.identifier.identify(scan_result)

        # Step 2: Classify based on identification and AI analysis
        classified = self.classifier.classify(scan_result, id_result)

        return classified

    def _add_scan_result(self, result: ClassificationResult):
        """Add a scan result to the view (called on main thread)."""
        # Get the size for this result
        size_bytes = 0
        for sr in self._scan_results:
            if sr.path == result.path:
                size_bytes = sr.size_bytes
                break

        # Add to scan view
        self.scan_view.add_result(result, size_bytes)
        self._update_statistics()

    def _scan_complete(self):
        """Handle scan completion."""
        self._set_scanning_state(False)
        self._update_progress(100)
        self._update_status(f"扫描完成: 发现 {self._total_scanned} 个文件夹")

        # Build size dict from scan results
        sizes = {sr.path: sr.size_bytes for sr in self._scan_results}

        # Update scan view with all results and sizes
        results = list(self._classified_results.values())
        self.scan_view.set_results(results, sizes)

        # Update statistics
        self._update_statistics()

    def _handle_scan_error(self, error: str):
        """Handle scan error."""
        self._set_scanning_state(False)
        self._update_status(f"错误: {error}")
        messagebox.showerror("扫描错误", f"扫描过程中发生错误:\n{error}")

    def _stop_scan(self):
        """Stop the current scan operation."""
        if self._is_scanning:
            self.scanner.stop()
            self._update_status("正在停止扫描...")

    def _set_scanning_state(self, is_scanning: bool):
        """Update UI state for scanning/not scanning."""
        self._is_scanning = is_scanning

        if is_scanning:
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            self.btn_settings.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)
        else:
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.btn_settings.config(state=tk.NORMAL)
            self.btn_delete.config(state=tk.NORMAL)

    # ==================== UI Update Methods ====================

    def _update_progress(self, value: float):
        """Update the progress bar."""
        self.progress_var.set(value)

    def _update_status(self, message: str):
        """Update the status label."""
        self.status_label.config(text=message)

    def _update_statistics(self):
        """Update the statistics display."""
        stats = self.scan_view.get_selection_stats()

        # Format size
        size = stats["size_bytes"]
        if size < 1024:
            size_str = f"{size} B"
        elif size < 1024 * 1024:
            size_str = f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{size / (1024 * 1024 * 1024):.2f} GB"

        self.stats_label.config(
            text=f"已选中: {stats['selected']} / {stats['total']} 项 | "
                 f"可释放: {size_str}"
        )

    # ==================== Event Handlers ====================

    def _on_item_selected(self, path: Optional[str]):
        """Handle item selection in scan view."""
        if path and path in self._classified_results:
            self.detail_panel.set_result(self._classified_results[path])
        else:
            self.detail_panel.set_result(None)

    def _on_item_checked(self, path: str, checked: bool):
        """Handle item check state change."""
        if path in self._classified_results:
            self._classified_results[path].selected = checked
        self._update_statistics()

    def _on_open_directory(self, path: str):
        """Handle open directory request."""
        if os.path.exists(path):
            import subprocess
            import platform

            if platform.system() == "Windows":
                subprocess.run(["explorer", path])
            elif platform.system() == "Darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
        else:
            messagebox.showwarning("未找到", f"路径不存在:\n{path}")

    def _on_ask_ai(self, path: str):
        """Handle ask AI request."""
        if not self.ai_analyzer:
            messagebox.showinfo(
                "AI 不可用",
                "AI 分析未启用或未配置。\n"
                "请检查您的设置。",
            )
            return

        # Find the scan result for this path
        scan_result = None
        for sr in self._scan_results:
            if sr.path == path:
                scan_result = sr
                break

        if not scan_result:
            messagebox.showwarning("未找到", "未找到此路径的扫描结果。")
            return

        # Get current classification
        classified = self._classified_results.get(path)
        if not classified:
            messagebox.showwarning("未找到", "未找到此路径的分类结果。")
            return

        # Run AI analysis in background
        self._update_status("正在 AI 分析...")

        def run_ai_analysis():
            try:
                # Get identification result info
                id_result = self.identifier.identify(scan_result)

                # Run AI analysis
                ai_result = self.ai_analyzer.analyze(
                    scan_result,
                    source_name=id_result.source_name,
                    program_status=id_result.program_status.value if id_result.program_status else None,
                    evidence_chain=id_result.evidence_chain,
                )

                if ai_result:
                    # Update classification with AI result
                    classified.ai_result = ai_result

                    # Update UI on main thread
                    self.root.after(0, lambda: self._ai_analysis_complete(path, ai_result))
                else:
                    self.root.after(0, lambda: self._ai_analysis_failed("AI 未返回结果"))

            except Exception as e:
                self.root.after(0, lambda: self._ai_analysis_failed(str(e)))

        thread = threading.Thread(target=run_ai_analysis, daemon=True)
        thread.start()

    def _ai_analysis_complete(self, path: str, ai_result: AIAnalysisResult):
        """Handle AI analysis completion."""
        self._update_status("AI 分析完成")

        # Update the detail panel if this path is selected
        if path in self._classified_results:
            self.detail_panel.update_ai_result(self._classified_results[path])

        suggestion_text = {
            "can_delete": "可以删除",
            "caution": "需要谨慎",
            "keep": "建议保留"
        }.get(ai_result.suggestion, ai_result.suggestion)

        messagebox.showinfo(
            "AI 分析完成",
            f"AI 建议: {suggestion_text}\n"
            f"置信度: {ai_result.confidence * 100:.1f}%\n\n"
            f"理由: {ai_result.reason}",
        )

    def _ai_analysis_failed(self, error: str):
        """Handle AI analysis failure."""
        self._update_status("AI 分析失败")
        messagebox.showwarning("AI 分析失败", f"无法完成 AI 分析:\n{error}")

    def _select_all(self):
        """Select all items in the scan view."""
        self.scan_view.select_all()
        # Update all classification results
        for path in self._classified_results:
            self._classified_results[path].selected = True
        self._update_statistics()

    def _deselect_all(self):
        """Deselect all items in the scan view."""
        self.scan_view.deselect_all()
        # Update all classification results
        for path in self._classified_results:
            self._classified_results[path].selected = False
        self._update_statistics()

    def _delete_selected(self):
        """Delete selected items after confirmation."""
        selected_results = self.scan_view.get_selected_results()

        if not selected_results:
            messagebox.showinfo("未选择", "请选择要删除的项目。")
            return

        # Calculate total size
        total_size = sum(r.confidence * 1024 * 1024 for r in selected_results)  # Mock size

        # Format size for display
        if total_size < 1024 * 1024:
            size_str = f"{total_size / 1024:.1f} KB"
        elif total_size < 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.1f} MB"
        else:
            size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"

        # Confirm deletion
        message = (
            f"确定要删除 {len(selected_results)} 个项目吗？\n\n"
            f"可释放空间: {size_str}\n\n"
            f"此操作无法撤销。"
        )

        if not messagebox.askyesno("确认删除", message):
            return

        # Perform deletion
        self._perform_deletion(selected_results)

    def _perform_deletion(self, results: List[ClassificationResult]):
        """Perform the actual deletion of selected items."""
        deleted_count = 0
        failed_count = 0
        failed_paths = []

        for result in results:
            try:
                if os.path.exists(result.path):
                    # Use cleaner to delete
                    success = self.cleaner.delete_direct(result.path)
                    if success:
                        deleted_count += 1
                        # Remove from results
                        if result.path in self._classified_results:
                            del self._classified_results[result.path]
                    else:
                        failed_count += 1
                        failed_paths.append(result.path)
                else:
                    failed_count += 1
                    failed_paths.append(f"{result.path} (未找到)")
            except Exception as e:
                failed_count += 1
                failed_paths.append(f"{result.path} ({str(e)})")

        # Update scan view
        self.scan_view.set_results(list(self._classified_results.values()))
        self._update_statistics()

        # Show result
        if failed_count > 0:
            messagebox.showwarning(
                "删除完成",
                f"已删除: {deleted_count}\n失败: {failed_count}\n\n"
                f"失败路径:\n" + "\n".join(failed_paths[:5]),
            )
        else:
            messagebox.showinfo(
                "删除完成",
                f"成功删除 {deleted_count} 个项目。",
            )

        # Record decisions to learner (in real implementation)
        self._record_decisions(results, deleted_count > 0)

    def _record_decisions(self, results: List[ClassificationResult], success: bool):
        """
        Record user decisions to the learner module.

        Args:
            results: List of ClassificationResult objects that were processed.
            success: Whether the deletion was successful.
        """
        if not self.learner:
            return

        for result in results:
            try:
                # Find the corresponding scan result
                scan_result = None
                for sr in self._scan_results:
                    if sr.path == result.path:
                        scan_result = sr
                        break

                if not scan_result:
                    continue

                # Determine user decision
                user_decision = "deleted" if result.selected and success else "kept"

                # Get identification info for program status
                id_result = self.identifier.identify(scan_result)

                # Record the decision
                self.learner.record_decision(
                    scan_result=scan_result,
                    source_name=result.source_name,
                    program_status=id_result.program_status if id_result else ProgramStatus.UNKNOWN,
                    ai_suggestion=result.ai_result.suggestion if result.ai_result else None,
                    risk_level=result.risk_level,
                    user_decision=user_decision,
                    ai_confidence=result.ai_result.confidence if result.ai_result else None,
                )

            except Exception:
                # Silently handle recording errors
                pass

    def _open_settings(self):
        """Open the settings dialog."""
        def on_save():
            """Called when settings are saved."""
            # Save to file
            try:
                self.config.save_to_file("config.yaml")
            except Exception as e:
                print(f"Warning: Could not save config: {e}")

        show_settings_dialog(self.root, self.config, on_save)

    def run(self):
        """Start the main application loop."""
        self.root.mainloop()


def main():
    """Main entry point for the application."""
    # Load configuration
    config = get_config()

    # Try to load from config file if it exists
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    if os.path.exists(config_path):
        try:
            config.load_from_file(config_path)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")

    # Create and run main window
    app = MainWindow(config)
    app.run()


if __name__ == "__main__":
    main()

"""
Settings Dialog for DeepDel application.

This module provides a dialog for configuring application settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, List, Callable

from config import Config


class SettingsDialog(tk.Toplevel):
    """
    Settings dialog for configuring DeepDel.

    Categories:
    - Scan Settings: Paths, min size, exclude patterns
    - AI Settings: Enable/disable, model, confidence threshold
    - Delete Settings: Recycle bin, restore point
    - Performance: Max workers
    """

    def __init__(self, parent: tk.Widget, config: Config, on_save: Optional[Callable] = None):
        """
        Initialize the settings dialog.

        Args:
            parent: Parent widget
            config: Configuration object to edit
            on_save: Callback when settings are saved
        """
        super().__init__(parent)

        self.config = config
        self.on_save = on_save
        self.result = False

        self.title("设置 - DeepDel")
        self.geometry("500x550")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - 550) // 2
        self.geometry(f"+{x}+{y}")

        self._create_widgets()

    def _create_widgets(self):
        """Create all widgets."""
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create tabs
        self._create_scan_tab()
        self._create_ai_tab()
        self._create_delete_tab()
        self._create_performance_tab()

        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="确定", command=self._on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self._on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="应用", command=self._on_apply).pack(side=tk.RIGHT, padx=5)

        # Bind Escape to cancel
        self.bind("<Escape>", lambda e: self._on_cancel())

    def _create_scan_tab(self):
        """Create scan settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="扫描设置")

        # Scan paths
        ttk.Label(frame, text="扫描路径:", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="每行一个路径，支持环境变量如 %TEMP%", foreground="gray").pack(anchor=tk.W)

        paths_frame = ttk.Frame(frame)
        paths_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.paths_text = tk.Text(paths_frame, height=6, width=50)
        self.paths_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(paths_frame, orient=tk.VERTICAL, command=self.paths_text.yview)
        self.paths_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Load paths
        for path in self.config.scan_paths:
            self.paths_text.insert(tk.END, path + "\n")

        # Exclude patterns
        ttk.Label(frame, text="排除模式:", font=("", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(frame, text="支持通配符，如 *.git, *.svn", foreground="gray").pack(anchor=tk.W)

        exclude_frame = ttk.Frame(frame)
        exclude_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.exclude_text = tk.Text(exclude_frame, height=4, width=50)
        self.exclude_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        exclude_scroll = ttk.Scrollbar(exclude_frame, orient=tk.VERTICAL, command=self.exclude_text.yview)
        self.exclude_text.config(yscrollcommand=exclude_scroll.set)
        exclude_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for pattern in self.config.scan_exclude:
            self.exclude_text.insert(tk.END, pattern + "\n")

        # Min size
        size_frame = ttk.Frame(frame)
        size_frame.pack(fill=tk.X, pady=10)

        ttk.Label(size_frame, text="最小文件大小 (MB):").pack(side=tk.LEFT)
        self.min_size_var = tk.StringVar(value=str(self.config.scan_min_size_mb))
        ttk.Entry(size_frame, textvariable=self.min_size_var, width=10).pack(side=tk.LEFT, padx=5)

    def _create_ai_tab(self):
        """Create AI settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="AI 设置")

        # Enable AI
        self.ai_enabled_var = tk.BooleanVar(value=self.config.ai_enabled)
        ttk.Checkbutton(frame, text="启用 AI 分析", variable=self.ai_enabled_var).pack(anchor=tk.W)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # AI Settings frame
        ai_frame = ttk.LabelFrame(frame, text="AI 配置", padding=10)
        ai_frame.pack(fill=tk.X, pady=5)

        # Model
        ttk.Label(ai_frame, text="模型:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ai_model_var = tk.StringVar(value=self.config.ai_model)
        model_combo = ttk.Combobox(ai_frame, textvariable=self.ai_model_var, width=25)
        model_combo['values'] = ('glm-4-flash', 'glm-4', 'glm-4-plus')
        model_combo.grid(row=0, column=1, sticky=tk.W, pady=2, padx=5)

        # Trigger confidence
        ttk.Label(ai_frame, text="触发阈值:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Label(ai_frame, text="当置信度低于此值时调用 AI").grid(row=1, column=1, sticky=tk.W)

        conf_frame = ttk.Frame(ai_frame)
        conf_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)

        self.ai_confidence_var = tk.DoubleVar(value=self.config.ai_trigger_confidence)
        ttk.Scale(conf_frame, from_=0.0, to=1.0, variable=self.ai_confidence_var,
                  orient=tk.HORIZONTAL, length=200).pack(side=tk.LEFT)
        self.conf_label = ttk.Label(conf_frame, text=f"{self.config.ai_trigger_confidence:.2f}")
        self.conf_label.pack(side=tk.LEFT, padx=5)

        def update_conf_label(*args):
            self.conf_label.config(text=f"{self.ai_confidence_var.get():.2f}")
        self.ai_confidence_var.trace('w', update_conf_label)

        # Timeout
        ttk.Label(ai_frame, text="超时时间 (秒):").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.ai_timeout_var = tk.StringVar(value=str(self.config.ai_timeout))
        ttk.Entry(ai_frame, textvariable=self.ai_timeout_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=2, padx=5)

        # API Key info
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(frame, text="API Key 从环境变量 GLM_API_KEY 读取", foreground="gray").pack(anchor=tk.W)

    def _create_delete_tab(self):
        """Create delete settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="删除设置")

        # Recycle bin
        self.use_recycle_bin_var = tk.BooleanVar(value=self.config.delete_use_recycle_bin)
        ttk.Checkbutton(
            frame,
            text="使用回收站",
            variable=self.use_recycle_bin_var
        ).pack(anchor=tk.W, pady=5)

        ttk.Label(
            frame,
            text="删除的文件将移动到回收站，可以恢复",
            foreground="gray"
        ).pack(anchor=tk.W, padx=20)

        # Restore point
        self.create_restore_point_var = tk.BooleanVar(value=self.config.delete_create_restore_point)
        ttk.Checkbutton(
            frame,
            text="删除前创建还原点",
            variable=self.create_restore_point_var
        ).pack(anchor=tk.W, pady=(15, 5))

        ttk.Label(
            frame,
            text="注意: 仅在 Windows 上有效，需要管理员权限",
            foreground="gray"
        ).pack(anchor=tk.W, padx=20)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Safety info
        ttk.Label(frame, text="安全提示:", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(
            frame,
            text="• 绿色标记的文件夹可以安全删除\n"
                 "• 黄色标记的文件夹建议删除\n"
                 "• 红色标记的文件夹需要谨慎处理",
            justify=tk.LEFT
        ).pack(anchor=tk.W, padx=10, pady=5)

    def _create_performance_tab(self):
        """Create performance settings tab."""
        frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(frame, text="性能")

        # Max workers
        worker_frame = ttk.Frame(frame)
        worker_frame.pack(fill=tk.X, pady=5)

        ttk.Label(worker_frame, text="扫描线程数:").pack(side=tk.LEFT)
        self.max_workers_var = tk.StringVar(value=str(self.config.performance_max_workers))
        ttk.Entry(worker_frame, textvariable=self.max_workers_var, width=5).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            frame,
            text="增加线程数可以加快扫描速度，但会占用更多系统资源",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)

        # Clear learning data
        ttk.Label(frame, text="学习数据:", font=("", 10, "bold")).pack(anchor=tk.W)

        clear_frame = ttk.Frame(frame)
        clear_frame.pack(fill=tk.X, pady=5)

        ttk.Button(clear_frame, text="清除所有学习数据", command=self._clear_learning_data).pack(side=tk.LEFT)

        ttk.Label(
            frame,
            text="清除学习数据将重置所有用户决策记录",
            foreground="gray"
        ).pack(anchor=tk.W, pady=5)

    def _clear_learning_data(self):
        """Clear all learning data."""
        if messagebox.askyesno(
            "确认",
            "确定要清除所有学习数据吗？\n\n这将重置所有用户决策记录，无法恢复。",
            parent=self
        ):
            try:
                from modules.learner import Learner
                learner = Learner()
                learner.clear_all_decisions()
                messagebox.showinfo("完成", "学习数据已清除", parent=self)
            except Exception as e:
                messagebox.showerror("错误", f"清除失败: {e}", parent=self)

    def _get_scan_paths(self) -> List[str]:
        """Get scan paths from text widget."""
        text = self.paths_text.get("1.0", tk.END).strip()
        paths = [p.strip() for p in text.split("\n") if p.strip()]
        return paths

    def _get_exclude_patterns(self) -> List[str]:
        """Get exclude patterns from text widget."""
        text = self.exclude_text.get("1.0", tk.END).strip()
        patterns = [p.strip() for p in text.split("\n") if p.strip()]
        return patterns

    def _apply_settings(self) -> bool:
        """Apply settings to config."""
        try:
            # Scan settings
            self.config.scan_paths = self._get_scan_paths()
            self.config.scan_exclude = self._get_exclude_patterns()
            self.config.scan_min_size_mb = int(float(self.min_size_var.get()))

            # AI settings
            self.config.ai_enabled = self.ai_enabled_var.get()
            self.config.ai_model = self.ai_model_var.get()
            self.config.ai_trigger_confidence = float(self.ai_confidence_var.get())
            self.config.ai_timeout = int(float(self.ai_timeout_var.get()))

            # Delete settings
            self.config.delete_use_recycle_bin = self.use_recycle_bin_var.get()
            self.config.delete_create_restore_point = self.create_restore_point_var.get()

            # Performance settings
            self.config.performance_max_workers = int(float(self.max_workers_var.get()))

            return True
        except ValueError as e:
            messagebox.showerror("错误", f"无效的设置值: {e}", parent=self)
            return False

    def _on_ok(self):
        """Handle OK button."""
        if self._apply_settings():
            self.result = True
            if self.on_save:
                self.on_save()
            self.destroy()

    def _on_apply(self):
        """Handle Apply button."""
        if self._apply_settings():
            if self.on_save:
                self.on_save()

    def _on_cancel(self):
        """Handle Cancel button."""
        self.result = False
        self.destroy()


def show_settings_dialog(parent: tk.Widget, config: Config, on_save: Optional[Callable] = None) -> bool:
    """
    Show the settings dialog.

    Args:
        parent: Parent widget
        config: Configuration object
        on_save: Callback when settings are saved

    Returns:
        True if settings were saved, False otherwise
    """
    dialog = SettingsDialog(parent, config, on_save)
    parent.wait_window(dialog)
    return dialog.result

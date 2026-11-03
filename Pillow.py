import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageFilter

class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("彩色影像模式轉換工具")
        self.root.geometry("1150x650")
        self.root.minsize(950, 550)

        # 狀態變數
        self.src_image_path = None
        self.original_img = None     # PIL 原圖 (RGB)
        self.processed_img = None    # 處理後的預設影像

        # 拉普拉斯專用 (a/b/c 三張圖)
        self.laplacian_a = None
        self.laplacian_b = None
        self.laplacian_c = None

        self.preview_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self._build_ui()

    def _build_ui(self):
        # 頂部操作欄
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(top_frame, text="📁 開啟影像", command=self.load_image)
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.lbl_filepath = ttk.Label(top_frame, text="未選擇任何檔案", foreground="gray")
        self.lbl_filepath.pack(side=tk.LEFT, padx=10)

        self.btn_save = ttk.Button(top_frame, text="💾 儲存新檔", command=self.save_image, state=tk.DISABLED)
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        # 主區域
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左側控制選單
        control_frame = ttk.LabelFrame(main_frame, text="轉換設定", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.mode_var = tk.StringVar(value="gray")
        
        rb_gray = ttk.Radiobutton(control_frame, text="1. 灰階 (Grayscale)", value="gray", variable=self.mode_var, command=self.on_mode_change)
        rb_gray.pack(anchor=tk.W, pady=2)

        rb_bw = ttk.Radiobutton(control_frame, text="2. 純黑白 (二值化)", value="bw", variable=self.mode_var, command=self.on_mode_change)
        rb_bw.pack(anchor=tk.W, pady=2)

        self.frame_bw_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_bw_param, text="臨界值 (Threshold):").pack(anchor=tk.W)
        self.scale_threshold = ttk.Scale(self.frame_bw_param, from_=0, to=255, value=128, command=self.on_param_change)
        self.scale_threshold.pack(fill=tk.X, pady=2)
        self.lbl_threshold_val = ttk.Label(self.frame_bw_param, text="128")
        self.lbl_threshold_val.pack(anchor=tk.E)

        rb_palette = ttk.Radiobutton(control_frame, text="3. 調色盤 (Palette)", value="palette", variable=self.mode_var, command=self.on_mode_change)
        rb_palette.pack(anchor=tk.W, pady=2)

        self.frame_palette_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_palette_param, text="色彩數量 (2-256):").pack(anchor=tk.W)
        self.scale_colors = ttk.Scale(self.frame_palette_param, from_=2, to=256, value=16, command=self.on_param_change)
        self.scale_colors.pack(fill=tk.X, pady=2)
        self.lbl_colors_val = ttk.Label(self.frame_palette_param, text="16 色")
        self.lbl_colors_val.pack(anchor=tk.E)

        rb_xray = ttk.Radiobutton(control_frame, text="4. X-Ray 負片效果", value="xray", variable=self.mode_var, command=self.on_mode_change)
        rb_xray.pack(anchor=tk.W, pady=2)

        rb_median = ttk.Radiobutton(control_frame, text="5. 全圖中位數濾波", value="median", variable=self.mode_var, command=self.on_mode_change)
        rb_median.pack(anchor=tk.W, pady=2)

        self.frame_median_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_median_param, text="濾波核心大小 (Kernel):").pack(anchor=tk.W)
        self.scale_kernel = ttk.Scale(self.frame_median_param, from_=3, to=15, value=3, command=self.on_param_change)
        self.scale_kernel.pack(fill=tk.X, pady=2)
        self.lbl_kernel_val = ttk.Label(self.frame_median_param, text="3 x 3")
        self.lbl_kernel_val.pack(anchor=tk.E)

        rb_local_median = ttk.Radiobutton(control_frame, text="6. 局部中位數濾波 (筆刷)", value="local_median", variable=self.mode_var, command=self.on_mode_change)
        rb_local_median.pack(anchor=tk.W, pady=2)

        self.frame_local_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_local_param, text="刷子大小 (Brush Size):").pack(anchor=tk.W)
        self.scale_brush = ttk.Scale(self.frame_local_param, from_=10, to=100, value=30, command=self.on_param_change)
        self.scale_brush.pack(fill=tk.X, pady=2)
        self.lbl_brush_val = ttk.Label(self.frame_local_param, text="30 px")
        self.lbl_brush_val.pack(anchor=tk.E)

        # 7. 拉普拉斯濾波器 (對齊講義需求)
        rb_laplacian = ttk.Radiobutton(control_frame, text="7. 拉普拉斯濾波器 (銳化)", value="laplacian", variable=self.mode_var, command=self.on_mode_change)
        rb_laplacian.pack(anchor=tk.W, pady=2)

        # 右側預覽容器
        self.preview_frame = ttk.Frame(main_frame)
        self.preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 一般模式：原始圖 + 轉換後圖
        self.frame_orig = ttk.LabelFrame(self.preview_frame, text="原始彩色影像", padding="5")
        self.frame_orig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_orig_preview = ttk.Label(self.frame_orig, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_orig_preview.pack(fill=tk.BOTH, expand=True)

        self.frame_proc = ttk.LabelFrame(self.preview_frame, text="轉換後預覽", padding="5")
        self.frame_proc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_proc_preview = ttk.Label(self.frame_proc, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_proc_preview.pack(fill=tk.BOTH, expand=True)

        # 拉普拉斯模式專用三對比框 (a, b, c)
        self.frame_lap_a = ttk.LabelFrame(self.preview_frame, text="(a) 原始灰階影像", padding="5")
        self.lbl_lap_a = ttk.Label(self.frame_lap_a, text="無資料", anchor=tk.CENTER)
        self.lbl_lap_a.pack(fill=tk.BOTH, expand=True)

        self.frame_lap_b = ttk.LabelFrame(self.preview_frame, text="(b) Laplacian 遮罩處理結果", padding="5")
        self.lbl_lap_b = ttk.Label(self.frame_lap_b, text="無資料", anchor=tk.CENTER)
        self.lbl_lap_b.pack(fill=tk.BOTH, expand=True)

        self.frame_lap_c = ttk.LabelFrame(self.preview_frame, text="(c) 結合(a)與(b)之銳化結果", padding="5")
        self.lbl_lap_c = ttk.Label(self.frame_lap_c, text="無資料", anchor=tk.CENTER)
        self.lbl_lap_c.pack(fill=tk.BOTH, expand=True)

        # 滑鼠事件綁定
        self.lbl_proc_preview.bind("<Button-1>", self.apply_local_filter)
        self.lbl_proc_preview.bind("<B1-Motion>", self.apply_local_filter)

        self.root.bind("<Configure>", self.on_resize)

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="選擇彩色影像",
            filetypes=[("圖片檔案", "*.jpg *.jpeg *.png *.bmp *.webp"), ("所有檔案", "*.*")]
        )
        if not file_path:
            return

        try:
            self.src_image_path = file_path
            self.lbl_filepath.config(text=os.path.basename(file_path))
            self.original_img = Image.open(file_path).convert("RGB")
            
            self.btn_save.config(state=tk.NORMAL)
            self.on_mode_change()
            self.update_preview()
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟圖片：\n{e}")

    def process_image(self):
        if self.original_img is None:
            return

        mode = self.mode_var.get()

        if mode == 'gray':
            self.processed_img = self.original_img.convert('L')
        elif mode == 'bw':
            thresh = int(self.scale_threshold.get())
            gray = self.original_img.convert('L')
            self.processed_img = gray.point(lambda p: 255 if p > thresh else 0).convert('1')
        elif mode == 'palette':
            num_colors = int(self.scale_colors.get())
            self.processed_img = self.original_img.quantize(colors=num_colors)
        elif mode == 'xray':
            gray = self.original_img.convert('L')
            inverted = ImageOps.invert(gray)
            enhancer = ImageEnhance.Contrast(inverted)
            self.processed_img = enhancer.enhance(1.5)
        elif mode == 'median':
            k_size = int(self.scale_kernel.get())
            if k_size % 2 == 0:
                k_size += 1
            self.processed_img = self.original_img.filter(ImageFilter.MedianFilter(size=k_size))
        elif mode == 'local_median':
            if self.processed_img is None or self.processed_img.size != self.original_img.size or self.processed_img.mode != self.original_img.mode:
                self.processed_img = self.original_img.copy()

        elif mode == 'laplacian':
            # === 完全對齊講義定義的 Laplacian 銳化流程 ===
            
            # (a) 原始灰階影像
            gray_img = self.original_img.convert('L')
            self.laplacian_a = gray_img
            gray_np = np.array(gray_img, dtype=np.float32)

            # 使用標準 3x3 中心點為負的拉普拉斯 Kernel [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
            lap_filter = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1.0, offset=0)
            edge_img = gray_img.filter(lap_filter)
            edge_np = np.array(edge_img, dtype=np.float32)

            # (b) Laplacian 遮罩處理結果 (純邊緣，視覺化時取絕對值並拉高視覺效果)
            edge_vis = np.clip(np.abs(edge_np) * 1.5, 0, 255).astype(np.uint8)
            self.laplacian_b = Image.fromarray(edge_vis)

            # (c) 結合 (a) 與 (b) 之銳化結果： Sharpened = (a) - Laplacian_edge
            sharpened_np = np.clip(gray_np - edge_np, 0, 255).astype(np.uint8)
            self.laplacian_c = Image.fromarray(sharpened_np)

            # 預設最終匯出影像設為 (c) 銳化結果
            self.processed_img = self.laplacian_c

    def apply_local_filter(self, event):
        if self.original_img is None or self.mode_var.get() != 'local_median':
            return

        click_x, click_y = event.x, event.y
        img_x = int((click_x - self.offset_x) / self.preview_scale)
        img_y = int((click_y - self.offset_y) / self.preview_scale)

        w, h = self.original_img.size
        if 0 <= img_x < w and 0 <= img_y < h:
            brush_size = int(self.scale_brush.get())
            radius = brush_size // 2

            left = max(0, img_x - radius)
            top = max(0, img_y - radius)
            right = min(w, img_x + radius)
            bottom = min(h, img_y + radius)

            if right > left and bottom > top:
                crop_box = (left, top, right, bottom)
                cropped_region = self.processed_img.crop(crop_box)
                filtered_region = cropped_region.filter(ImageFilter.MedianFilter(size=5))
                self.processed_img.paste(filtered_region, crop_box)
                self.update_preview()

    def on_mode_change(self):
        mode = self.mode_var.get()
        
        self.frame_bw_param.pack_forget()
        self.frame_palette_param.pack_forget()
        self.frame_median_param.pack_forget()
        self.frame_local_param.pack_forget()

        # 切換畫面佈局
        if mode == 'laplacian':
            self.frame_orig.pack_forget()
            self.frame_proc.pack_forget()
            
            self.frame_lap_a.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            self.frame_lap_b.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            self.frame_lap_c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        else:
            self.frame_lap_a.pack_forget()
            self.frame_lap_b.pack_forget()
            self.frame_lap_c.pack_forget()

            self.frame_orig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
            self.frame_proc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)

            if mode == 'bw':
                self.frame_bw_param.pack(fill=tk.X, pady=5)
            elif mode == 'palette':
                self.frame_palette_param.pack(fill=tk.X, pady=5)
            elif mode == 'median':
                self.frame_median_param.pack(fill=tk.X, pady=5)
            elif mode == 'local_median':
                self.frame_local_param.pack(fill=tk.X, pady=5)
                if self.original_img:
                    self.processed_img = self.original_img.copy()

        self.process_image()
        self.update_preview()

    def on_param_change(self, event=None):
        self.lbl_threshold_val.config(text=str(int(self.scale_threshold.get())))
        self.lbl_colors_val.config(text=f"{int(self.scale_colors.get())} 色")
        
        k_size = int(self.scale_kernel.get())
        if k_size % 2 == 0:
            k_size += 1
        self.lbl_kernel_val.config(text=f"{k_size} x {k_size}")
        self.lbl_brush_val.config(text=f"{int(self.scale_brush.get())} px")
        
        self.process_image()
        self.update_preview()

    def update_preview(self):
        if self.original_img is None:
            return

        try:
            mode = self.mode_var.get()

            if mode == 'laplacian':
                box_width = max(self.lbl_lap_a.winfo_width(), 160)
                box_height = max(self.lbl_lap_a.winfo_height(), 160)

                if self.laplacian_a and self.laplacian_b and self.laplacian_c:
                    a_resized, _, _, _ = self._resize_aspect_ratio(self.laplacian_a, box_width, box_height)
                    b_resized, _, _, _ = self._resize_aspect_ratio(self.laplacian_b, box_width, box_height)
                    c_resized, _, _, _ = self._resize_aspect_ratio(self.laplacian_c, box_width, box_height)

                    self.tk_lap_a = ImageTk.PhotoImage(a_resized, master=self.root)
                    self.tk_lap_b = ImageTk.PhotoImage(b_resized, master=self.root)
                    self.tk_lap_c = ImageTk.PhotoImage(c_resized, master=self.root)

                    self.lbl_lap_a.config(image=self.tk_lap_a, text="")
                    self.lbl_lap_b.config(image=self.tk_lap_b, text="")
                    self.lbl_lap_c.config(image=self.tk_lap_c, text="")
            else:
                box_width = max(self.lbl_orig_preview.winfo_width(), 200)
                box_height = max(self.lbl_orig_preview.winfo_height(), 200)

                orig_resized, _, _, _ = self._resize_aspect_ratio(self.original_img, box_width, box_height)
                self.tk_orig_image = ImageTk.PhotoImage(orig_resized, master=self.root)
                self.lbl_orig_preview.config(image=self.tk_orig_image, text="")

                if self.processed_img:
                    proc_resized, scale, ox, oy = self._resize_aspect_ratio(self.processed_img, box_width, box_height)
                    self.preview_scale = scale
                    self.offset_x = ox
                    self.offset_y = oy

                    self.tk_proc_image = ImageTk.PhotoImage(proc_resized, master=self.root)
                    self.lbl_proc_preview.config(image=self.tk_proc_image, text="")
        except Exception as e:
            print(f"預覽更新失敗: {e}")

    def _resize_aspect_ratio(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))

        offset_x = (max_w - new_w) // 2
        offset_y = (max_h - new_h) // 2

        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return resized_img, ratio, offset_x, offset_y

    def on_resize(self, event):
        if event.widget == self.root:
            self.update_preview()

    def save_image(self):
        mode = self.mode_var.get()
        base_name, _ = os.path.splitext(os.path.basename(self.src_image_path))

        if mode == 'laplacian':
            save_dir = filedialog.askdirectory(title="選擇資料夾 (將自動儲存 a, b, c 三張圖片)")
            if save_dir:
                try:
                    path_a = os.path.join(save_dir, f"{base_name}_laplacian_a_origin.png")
                    path_b = os.path.join(save_dir, f"{base_name}_laplacian_b_edge.png")
                    path_c = os.path.join(save_dir, f"{base_name}_laplacian_c_sharpened.png")

                    self.laplacian_a.save(path_a)
                    self.laplacian_b.save(path_b)
                    self.laplacian_c.save(path_c)

                    messagebox.showinfo("成功", f" (a)、(b)、(c) 三張圖片已成功儲存至：\n{save_dir}")
                except Exception as e:
                    messagebox.showerror("錯誤", f"儲存圖片失敗：\n{e}")
        else:
            if self.processed_img is None:
                return

            default_filename = f"{base_name}_{mode}.png"
            save_path = filedialog.asksaveasfilename(
                title="另存新檔",
                initialfile=default_filename,
                filetypes=[("PNG 檔案", "*.png"), ("JPEG 檔案", "*.jpg"), ("所有檔案", "*.*")]
            )

            if save_path:
                try:
                    self.processed_img.save(save_path)
                    messagebox.showinfo("成功", f"檔案已成功儲存至：\n{save_path}")
                except Exception as e:
                    messagebox.showerror("錯誤", f"儲存檔案失敗：\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()

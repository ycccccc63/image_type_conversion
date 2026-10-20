import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageFilter

class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("彩色影像模式轉換工具 (含局部筆刷去噪)")
        self.root.geometry("900x600")
        self.root.minsize(800, 500)

        # 狀態變數
        self.src_image_path = None
        self.original_img = None     # Pillow 原圖 (RGB)
        self.processed_img = None    # 處理後的 Pillow 影像
        self.tk_orig_image = None    # UI 顯示用的 ImageTk
        self.tk_proc_image = None    # UI 顯示用的 ImageTk
        
        # 預覽縮放參數 (用於座標轉換)
        self.preview_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0

        self._build_ui()

    def _build_ui(self):
        # 頂部操作欄：檔案選取與儲存
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(top_frame, text="📁 開啟影像", command=self.load_image)
        self.btn_open.pack(side=tk.LEFT, padx=5)

        self.lbl_filepath = ttk.Label(top_frame, text="未選擇任何檔案", foreground="gray")
        self.lbl_filepath.pack(side=tk.LEFT, padx=10)

        self.btn_save = ttk.Button(top_frame, text="💾 儲存新檔", command=self.save_image, state=tk.DISABLED)
        self.btn_save.pack(side=tk.RIGHT, padx=5)

        # 中間主區域：左側控制面板、右側影像預覽區
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- 左側：控制選項 ---
        control_frame = ttk.LabelFrame(main_frame, text="轉換設定", padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.mode_var = tk.StringVar(value="gray")
        
        rb_gray = ttk.Radiobutton(control_frame, text="1. 灰階 (Grayscale)", value="gray", variable=self.mode_var, command=self.on_mode_change)
        rb_gray.pack(anchor=tk.W, pady=3)

        rb_bw = ttk.Radiobutton(control_frame, text="2. 純黑白 (二值化)", value="bw", variable=self.mode_var, command=self.on_mode_change)
        rb_bw.pack(anchor=tk.W, pady=3)

        # 純黑白二值化 Threshold 滑桿
        self.frame_bw_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_bw_param, text="臨界值 (Threshold):").pack(anchor=tk.W)
        self.scale_threshold = ttk.Scale(self.frame_bw_param, from_=0, to=255, value=128, command=self.on_param_change)
        self.scale_threshold.pack(fill=tk.X, pady=2)
        self.lbl_threshold_val = ttk.Label(self.frame_bw_param, text="128")
        self.lbl_threshold_val.pack(anchor=tk.E)

        rb_palette = ttk.Radiobutton(control_frame, text="3. 調色盤 (Palette)", value="palette", variable=self.mode_var, command=self.on_mode_change)
        rb_palette.pack(anchor=tk.W, pady=3)

        # 調色盤色彩數 Slider
        self.frame_palette_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_palette_param, text="色彩數量 (2-256):").pack(anchor=tk.W)
        self.scale_colors = ttk.Scale(self.frame_palette_param, from_=2, to=256, value=16, command=self.on_param_change)
        self.scale_colors.pack(fill=tk.X, pady=2)
        self.lbl_colors_val = ttk.Label(self.frame_palette_param, text="16 色")
        self.lbl_colors_val.pack(anchor=tk.E)

        # X-Ray 模式
        rb_xray = ttk.Radiobutton(control_frame, text="4. X-Ray 負片效果", value="xray", variable=self.mode_var, command=self.on_mode_change)
        rb_xray.pack(anchor=tk.W, pady=3)

        # 全圖中位數濾波器
        rb_median = ttk.Radiobutton(control_frame, text="5. 全圖中位數濾波", value="median", variable=self.mode_var, command=self.on_mode_change)
        rb_median.pack(anchor=tk.W, pady=3)

        # 全圖中位數濾波參數
        self.frame_median_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_median_param, text="濾波核心大小 (Kernel):").pack(anchor=tk.W)
        self.scale_kernel = ttk.Scale(self.frame_median_param, from_=3, to=15, value=3, command=self.on_param_change)
        self.scale_kernel.pack(fill=tk.X, pady=2)
        self.lbl_kernel_val = ttk.Label(self.frame_median_param, text="3 x 3")
        self.lbl_kernel_val.pack(anchor=tk.E)

        # 6. 新增：局部中位數濾波 (刷子模式)
        rb_local_median = ttk.Radiobutton(control_frame, text="6. 局部中位數濾波 (筆刷)", value="local_median", variable=self.mode_var, command=self.on_mode_change)
        rb_local_median.pack(anchor=tk.W, pady=3)

        # 局部中位數濾波筆刷參數
        self.frame_local_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_local_param, text="刷子大小 (Brush Size):").pack(anchor=tk.W)
        self.scale_brush = ttk.Scale(self.frame_local_param, from_=10, to=100, value=30, command=self.on_param_change)
        self.scale_brush.pack(fill=tk.X, pady=2)
        self.lbl_brush_val = ttk.Label(self.frame_local_param, text="30 px")
        self.lbl_brush_val.pack(anchor=tk.E)

        # --- 右側：預覽區域 ---
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 原圖預覽框
        frame_orig = ttk.LabelFrame(preview_frame, text="原始彩色影像", padding="5")
        frame_orig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_orig_preview = ttk.Label(frame_orig, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_orig_preview.pack(fill=tk.BOTH, expand=True)

        # 轉換後預覽框
        frame_proc = ttk.LabelFrame(preview_frame, text="轉換後預覽 (滑鼠塗抹處)", padding="5")
        frame_proc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_proc_preview = ttk.Label(frame_proc, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_proc_preview.pack(fill=tk.BOTH, expand=True)

        # 綁定滑鼠點擊與拖曳事件至右側預覽圖
        self.lbl_proc_preview.bind("<Button-1>", self.apply_local_filter)
        self.lbl_proc_preview.bind("<B1-Motion>", self.apply_local_filter)

        self.root.bind("<Configure>", self.on_resize)

    def load_image(self):
        """選擇檔案並讀取圖片"""
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
        """根據目前介面設定執行全圖影像轉換"""
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
            # 初始化：如果切換到局部模式，先複製一份原圖作為底圖
            if self.processed_img is None or self.processed_img.size != self.original_img.size or self.processed_img.mode != self.original_img.mode:
                self.processed_img = self.original_img.copy()

    def apply_local_filter(self, event):
        """當滑鼠在預覽畫面上按住/拖曳時，計算座標並局部套用中位數濾波器"""
        if self.original_img is None or self.mode_var.get() != 'local_median':
            return

        # 取得滑鼠在 Label 上的點擊座標 (UI 座標)
        click_x = event.x
        click_y = event.y

        # 將 UI 座標反推回原本影像的像素座標
        img_x = int((click_x - self.offset_x) / self.preview_scale)
        img_y = int((click_y - self.offset_y) / self.preview_scale)

        w, h = self.original_img.size
        
        # 檢查點擊是否在有效影像範圍內
        if 0 <= img_x < w and 0 <= img_y < h:
            brush_size = int(self.scale_brush.get())
            radius = brush_size // 2

            # 計算切片區域 (Crop Box)
            left = max(0, img_x - radius)
            top = max(0, img_y - radius)
            right = min(w, img_x + radius)
            bottom = min(h, img_y + radius)

            if right > left and bottom > top:
                # 1. 剪裁局部區域
                crop_box = (left, top, right, bottom)
                cropped_region = self.processed_img.crop(crop_box)

                # 2. 對該區域施加中位數濾波器 (Kernel 定為 5x5 以確保效果顯著)
                filtered_region = cropped_region.filter(ImageFilter.MedianFilter(size=5))

                # 3. 將處理完的區域貼回 processed_img 影像中
                self.processed_img.paste(filtered_region, crop_box)

                # 4. 即時更新畫面
                self.update_preview()

    def on_mode_change(self):
        """模式切換時重設控制選單"""
        mode = self.mode_var.get()
        
        self.frame_bw_param.pack_forget()
        self.frame_palette_param.pack_forget()
        self.frame_median_param.pack_forget()
        self.frame_local_param.pack_forget()

        if mode == 'bw':
            self.frame_bw_param.pack(fill=tk.X, pady=5)
        elif mode == 'palette':
            self.frame_palette_param.pack(fill=tk.X, pady=5)
        elif mode == 'median':
            self.frame_median_param.pack(fill=tk.X, pady=5)
        elif mode == 'local_median':
            self.frame_local_param.pack(fill=tk.X, pady=5)
            # 重設為原圖，準備讓使用者開始塗抹
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
        """更新預覽圖，並計算顯示縮放比例與偏移量"""
        if self.original_img is None or self.processed_img is None:
            return

        try:
            box_width = max(self.lbl_orig_preview.winfo_width(), 250)
            box_height = max(self.lbl_orig_preview.winfo_height(), 250)

            # 縮放原圖
            orig_resized, _, _, _ = self._resize_aspect_ratio(self.original_img, box_width, box_height)
            self.tk_orig_image = ImageTk.PhotoImage(orig_resized, master=self.root)
            self.lbl_orig_preview.config(image=self.tk_orig_image, text="")

            # 縮放處理後的圖片（保留縮放比例與偏移量以供座標轉換）
            proc_resized, scale, ox, oy = self._resize_aspect_ratio(self.processed_img, box_width, box_height)
            self.preview_scale = scale
            self.offset_x = ox
            self.offset_y = oy

            self.tk_proc_image = ImageTk.PhotoImage(proc_resized, master=self.root)
            self.lbl_proc_preview.config(image=self.tk_proc_image, text="")
        except Exception as e:
            print(f"預覽更新失敗: {e}")

    def _resize_aspect_ratio(self, img, max_w, max_h):
        """等比例縮放圖片，並回傳顯示比例與置中偏移量"""
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))

        # 計算圖片在 Label 內置中的偏移像素 (Offset)
        offset_x = (max_w - new_w) // 2
        offset_y = (max_h - new_h) // 2

        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return resized_img, ratio, offset_x, offset_y

    def on_resize(self, event):
        if event.widget == self.root:
            self.update_preview()

    def save_image(self):
        if self.processed_img is None:
            return

        mode = self.mode_var.get()
        base_name, _ = os.path.splitext(os.path.basename(self.src_image_path))
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

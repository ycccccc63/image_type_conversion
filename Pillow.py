import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageEnhance

class ImageConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("彩色影像模式轉換工具")
        self.root.geometry("900x600") # 修正幾何尺寸格式
        self.root.minsize(800, 500)

        # 狀態變數
        self.src_image_path = None
        self.original_img = None     # Pillow 原圖 (RGB)
        self.processed_img = None    # 處理後的 Pillow 影像
        self.tk_orig_image = None    # UI 顯示用的 ImageTk
        self.tk_proc_image = None    # UI 顯示用的 ImageTk

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

        # 模式選擇 (Radio Buttons)
        self.mode_var = tk.StringVar(value="gray")
        
        rb_gray = ttk.Radiobutton(control_frame, text="1. 灰階 (Grayscale)", value="gray", variable=self.mode_var, command=self.on_mode_change)
        rb_gray.pack(anchor=tk.W, pady=5)

        rb_bw = ttk.Radiobutton(control_frame, text="2. 純黑白 (二值化)", value="bw", variable=self.mode_var, command=self.on_mode_change)
        rb_bw.pack(anchor=tk.W, pady=5)

        # 純黑白二值化 Threshold 滑桿
        self.frame_bw_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_bw_param, text="臨界值 (Threshold):").pack(anchor=tk.W)
        self.scale_threshold = ttk.Scale(self.frame_bw_param, from_=0, to=255, value=128, command=self.on_param_change)
        self.scale_threshold.pack(fill=tk.X, pady=2)
        self.lbl_threshold_val = ttk.Label(self.frame_bw_param, text="128")
        self.lbl_threshold_val.pack(anchor=tk.E)

        rb_palette = ttk.Radiobutton(control_frame, text="3. 調色盤 (Palette)", value="palette", variable=self.mode_var, command=self.on_mode_change)
        rb_palette.pack(anchor=tk.W, pady=5)

        # 調色盤色彩數 Slider
        self.frame_palette_param = ttk.Frame(control_frame)
        ttk.Label(self.frame_palette_param, text="色彩數量 (2-256):").pack(anchor=tk.W)
        self.scale_colors = ttk.Scale(self.frame_palette_param, from_=2, to=256, value=16, command=self.on_param_change)
        self.scale_colors.pack(fill=tk.X, pady=2)
        self.lbl_colors_val = ttk.Label(self.frame_palette_param, text="16 色")
        self.lbl_colors_val.pack(anchor=tk.E)

        # 新增：X-Ray 模式
        rb_xray = ttk.Radiobutton(control_frame, text="4. X-Ray 負片效果", value="xray", variable=self.mode_var, command=self.on_mode_change)
        rb_xray.pack(anchor=tk.W, pady=5)

        # --- 右側：預覽區域 ---
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # 原圖預覽框
        frame_orig = ttk.LabelFrame(preview_frame, text="原始彩色影像", padding="5")
        frame_orig.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_orig_preview = ttk.Label(frame_orig, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_orig_preview.pack(fill=tk.BOTH, expand=True)

        # 轉換後預覽框
        frame_proc = ttk.LabelFrame(preview_frame, text="轉換後預覽", padding="5")
        frame_proc.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=2)
        self.lbl_proc_preview = ttk.Label(frame_proc, text="尚未載入圖片", anchor=tk.CENTER)
        self.lbl_proc_preview.pack(fill=tk.BOTH, expand=True)

        # 視窗大小改變時動態調整圖片顯示
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
        """根據目前介面設定執行影像轉換功能"""
        if self.original_img is None:
            return

        mode = self.mode_var.get()

        if mode == 'gray':
            # 1. 灰階 ('L' 模式)
            self.processed_img = self.original_img.convert('L')

        elif mode == 'bw':
            # 2. 純黑白二值化 ('1' 模式)
            thresh = int(self.scale_threshold.get())
            gray = self.original_img.convert('L')
            self.processed_img = gray.point(lambda p: 255 if p > thresh else 0).convert('1')

        elif mode == 'palette':
            # 3. 調色盤 ('P' 模式)
            num_colors = int(self.scale_colors.get())
            self.processed_img = self.original_img.quantize(colors=num_colors)

        elif mode == 'xray':
            # 4. X-Ray 效果：先轉灰階 -> 反相(Invert) -> 增強對比度
            gray = self.original_img.convert('L')
            inverted = ImageOps.invert(gray)
            enhancer = ImageEnhance.Contrast(inverted)
            self.processed_img = enhancer.enhance(1.5)  # 稍微拉高對比度 1.5 倍

    def on_mode_change(self):
        """選擇模式切換時顯示/隱藏對應控制選單"""
        mode = self.mode_var.get()
        
        if mode == 'bw':
            self.frame_bw_param.pack(fill=tk.X, pady=5)
            self.frame_palette_param.pack_forget()
        elif mode == 'palette':
            self.frame_bw_param.pack_forget()
            self.frame_palette_param.pack(fill=tk.X, pady=5)
        else:
            self.frame_bw_param.pack_forget()
            self.frame_palette_param.pack_forget()

        self.process_image()
        self.update_preview()

    def on_param_change(self, event=None):
        """滑桿數值變更時即時觸發重新計算與繪製"""
        self.lbl_threshold_val.config(text=str(int(self.scale_threshold.get())))
        self.lbl_colors_val.config(text=f"{int(self.scale_colors.get())} 色")
        
        self.process_image()
        self.update_preview()

    def update_preview(self):
        """將 Pillow Image 轉換為 Tkinter 可用格式並調整視窗縮放比例"""
        if self.original_img is None or self.processed_img is None:
            return

        try:
            box_width = max(self.lbl_orig_preview.winfo_width(), 250)
            box_height = max(self.lbl_orig_preview.winfo_height(), 250)

            # 縮放原圖 (指定 master=self.root 防錯)
            orig_resized = self._resize_aspect_ratio(self.original_img, box_width, box_height)
            self.tk_orig_image = ImageTk.PhotoImage(orig_resized, master=self.root)
            self.lbl_orig_preview.config(image=self.tk_orig_image, text="")

            # 縮放處理後圖片
            proc_resized = self._resize_aspect_ratio(self.processed_img, box_width, box_height)
            self.tk_proc_image = ImageTk.PhotoImage(proc_resized, master=self.root)
            self.lbl_proc_preview.config(image=self.tk_proc_image, text="")
        except Exception as e:
            print(f"預覽更新失敗: {e}")

    def _resize_aspect_ratio(self, img, max_w, max_h):
        """等比例縮放圖片至指定容器大小"""
        w, h = img.size
        ratio = min(max_w / w, max_h / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def on_resize(self, event):
        """視窗動態調整大小時更新預覽"""
        if event.widget == self.root:
            self.update_preview()

    def save_image(self):
        """儲存轉換後的影像檔案"""
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

# ================= 程式啟動點 =================
if __name__ == "__main__":
    root = tk.Tk()
    app = ImageConverterApp(root)
    root.mainloop()
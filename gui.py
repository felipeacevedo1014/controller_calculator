import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import threading
import sys, os
import math
import webbrowser
import requests
from PIL import Image, ImageTk

from core import Controller, fetch_prices, run_calculations, run_building_calculations
from tooltip import ToolTip
from updater import check_for_updates
from version import __version__, __app_name__


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{__app_name__} v{__version__}")
        # --- fonts ---
        self.font_main = ("Arial", 14)
        self.font_tree = ("Arial", 12)
        
        self.title("Trane Controller & Expansion Calculator")
        self.geometry("1020x580")
        self.resizable(True, False)

        check_for_updates()
        print("Running version:", __version__)

        # --- controllers & pricing setup ---
        self.controllers = self.initialize_controllers()
        self.expansions = [
            self.controllers["XM90"],
            self.controllers["XM70"],
            self.controllers["XM30"],
            self.controllers["XM32"],
        ]

        # --- zoom setup 🔧 ---
        self.image_x = 0
        self.image_y = 0

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        # Baseline is 1920x1080
        base_width = 1920
        base_zoom = {
            "S500": 0.25,
            "UC600": 0.25,
            "S800": 0.54
        }
        scaling_factor = screen_width / base_width
        # if screen_width > 1500:
        #     scaling_factor = 1.0
        # else:
        #     scaling_factor = 2
        # Apply scaling
        self.zoom_factors = {
            key: round(zoom * scaling_factor, 3)
            for key, zoom in base_zoom.items()
        }
        self.zoom_factor = self.zoom_factors["S500"]  # or default controller
        print(f"Screen resolution: {screen_width}x{screen_height}")
        print("Zoom factors:", self.zoom_factors)

        def resource_path(rel_path: str) -> str:
            base = getattr(sys, "_MEIPASS", os.path.abspath("."))
            return os.path.join(base, rel_path)

        self.zoom_step = 0.2
        self.original_images = {
            "S500": Image.open(resource_path("assets/S500_2.png")),
            "UC600": Image.open(resource_path("assets/UC600_2.png")),
            "S800": Image.open(resource_path("assets/S800.png"))
        }

        #--image panning setup 🔧---
        self.pan_start_x = None
        self.pan_start_y = None  

        # --- load controller images (initial) 🔧 ---
        self.current_controller = "S500"
        self.current_image = None  # updated by method
        self.zoom_factor = self.zoom_factors.get(self.current_controller, 0.3)  # 🔧 Add this
        
        # --- bind zoom 🔧 ---
        self.bind("<Control-MouseWheel>", self._on_mousewheel_zoom)

        # --- tabview setup ---
        self._multi_new_row_counter = 1  # auto-name counter for new rows
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        self.tab_system = self.tabview.add("Single System")
        self.tab_building = self.tabview.add("Multiple Systems")
        self.tab_resources = self.tabview.add("Resources")
        self.tabview.set("Single System")

        # --- build tabs ---
        self.build_single_system_tab()
        self.build_multiple_system_tab()
        self.build_resources_tab()

        # --- status label ---
        self.status_label = ctk.CTkLabel(self, text="",font=("Arial", 14))
        self.status_label.pack()

    def initialize_controllers(self):
        uc600 = Controller("UC600", power_AC=26, width=8.5, UI=8, UIAO=6, BO=4, PRESSURE=1, max_point_capacity=120)
        s500 =  Controller("S500",  power_AC=24, width=5.65,AI=5, UI=2, BI=3, BO=9, BIAO=2, PRESSURE=2, max_point_capacity=133)
        s800 =  Controller("S800",  power_DC=24, width=5.65, max_point_capacity=500)
        xm90 =  Controller("XM90",  power_AC=50, width=8.5, UI=16, UIAO=8, BO=8)
        xm70 =  Controller("XM70",  power_AC=26, width=8.5, UI=8, UIAO=6, BO=4, PRESSURE=1)
        xm30 =  Controller("XM30",  power_DC=120, width=2.11, UIAO=4)
        xm32 =  Controller("XM32",  power_DC=100, width=2.82, BO=4)
        pm014 = Controller("PM014", power_AC=20, width=5)

        prices_url = "https://raw.githubusercontent.com/felipeacevedo1014/controller_calculator/refs/heads/main/prices.csv"
        prices_df = fetch_prices(prices_url)
        prices = list(prices_df.iloc[:, 2])

        for i, key in enumerate(["UC600","S500","XM90","XM70","XM30","XM32","S800","PM014"]):
            locals()[key.lower()].price = prices[i]

        return {
            "UC600": uc600,
            "S500":  s500,
            "XM90":  xm90,
            "XM70":  xm70,
            "XM30":  xm30,
            "XM32":  xm32,
            "S800":  s800,
            "PM014": pm014,
        }

    def build_single_system_tab(self):
        frame = ctk.CTkFrame(self.tab_system)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        frame.grid_propagate(False)

        for r in range(1, 6):
            frame.grid_rowconfigure(r, weight=1)
        frame.grid_rowconfigure(7, weight=1)
        frame.grid_columnconfigure(2, weight=1)

        # --- central image label ---
        self.canvas_frame = ctk.CTkFrame(frame)
        self.canvas_frame.grid(row=1, column=2, rowspan=6, sticky="nsew")
        self.canvas = tk.Canvas(self.canvas_frame, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")
        self.zoom_hint_label = ctk.CTkLabel(
            frame,
            text="🔍 Hold Ctrl and scroll to zoom. Click and drag to pan. Double Click to reset the zoom",
            text_color="gray",
            font=self.font_tree
        )
        self.zoom_hint_label.grid(row=8, column=2, pady=(2, 2), sticky="nsew")
        # Initialize canvas image handle
        self.canvas_image_id = None

        # Bind panning events
        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._do_pan)
        #self.after(100, lambda: self._update_image_display(
        #    self.original_images[self.current_controller], center_if_needed=True))
        self.after(50,self._wait_for_canvas_ready)

        #--zoom reset--
        self.canvas.bind("<Double-Button-1>", self._reset_zoom)

        # --- input fields (cols 0–1) ---
        self.inputs = {}
        row = 0
        for label in ["BO", "BI", "UI", "AO", "AI", "PRESSURE"]:
            ctk.CTkLabel(frame, text=label, font=self.font_main).grid(row=1+row, column=0, sticky="w", padx=5, pady=2)
            entry = ctk.CTkEntry(frame, width=60, font=self.font_main)
            entry.insert(0, "0")
            entry.grid(row=1+row, column=1, pady=2, padx=(0,5), sticky="w")
            self.inputs[label] = entry
            row += 1

        # --- controller selector & spare ---
        ctk.CTkLabel(frame, text="", font=self.font_main).grid(row=0, column=0, padx=5)
        self.controller_choice = ctk.CTkOptionMenu(
            frame, font=self.font_main,
            values=["S500", "UC600", "S800"],
            command=self._on_controller_select
        )
        self.controller_choice.set("S500")
        self.controller_choice.grid(row=0, column=3, padx=10, columnspan=2, sticky="e")
        ToolTip(self.controller_choice, text="Choose a controller: UC600, S500 or S800.")

        ctk.CTkLabel(frame, text="Spare Points[%]", font=self.font_main).grid(row=1, column=3, sticky="w", padx=2)
        self.spare_spin = ctk.CTkEntry(frame, width=50, font=self.font_main)
        self.spare_spin.insert(0, "0")
        self.spare_spin.grid(row=1, column=3, columnspan=2, pady=2, padx=(0,5), sticky="e")
        ToolTip(self.spare_spin, text="Add spare points to each type (e.g. 10% means 10% more points calculated)")

        self.expansion_vars = {}
        for idx, exp in enumerate(["XM90", "XM70", "XM30", "XM32"]):
            cb = ctk.CTkCheckBox(frame, text=f"Include {exp}", font=self.font_main)
            cb.deselect() if exp in ["XM70"] else cb.select()
            cb.grid(row=2+idx, column=3, columnspan=2, sticky="w", padx=5)
            self.expansion_vars[exp] = cb

        # --- PM014 checkbox ---
        self.pm014_var = ctk.CTkCheckBox(frame, text="Include PM014", font=self.font_main)
        self.pm014_var.select()
        self.pm014_var.grid(row=6, column=3, columnspan=2, sticky="w", padx=5)

        ctk.CTkButton(frame, text="Calculate", command=self.calculate_single, font=self.font_main)\
            .grid(row=8, column=0, pady=10, padx=5, columnspan=2)
        self.save_button = ctk.CTkButton(frame, text="Save Results", command=self.save_single_results, font=self.font_main)
        self.save_button.grid(row=8, column=3, pady=10, padx=5, columnspan=2)


        style = ttk.Style()
        is_dark = ctk.get_appearance_mode() == "Dark"
        print(f"Using dark mode: {is_dark}")
        #bg_color = self["bg"] if is_dark else "#e0e0e0"
        bg_color ="gray14"
        print(f"Using background color: {bg_color}")
        style.configure("Custom.Treeview", background=bg_color, fieldbackground=bg_color, foreground="white")
        style.configure("Custom.Treeview.Heading", font=("Arial", 14, "bold"))  # Column titles
        style.configure("Custom.Treeview", font=self.font_tree)  # Row content

        self.tree_single = ttk.Treeview(
        frame,
        columns=("S500","UC600","S800","XM90","XM70","XM30","XM32","PM014","Price","Width"),
        show="headings",
        height=8,
        style="Custom.Treeview"
        )


        for col in self.tree_single["columns"]:
            self.tree_single.heading(col, text=col)
            self.tree_single.column(col, anchor="center", width=80)
        self.tree_single.grid(row=9, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)

    def _wait_for_canvas_ready(self):
        if self.canvas.winfo_width() < 10 or self.canvas.winfo_height()<10:
            self.after(50, self._wait_for_canvas_ready)
        else:
            self._update_image_display(self.original_images[self.current_controller], center_if_needed=True)

    def _on_controller_select(self, new_ctrl: str):
        self.current_controller = new_ctrl
        self.zoom_factor = self.zoom_factors[new_ctrl]
        pil_image = self.original_images[new_ctrl]
        self._update_image_display(pil_image)

    def _update_image_display(self, pil_image, center_if_needed=True):
        w, h = pil_image.size
        new_size = (int(w * self.zoom_factor), int(h * self.zoom_factor))
        resized = pil_image.resize(new_size, Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)

        # If we want to center on first load/reset
        if center_if_needed:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.image_x = (canvas_width - new_size[0]) // 2
            self.image_y = (canvas_height - new_size[1]) // 2

        self.canvas.delete("all")
        self.canvas_image_id = self.canvas.create_image(
            self.image_x,
            self.image_y,
            anchor="nw",
            image=self.tk_image
        )
    def _on_mousewheel_zoom(self, event):
        canvas_mouse_x = self.canvas.canvasx(event.x)
        canvas_mouse_y = self.canvas.canvasy(event.y)
        rel_x = canvas_mouse_x - self.image_x
        rel_y = canvas_mouse_y - self.image_y
        old_zoom = self.zoom_factor
        if event.delta > 0:
            self.zoom_factor *= 1 + self.zoom_step
        else:
            self.zoom_factor /= 1 + self.zoom_step
        scale = self.zoom_factor / old_zoom
        self.image_x = canvas_mouse_x - rel_x * scale
        self.image_y = canvas_mouse_y - rel_y * scale
        pil_image = self.original_images[self.current_controller]
        self._update_image_display(pil_image, center_if_needed=False)  # 🟡 KEY CHANGE

    def _reset_zoom(self, event=None):
        self.zoom_factor = self.zoom_factors[self.current_controller]
        pil_image = self.original_images[self.current_controller]
        self._update_image_display(pil_image, center_if_needed=True)

    def calculate_single(self):
        try:
            system_points = {k: int(v.get()) for k, v in self.inputs.items()}
            try:
                spare = int(self.spare_spin.get())
            except ValueError:
                messagebox.showerror("Error","Spare Points must be an integer.")
                return
            ctrl = self.controllers[self.controller_choice.get()]
            # Check point capacity
            system_points = {
                k: math.ceil(v * (1 + spare / 100))
                for k, v in system_points.items()
            }
            total_points = sum(system_points.values())
            if total_points > ctrl.max_point_capacity:
                messagebox.showwarning(
                    "Point Limit Exceeded",
                    f"{ctrl.name} has a point limit of {ctrl.max_point_capacity}, "
                    f"but this system requires {total_points} points."
                )
                return
            
            # Only include checked expansions
            self.expansions = [
                self.controllers[exp]
                for exp in ["XM90", "XM70", "XM30", "XM32"]
                if self.expansion_vars[exp].get()
            ]
            print("Using expansions:", [exp.name for exp in self.expansions])

            def thread_fn():
                self.status_label.configure(text="Calculating...")
                include_pm014 = bool(self.pm014_var.get())
                results = run_calculations(
                    system_points,
                    ctrl,
                    self.expansions,
                    self.controllers["PM014"],
                    include_pm014
                )
                for col in results.columns:
                    if col not in ("Price", "Width"):
                        results[col] = results[col].astype(int)
                self.tree_single.delete(*self.tree_single.get_children())
                for _, row in results.iterrows():
                    formatted_row = []
                    for col, val in row.items():
                        if col in ("Price", "Width"):
                            formatted_row.append(f"{val:.2f}")
                        else:
                            formatted_row.append(f"{int(val)}")
                    self.tree_single.insert("", "end", values=formatted_row)
                self.status_label.configure(text="Done.")
   
            threading.Thread(target=thread_fn, daemon=True).start()


        except Exception as e:
            messagebox.showerror("Error", f"Invalid input: {e}")

    def _start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def _do_pan(self, event):
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y

        self.canvas.move(self.canvas_image_id, dx, dy)

        # 🛠️ Update tracked image position
        self.image_x += dx
        self.image_y += dy

        self.pan_start_x = event.x
        self.pan_start_y = event.y
    

    def save_single_results(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv")]
        )

        if file_path:
            data = [self.tree_single.item(i)['values'] for i in self.tree_single.get_children()]
            df = pd.DataFrame(data, columns=self.tree_single["columns"])

            try:
                if file_path.endswith(".xlsx"):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)
                messagebox.showinfo("Saved", f"Results saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")


    def build_multiple_system_tab(self):
        frame = ctk.CTkFrame(self.tab_building)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        # === Toolbar: 7 columns ===
        toolbar = ctk.CTkFrame(frame)
        toolbar.pack(fill="x", padx=5, pady=(0, 10))

        # Make 7 uniform columns
        for i in range(7):
            toolbar.grid_columnconfigure(i, weight=1, uniform="toolbar")

        # (text, command) in the order you want across the row
        buttons = [
            ("Download Template", self.download_template),
            ("Load File",         self.load_systems_excel),
            ("Calculate",         self.calculate_multiple),
            ("Add Row",           self.add_multi_row),
            ("Duplicate Row(s)",  self.duplicate_multi_rows),
            ("Delete Row(s)",     self.delete_multi_rows),
            ("Clear All",         self.clear_multi_rows),
        ]

        # Build the buttons into columns 0..6
        for col, (text, cmd) in enumerate(buttons):
            btn_width = 200 if col == 0 else 150
            btn = ctk.CTkButton(
            toolbar,
            text=text,
            width=btn_width,              
            command=cmd,
            font=self.font_main,
            )
            # right padding except last button
            padx = (0, 6) if col < len(buttons) - 1 else (0, 0)
            btn.grid(row=0, column=col, padx=padx, pady=(0, 0), sticky="n")


        # === Controller dropdown, expansions, spare % ===
        controls_frame = ctk.CTkFrame(frame)
        controls_frame.pack(fill="x", padx=5, pady=(0, 10))

        self.multi_controller_choice = ctk.CTkOptionMenu(
            controls_frame, values=["S500", "UC600", "S800"], width=100, font=self.font_main
        )
        ToolTip(self.multi_controller_choice, text="Choose which controller to use for all systems in the spreadsheet")
        self.multi_controller_choice.set("S500")
        self.multi_controller_choice.pack(side="left", padx=8)  

        self.multi_exp_vars = {}
        for exp in ["XM90", "XM70", "XM30", "XM32"]:
            cb = ctk.CTkCheckBox(controls_frame, text=exp, width=80, font=self.font_main)
            cb.deselect() if exp in ["XM70"] else cb.select()
            cb.pack(side="left", padx=3)
            self.multi_exp_vars[exp] = cb
        self.multi_pm014_var = ctk.CTkCheckBox(controls_frame, text="PM014", width=80, font=self.font_main)
        self.multi_pm014_var.select()
        self.multi_pm014_var.pack(side="left", padx=3)

        ctk.CTkLabel(controls_frame, text="Spare %:", font=self.font_main).pack(side="left", padx=(10, 2))
        self.multi_spare_spin = ctk.CTkEntry(controls_frame, width=40, font=self.font_main)
        self.multi_spare_spin.insert(0, "0")
        self.multi_spare_spin.pack(side="left", padx=(0, 5))
        ToolTip(self.multi_spare_spin, text="Add spare points to each type (e.g. 10% means 10% more points calculated)")

        # === Editable system input table ===
        self.multi_input_table = ttk.Treeview(
            frame,
            columns=("System", "BO", "BI", "UI", "AO", "AI", "PRESSURE"),
            show="headings",
            height=6,
            style="Custom.Treeview",
            selectmode="extended"
        )
        for col in self.multi_input_table["columns"]:
            self.multi_input_table.heading(col, text=col)
            self.multi_input_table.column(col, width=100, anchor="center")
        self.multi_input_table.pack(fill="both", expand=True, pady=5, padx=5)
        self.multi_input_table.bind("<Double-1>", self.edit_cell)
        self.multi_input_table.bind("<Delete>", lambda e: self.delete_multi_rows())
        self.multi_input_table.bind("<Control-n>", lambda e: self.add_multi_row())
        self.multi_input_table.bind("<Control-d>", lambda e: self.duplicate_multi_rows())
        self.multi_input_table.bind("<Control-BackSpace>", lambda e: self.clear_multi_rows())

        self.table_hint_label = ctk.CTkLabel(
            frame,
            text="💡 Double Click to edit table cells. Press Enter to save changes.",
            text_color="gray",
            font=self.font_tree
        )
        self.table_hint_label.pack(pady=(2, 2))

        # === Output table ===
        self.multi_result_table = ttk.Treeview(
            frame,
            columns=("System","S500","UC600","XM90", "XM70", "XM30", "XM32", "PM014", "Price", "Width"),
            show="headings",
            height=6,
            style="Custom.Treeview"
        )
        for col in self.multi_result_table["columns"]:
            self.multi_result_table.heading(col, text=col)
            self.multi_result_table.column(col, width=85, anchor="center")
        self.multi_result_table.pack(fill="both", expand=True, pady=10, padx=1)

        # === Save button ===
        self.save_multi_button = ctk.CTkButton(
            frame, text="Save Results", width=120, command=self.save_multi_results, font=self.font_main
        )
        self.save_multi_button.pack(pady=(0, 5))

    def download_template(self):
        """Create and save a Multiple Systems input template (Excel or CSV)."""
        # Must match your loader & table order
        columns = ["System", "BO", "BI", "UI", "AO", "AI", "PRESSURE"]
        file_path = filedialog.asksaveasfilename(
            title="Save Template",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv")]
        )
        if not file_path:
            return
        try:
            df = pd.DataFrame(columns=columns)
            # Optional sample row:
            # df.loc[0] = ["AHU-1", 0, 0, 0, 0, 0, 0]
            if file_path.endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            messagebox.showinfo("Template Created", f"Template saved to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not create template:\n{e}")


    def load_systems_excel(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel or CSV File",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv")]
        )
        if not file_path:
            return

        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Normalize column names to lowercase
            df.columns = [col.strip().lower() for col in df.columns]

            # Define required lowercase columns
            required_cols = ["system", "bo", "bi", "ui", "ao", "ai", "pressure"]
            for col in required_cols:
                if col not in df.columns:
                    messagebox.showerror("Error", f"Missing column: {col.upper()}")
                    return

            # Clear previous entries
            self.multi_input_table.delete(*self.multi_input_table.get_children())

            # Populate the table (preserve original order)
            for _, row in df.iterrows():
                values = [row.get(col, 0) for col in required_cols]
                self.multi_input_table.insert("", "end", values=values)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    
    def calculate_multiple(self):
        def thread_fn():
            try:
                self.status_label.configure(text="Calculating...")
                # 1) Gather table rows
                rows = []
                for item in self.multi_input_table.get_children():
                    values = self.multi_input_table.item(item)['values']
                    rows.append(values)
                if not rows:
                    messagebox.showwarning("No Data", "Please load or enter at least one system.")
                    return

                df = pd.DataFrame(rows, columns=["System Name", "BO", "BI", "UI", "AO", "AI", "PRESSURE"])

                # 2) Validate numeric fields
                for col in ["BO", "BI", "UI", "AO", "AI", "PRESSURE"]:
                    df[col] = pd.to_numeric(df[col], errors="raise")

                # 3) Controller & expansions (respect checkboxes)
                ctrl = self.controllers[self.multi_controller_choice.get()]
                expansions = [
                    self.controllers[name]
                    for name in ["XM90", "XM70", "XM30", "XM32"]
                    if self.multi_exp_vars[name].get()
                ]

                # 4) Spare%
                spare = int(self.multi_spare_spin.get())

                # 5) Capacity check per system
                total_points_per_system = df.iloc[:, 1:-1].applymap(lambda x: math.ceil(x * (1 + spare / 100)))
                total_points_sum = total_points_per_system.sum(axis=1)
                controller_limit = ctrl.max_point_capacity
                exceeded = df["System Name"][total_points_sum > controller_limit].tolist()
                if exceeded:
                    messagebox.showwarning(
                        "Point Capacity Exceeded",
                        f"The following systems exceed {ctrl.name}'s capacity of {controller_limit} points." + "".join(exceeded)
                    )
                    return

                # 6) Run calculation
                include_pm014 = bool(self.multi_pm014_var.get())
                results_df = run_building_calculations(
                    df, ctrl, expansions, self.controllers["PM014"], include_pm014, spare
                )

                # 7) Display results
                self.multi_result_table.delete(*self.multi_result_table.get_children())
                columns = list(results_df.columns)
                self.multi_result_table["columns"] = columns
                for col in columns:
                    self.multi_result_table.heading(col, text=col)
                    self.multi_result_table.column(col, width=90, anchor="center")

                for _, row in results_df.iterrows():
                    formatted = []
                    for col in columns:
                        val = row[col]
                        if col in ("Price", "Width"):
                            formatted.append(f"{val:.2f}")
                        elif col == "System Name":
                            formatted.append(str(val))
                        else:
                            formatted.append(str(int(val)) if pd.notna(val) else "")
                    self.multi_result_table.insert("", "end", values=formatted)
                self.status_label.configure(text="Done.")
            except Exception as e:
                messagebox.showerror("Error", f"Calculation failed {e}")
        threading.Thread(target=thread_fn, daemon=True).start()


    def edit_cell(self, event):
        # Identify clicked region
        region = self.multi_input_table.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.multi_input_table.identify_row(event.y)
        col_id = self.multi_input_table.identify_column(event.x)

        # Get column index and name
        col_index = int(col_id.replace("#", "")) - 1
        col_name = self.multi_input_table["columns"][col_index]

        # Get existing value
        item = self.multi_input_table.item(row_id)
        old_value = item["values"][col_index]

        # Get cell coordinates
        x, y, width, height = self.multi_input_table.bbox(row_id, col_id)

        # Create entry widget
        entry = tk.Entry(self.multi_input_table, font=("Arial", 14))
        entry.insert(0, old_value)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus()

        # Auto-select all text so typing overwrites the value
        entry.selection_range(0, tk.END)
        entry.icursor(tk.END)

        # Re-select on focus-in (smooth UX across platforms)
        entry.bind("<FocusIn>", lambda e: (entry.selection_range(0, tk.END), entry.icursor(tk.END)))

        # Optional: Ctrl+A to select all
        entry.bind("<Control-a>", lambda e: (entry.selection_range(0, tk.END), "break"))

        def on_enter(event=None):
            new_value = entry.get()
            # Update value in the Treeview
            item["values"][col_index] = new_value
            self.multi_input_table.item(row_id, values=item["values"])
            entry.destroy()

        entry.bind("<Return>", on_enter)
        entry.bind("<FocusOut>", on_enter)


    def add_multi_row(self):
        """Append a new editable row to the Multiple Systems input table."""
        try:
            # Auto-generate a unique system name
            existing = [self.multi_input_table.item(i)["values"][0] for i in self.multi_input_table.get_children()]
            while True:
                name = f"System {self._multi_new_row_counter}"
                self._multi_new_row_counter += 1
                if name not in existing:
                    break
            values = [name, 0, 0, 0, 0, 0, 0]
            new_item = self.multi_input_table.insert("", "end", values=values)
            self.multi_input_table.see(new_item)
        except Exception as e:
            messagebox.showerror("Error", f"Could not add row:\n{e}")

    def delete_multi_rows(self):
        """Delete the selected rows from the Multiple Systems input table."""
        selection = self.multi_input_table.selection()
        if not selection:
            messagebox.showinfo("Delete Row(s)", "Select one or more rows to delete.")
            return
        # Optional: Confirm
        if not messagebox.askyesno("Confirm Delete", f"Delete {len(selection)} selected row(s)?"):
            return
        for item in selection:
            try:
                self.multi_input_table.delete(item)
            except Exception:
                pass

    def duplicate_multi_rows(self):
        """Duplicate selected rows in the Multiple Systems input table."""
        selection = self.multi_input_table.selection()
        if not selection:
            messagebox.showinfo("Duplicate Row(s)", "Select one or more rows to duplicate.")
            return
        # Build set of existing names for fast uniqueness checks
        existing_names = {self.multi_input_table.item(i)["values"][0] for i in self.multi_input_table.get_children()}
        def unique_name(base):
            if base not in existing_names:
                existing_names.add(base)
                return base
            k = 1
            while True:
                candidate = f"{base} ({k})"
                if candidate not in existing_names:
                    existing_names.add(candidate)
                    return candidate
                k += 1
        new_items = []
        for item in selection:
            vals = list(self.multi_input_table.item(item)["values"])
            if not vals:
                continue
            vals[0] = unique_name(str(vals[0]) + " - Copy")
            new_item = self.multi_input_table.insert("", "end", values=vals)
            new_items.append(new_item)
        if new_items:
            self.multi_input_table.see(new_items[-1])

    def clear_multi_rows(self):
        """Clear all rows from the Multiple Systems input table."""
        items = self.multi_input_table.get_children()
        if not items:
            return
        if not messagebox.askyesno("Clear All", "Delete ALL rows from the input table?"):
            return
        for item in items:
            try:
                self.multi_input_table.delete(item)
            except Exception:
                pass

    # --- Save results from multiple systems ---
    def save_multi_results(self):
        if not self.multi_result_table.get_children():
            messagebox.showwarning("No Results", "No results to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv")]
        )

        if not file_path:
            return

        # Extract table data
        data = [
            self.multi_result_table.item(row)["values"]
            for row in self.multi_result_table.get_children()
        ]
        columns = self.multi_result_table["columns"]

        df = pd.DataFrame(data, columns=columns)

        try:
            if file_path.endswith(".csv"):
                df.to_csv(file_path, index=False)
            else:
                df.to_excel(file_path, index=False)
            messagebox.showinfo("Saved", f"Results saved to:\n{os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file:\n{e}")

    def build_resources_tab(self):
        frame = ctk.CTkFrame(self.tab_resources)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text="Controller & Expansion Datasheets", font=("Arial", 14, "bold")).pack(pady=(5, 10))
        # --- datasheet links ---
        datasheets = {
            "UC600":"https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX45K-EN_06032022.pdf",
            "S500":"https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX090B-EN_04082023.pdf",
            "S800":"https://www.trane.com/content/dam/Trane/Commercial/lar/Mexico/BAS-PRD041C-EN_10272023.pdf",
            "XM90": "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX46E-EN_03182020.pdf",
            "XM70": "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX46E-EN_03182020.pdf",
            "XM30": "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX46E-EN_03182020.pdf",
            "XM32": "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX46E-EN_03182020.pdf",
            "PM014": "https://elibrary.tranetechnologies.com/public/commercial-hvac/Literature/Installation%20Operation%20and%20Maintenance/BAS-SVX33G-EN_04012020.pdf"
        }
        for name, url in datasheets.items():
            btn = ctk.CTkButton(
                frame,
                text=f"{name} Datasheet",
                width=240,
                command=lambda u=url: webbrowser.open(u),
                font=self.font_main
            )
            btn.pack(pady=5)


if __name__ == '__main__':
    app = App()
    app.mainloop()

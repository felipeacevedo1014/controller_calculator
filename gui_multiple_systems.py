import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import threading
import os
import math
from PIL import Image, ImageTk

from core_2 import Controller, fetch_prices, run_calculations, run_building_calculations

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trane Controller & Expansion Calculator")
        self.geometry("920x480")
        self.resizable(False, False)

        # --- controllers & pricing setup ---
        self.controllers = self.initialize_controllers()
        self.expansions = [
            self.controllers["XM90"],
            self.controllers["XM70"],
            self.controllers["XM30"],
            self.controllers["XM32"],
        ]
        #self.expansions_max_default = [5, 7, 34, 34]
        #use this to optimize the results
        self.expansions_max_default = [5, 7, 25, 25]

        # --- zoom setup 🔧 ---
        self.image_x = 0
        self.image_y = 0
        self.zoom_factor = 0.23
        self.zoom_step = 0.2
        self.original_images = {
            "S500": Image.open("assets/S500_2.png"),
            "UC600": Image.open("assets/UC600_2.png")
        }

        #--image panning setup 🔧---
        self.pan_start_x = None
        self.pan_start_y = None  

        # --- load controller images (initial) 🔧 ---
        self.current_controller = "S500"
        self.current_image = None  # updated by method

        # --- bind zoom 🔧 ---
        self.bind("<Control-MouseWheel>", self._on_mousewheel_zoom)

        # --- tabview setup ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(expand=True, fill="both", padx=10, pady=10)
        self.tab_system = self.tabview.add("Single System")
        self.tab_building = self.tabview.add("Multiple Systems")
        self.tabview.set("Single System")

        # --- build tabs ---
        self.build_single_system_tab()
        self.build_multiple_system_tab()

    def initialize_controllers(self):
        uc600 = Controller("UC600", power_AC=26, width=8.5, UI=8, UIAO=6, BO=4, PRESSURE=1, max_point_capacity=120)
        s500 =  Controller("S500",  power_AC=24, width=5.65,AI=5, UI=2, BI=3, BO=9, BIAO=2, PRESSURE=2, max_point_capacity=133)
        xm90 =  Controller("XM90",  power_AC=50, width=8.5, UI=16, UIAO=8, BO=8)
        xm70 =  Controller("XM70",  power_AC=26, width=8.5, UI=8, UIAO=6, BO=4)
        xm30 =  Controller("XM30",  power_DC=120, width=2.11, UIAO=4)
        xm32 =  Controller("XM32",  power_DC=100, width=2.82, BO=4)
        pm014 = Controller("PM014", power_AC=20, width=5)

        prices_url = "https://raw.githubusercontent.com/felipeacevedo1014/controller_calculator/refs/heads/main/prices.csv"
        prices_df = fetch_prices(prices_url)
        prices = list(prices_df.iloc[:, 2])

        for i, key in enumerate(["UC600","S500","XM90","XM70","XM30","XM32","PM014"]):
            locals()[key.lower()].price = prices[i]

        return {
            "UC600": uc600,
            "S500":  s500,
            "XM90":  xm90,
            "XM70":  xm70,
            "XM30":  xm30,
            "XM32":  xm32,
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
            font=("Arial", 11)
        )
        self.zoom_hint_label.grid(row=7, column=2, pady=(2, 0), sticky="n")
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
            ctk.CTkLabel(frame, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=2)
            entry = ctk.CTkEntry(frame, width=60)
            entry.insert(0, "0")
            entry.grid(row=row, column=1, pady=2, padx=(0,5), sticky="w")
            self.inputs[label] = entry
            row += 1

        # --- controller selector & spare ---
        ctk.CTkLabel(frame, text="Controller").grid(row=0, column=3, padx=5)
        self.controller_choice = ctk.CTkOptionMenu(
            frame,
            values=["S500", "UC600"],
            command=self._on_controller_select
        )
        self.controller_choice.set("S500")
        self.controller_choice.grid(row=0, column=3, padx=10, sticky="e")

        ctk.CTkLabel(frame, text="Spare Points [%]").grid(row=1, column=3, sticky="w", padx=2)
        self.spare_spin = ctk.CTkEntry(frame, width=50)
        self.spare_spin.insert(0, "0")
        self.spare_spin.grid(row=1, column=3, pady=2, padx=(0,5), sticky="e")

        self.expansion_vars = {}
        for idx, exp in enumerate(["XM90", "XM70", "XM30", "XM32"]):
            cb = ctk.CTkCheckBox(frame, text=f"Include {exp}")
            cb.select()
            cb.grid(row=2+idx, column=3, columnspan=2, sticky="w", padx=5)
            self.expansion_vars[exp] = cb

        ctk.CTkButton(frame, text="Calculate", command=self.calculate_single)\
            .grid(row=6, column=0, pady=10, padx=5, columnspan=2)
        self.save_button = ctk.CTkButton(frame, text="Save Results", command=self.save_single_results)
        self.save_button.grid(row=6, column=3, pady=10, padx=5, columnspan=2)


        style = ttk.Style()
        is_dark = ctk.get_appearance_mode() == "Dark"
        #bg_color = self["bg"] if is_dark else "#e0e0e0"
        bg_color ="#f0f0f0"
        print(f"Using background color: {bg_color}")
        style.configure("Custom.Treeview", background=bg_color, fieldbackground=bg_color, foreground="black")

        self.tree_single = ttk.Treeview(
        frame,
        columns=("S500","UC600","XM90","XM70","XM30","XM32","PM014","Price","Width"),
        show="headings",
        height=6,
        style="Custom.Treeview"
        )


        for col in self.tree_single["columns"]:
            self.tree_single.heading(col, text=col)
            self.tree_single.column(col, anchor="center", width=80)
        self.tree_single.grid(row=8, column=0, columnspan=5, sticky="nsew", padx=5, pady=5)

    def _wait_for_canvas_ready(self):
        if self.canvas.winfo_width() < 10 or self.canvas.winfo_height()<10:
            self.after(50, self._wait_for_canvas_ready)
        else:
            self._update_image_display(self.original_images[self.current_controller], center_if_needed=True)

    def _on_controller_select(self, new_ctrl: str):  # 🔧 Updated
        self.current_controller = new_ctrl
        self.zoom_factor = 0.23  # Reset zoom
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
        self.zoom_factor = 0.23
        pil_image = self.original_images[self.current_controller]
        self._update_image_display(pil_image, center_if_needed=True)

    def calculate_single(self):
        try:
            system_points = {k: int(v.get()) for k, v in self.inputs.items()}
            spare = int(self.spare_spin.get())
            system_points = {
                k: math.ceil(v * (1 + spare/100))
                for k, v in system_points.items()
            }
            ctrl = self.controllers[self.controller_choice.get()]

            expansions_max = [
                self.expansions_max_default[i]
                if self.expansion_vars[exp].get()
                else 0
                for i, exp in enumerate(["XM90","XM70","XM30","XM32"])
            ]

            def thread_fn():
                results = run_calculations(
                    system_points,
                    ctrl,
                    self.expansions,
                    expansions_max,
                    self.controllers["PM014"],
                    True
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

        top_frame = ctk.CTkFrame(frame)
        top_frame.pack(fill="x", padx=5, pady=(0, 10))

        # === Load Excel button ===
        self.load_excel_button = ctk.CTkButton(
            top_frame, text="Load", width=120, command=self.load_systems_excel
        )
        self.load_excel_button.pack(side="left", padx=10)

        # === Calculate button ===
        self.calculate_multi_button = ctk.CTkButton(
            top_frame, text="Calculate", width=120, command=self.calculate_multiple
        )
        self.calculate_multi_button.pack(side="left", padx=10)

        # === Controller dropdown ===
        self.multi_controller_choice = ctk.CTkOptionMenu(
            top_frame, values=["S500", "UC600"], width=100
        )
        self.multi_controller_choice.set("S500")
        self.multi_controller_choice.pack(side="left", padx=10)

        # === Expansion checkboxes ===
        self.multi_exp_vars = {}
        for exp in ["XM90", "XM70", "XM30", "XM32"]:
            cb = ctk.CTkCheckBox(top_frame, text=exp, width=80)
            cb.select()
            cb.pack(side="left", padx=3)
            self.multi_exp_vars[exp] = cb

        # === Spare % ===
        ctk.CTkLabel(top_frame, text="Spare %:").pack(side="left", padx=(10, 2))
        self.multi_spare_spin = ctk.CTkEntry(top_frame, width=40)
        self.multi_spare_spin.insert(0, "0")
        self.multi_spare_spin.pack(side="left", padx=(0, 5))

                # === Editable system input table ===
        self.multi_input_table = ttk.Treeview(frame, columns=("System", "BO", "BI", "UI", "AO", "AI", "PRESSURE"), show="headings", height=6)
        for col in self.multi_input_table["columns"]:
            self.multi_input_table.heading(col, text=col)
            self.multi_input_table.column(col, width=100, anchor="center")
        self.multi_input_table.pack(fill="both", expand=True, pady=5, padx=5)

        # === Output table ===
        self.multi_result_table = ttk.Treeview(frame, columns=("System","S500","UC600","XM90", "XM70", "XM30", "XM32", "PM014", "Price", "Width"), show="headings", height=6)
        for col in self.multi_result_table["columns"]:
            self.multi_result_table.heading(col, text=col)
            self.multi_result_table.column(col, width=85, anchor="center")
        self.multi_result_table.pack(fill="both", expand=True, pady=10, padx=1)

        # === Save button ===
        self.save_multi_button = ctk.CTkButton(
            frame, text="Save Results", width=120, command=self.save_multi_results
        )
        self.save_multi_button.pack(pady=(0, 5))


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
                values = [row[col] for col in required_cols]
                self.multi_input_table.insert("", "end", values=values)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file:\n{e}")

    def calculate_multiple(self):
        try:
            # 1. Gather input data from table
            rows = []
            for item in self.multi_input_table.get_children():
                values = self.multi_input_table.item(item)['values']
                rows.append(values)

            if not rows:
                messagebox.showwarning("No Data", "Please load or enter at least one system.")
                return

            df = pd.DataFrame(rows, columns=["System Name", "BO", "BI", "UI", "AO", "AI", "PRESSURE"])

            # 2. Validate numeric fields
            numeric_cols = ["BO", "BI", "UI", "AO", "AI", "PRESSURE"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors="raise")

            # 3. Get selected controller and expansions
            ctrl = self.controllers[self.multi_controller_choice.get()]
            expansions_max = [
                self.expansions_max_default[i]
                if self.multi_exp_vars[exp].get()
                else 0
                for i, exp in enumerate(["XM90", "XM70", "XM30", "XM32"])
            ]

            # 4. Get spare %
            spare = int(self.multi_spare_spin.get())

            # 5. Run calculation
            results_df = run_building_calculations(
                df,
                ctrl,
                self.expansions,
                expansions_max,
                self.controllers["PM014"],
                True,  # include PM014
                spare
            )
            print(results_df)

            # 6. Display results in table
            # Clear previous content and reconfigure columns
            self.multi_result_table.delete(*self.multi_result_table.get_children())

            # Dynamically assign new column headers
            columns = list(results_df.columns)
            self.multi_result_table["columns"] = columns

            for col in columns:
                self.multi_result_table.heading(col, text=col)
                self.multi_result_table.column(col, width=90, anchor="center")

            # Populate rows
            for _, row in results_df.iterrows():
                formatted_row = []
                for col in columns:
                    val = row[col]
                    if col in ("Price", "Width"):
                        formatted_row.append(f"{val:.2f}")
                    elif col == "System Name":
                        formatted_row.append(str(val))
                    else:
                        formatted_row.append(str(int(val)) if pd.notna(val) else "")
                self.multi_result_table.insert("", "end", values=formatted_row)

        except Exception as e:
            messagebox.showerror("Error", f"Calculation failed:\n{e}")

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


if __name__ == '__main__':
    app = App()
    app.mainloop()

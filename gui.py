import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pandas as pd
import threading
import os
import math
from PIL import Image

from core import Controller, fetch_prices, run_calculations, run_building_calculations

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Trane Controller & Expansion Calculator")
        self.geometry("900x540")

        # --- controllers & pricing setup ---
        self.controllers = self.initialize_controllers()
        self.expansions = [
            self.controllers["XM90"],
            self.controllers["XM70"],
            self.controllers["XM30"],
            self.controllers["XM32"],
        ]
        self.expansions_max_default = [5, 7, 34, 34]

        # --- load controller images ---
        self.controller_images = {
            name: ctk.CTkImage(
                Image.open(f"assets/{name}.png"), size=(300, 200)
            )
            for name in ["S500", "UC600"]
        }
        # keep a ref so they don't get garbage-collected
        self.current_image = self.controller_images["S500"]

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

        # --- allow image area to expand & center ---
        for r in range(1, 6):
            frame.grid_rowconfigure(r, weight=1)
        frame.grid_rowconfigure(7, weight=1)
        frame.grid_columnconfigure(2, weight=1)

        # --- central image label ---
        self.img_label = ctk.CTkLabel(frame, image=self.current_image, text="")
        self.img_label.grid(row=1, column=2, rowspan=6, sticky="nsew")

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

        ctk.CTkLabel(frame, text="Spare Points [%]").grid(row=1, column=3, sticky="w", padx=5)
        self.spare_spin = ctk.CTkEntry(frame, width=50)
        self.spare_spin.insert(0, "0")
        self.spare_spin.grid(row=1, column=4, pady=2, padx=(0,5), sticky="w")

        # --- expansions checkboxes ---
        self.expansion_vars = {}
        for idx, exp in enumerate(["XM90", "XM70", "XM30", "XM32"]):
            cb = ctk.CTkCheckBox(frame, text=f"Include {exp}")
            cb.select()
            cb.grid(row=2+idx, column=3, columnspan=2, sticky="w", padx=5)
            self.expansion_vars[exp] = cb

        # --- buttons ---
        ctk.CTkButton(frame, text="Calculate", command=self.calculate_single)\
            .grid(row=6, column=0, pady=10, padx=5, columnspan=2)
        self.save_button = ctk.CTkButton(frame, text="Save Results", command=self.save_single_results)
        self.save_button.grid(row=6, column=3, pady=10, padx=5, columnspan=2)

        # --- results table ---
        self.tree_single = ttk.Treeview(
            frame,
            columns=("S500","UC600","XM90","XM70","XM30","XM32","PM014","Price","Width"),
            show="headings",
            height=10
        )
        for col in self.tree_single["columns"]:
            self.tree_single.heading(col, text=col)
            self.tree_single.column(col, anchor="center", width=80)
        self.tree_single.grid(row=7, column=0, columnspan=5, sticky="nsew", padx=5, pady=10)

    def _on_controller_select(self, new_ctrl: str):
        """Swap the central image when controller changes."""
        img = self.controller_images[new_ctrl]
        self.img_label.configure(image=img)
        self.current_image = img  # keep reference

    def calculate_single(self):
        try:
            # 1) gather & adjust system points
            system_points = {k: int(v.get()) for k, v in self.inputs.items()}
            spare = int(self.spare_spin.get())
            system_points = {
                k: math.ceil(v * (1 + spare/100))
                for k, v in system_points.items()
            }
            ctrl = self.controllers[self.controller_choice.get()]

            # 2) determine expansion limits
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
                # Cast integer columns properly
                for col in results.columns:
                    if col not in ("Price", "Width"):
                        results[col] = results[col].astype(int)
                # Update the table
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



    def save_single_results(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files","*.csv")])
        if file_path:
            data = [self.tree_single.item(i)['values'] for i in self.tree_single.get_children()]
            df = pd.DataFrame(data, columns=self.tree_single["columns"])
            df.to_csv(file_path, index=False)
            messagebox.showinfo("Saved", f"Results saved to {os.path.basename(file_path)}")

    def build_multiple_system_tab(self):
        label = ctk.CTkLabel(self.tab_building, text="Multiple Systems tab coming next.")
        label.pack(pady=20)


if __name__ == '__main__':
    app = App()
    app.mainloop()

import pandas as pd
from itertools import product
import math
import requests
from io import StringIO
from collections import OrderedDict

ALL_EXPANSION_NAMES = ["XM90", "XM70", "XM30", "XM32"]
EXPECTED_COLUMNS = ["S500", "UC600", "S800", "XM90", "XM70", "XM30", "XM32", "PM014", "Price", "Width"]

class Controller:
    def __init__(self, name, price=0, power_AC=0, power_DC=0, width=0, UI=0, UIAO=0, BO=0, AI=0, BI=0, BIAO=0, PRESSURE=0, max_point_capacity=0):
        self.name = name
        self.price = price
        self.power_AC = power_AC
        self.power_DC = power_DC
        self.width = width
        self.BO = BO
        self.BI = BI
        self.UI = UI
        self.AI = AI
        self.UIAO = UIAO
        self.BIAO = BIAO
        self.PRESSURE = PRESSURE
        self.max_point_capacity = max_point_capacity

    def get_points(self, quantity):
        return {
            "BO": self.BO * quantity,
            "BI": self.BI * quantity,
            "UI": self.UI * quantity,
            "AI": self.AI * quantity,
            "UIAO": self.UIAO * quantity,
            "BIAO": self.BIAO * quantity,
            "PRESSURE": self.PRESSURE * quantity,
        }

class System:
    def __init__(self, system_points, system_controller, expansions_list, pm014, include_pm014):
        self.system_points = system_points
        self.system_controller = system_controller
        self.expansions = expansions_list  # list of Controller objects
        self.include_pm014 = include_pm014
        self.pm014 = pm014

    def _required_total_points(self):
        return int(sum(v for v in self.system_points.values() if isinstance(v, (int, float))))

    def _max_by_expansion(self, required_total_points: int):
        return {
            "XM90": math.ceil(required_total_points / 32),
            "XM70": math.ceil(required_total_points / 18),
            "XM30": math.ceil(required_total_points / 4),
            "XM32": math.ceil(required_total_points / 4),
        }

    def find_combinations(self):
        total_combinations = []

        required_total_points = self._required_total_points()
        exp_max_map = self._max_by_expansion(required_total_points)

        # Enabled expansion names
        enabled_names = [e.name for e in self.expansions]
        ranges = [range(exp_max_map[name] + 1) for name in enabled_names]

        for counts in product(*ranges) if ranges else [()]:
            # Build counts map for all expansions; default 0 for disabled
            counts_map = {name: 0 for name in ALL_EXPANSION_NAMES}
            for name, qty in zip(enabled_names, counts):
                counts_map[name] = qty

            # Compute points for this combo
            combination_points = self.get_combination_points({exp: counts_map[exp.name] for exp in self.expansions})
            if not self.valid_combination(combination_points):
                continue

            price = sum(exp.price * counts_map[exp.name] for exp in self.expansions)
            width = sum(exp.width * counts_map[exp.name] for exp in self.expansions)

            qty_pm014 = 0
            if self.include_pm014:
                total_xm30_32 = counts_map["XM30"] + counts_map["XM32"]
                total_xm90_70 = counts_map["XM90"] + counts_map["XM70"]
                qty_pm014 = max(0, math.ceil((total_xm30_32 - (2 * total_xm90_70) - 2) / 11))
                if self.system_controller.name == "S800":
                    qty_pm014 += 1

            controller_name = self.system_controller.name
            ordered = OrderedDict({"S500": 0, "UC600": 0, "S800": 0})
            ordered[controller_name] = 1
            for name in ALL_EXPANSION_NAMES:
                ordered[name] = counts_map[name]
            ordered["PM014"] = qty_pm014
            ordered["Price"] = round(price + self.system_controller.price + (self.pm014.price * qty_pm014), 2)
            ordered["Width"] = round(width + self.system_controller.width + (self.pm014.width * qty_pm014), 2)
            total_combinations.append(ordered)

        return self.filter_combinations(total_combinations)

    def get_combination_points(self, combination):
        total_points = self.system_controller.get_points(1)
        for expansion, quantity in combination.items():
            expansion_points = expansion.get_points(quantity)
            for key in total_points:
                total_points[key] += expansion_points[key]
        return total_points
        
    def valid_combination(self, total_points):
        sp = self.system_points
        tp = total_points
        checks = [
            sp.get("BO", 0) <= tp.get("BO", 0),
            sp.get("UI", 0) <= tp.get("UI", 0) + tp.get("UIAO", 0),
            sp.get("AO", 0) <= tp.get("BIAO", 0) + tp.get("UIAO", 0),
            sp.get("BI", 0) <= tp.get("BI", 0) + tp.get("BIAO", 0) + tp.get("UI", 0) + tp.get("UIAO", 0),
            sp.get("AI", 0) <= tp.get("AI", 0) + tp.get("UI", 0) + tp.get("UIAO", 0),
            sp.get("AI", 0) + sp.get("UI", 0) <= tp.get("AI", 0) + tp.get("UI", 0) + tp.get("UIAO", 0),
            sp.get("BI", 0) + sp.get("UI", 0) + sp.get("AO", 0) <= (
                tp.get("BI", 0) + tp.get("BIAO", 0) + tp.get("UI", 0) + tp.get("UIAO", 0)
            ),
            sp.get("BI", 0) + sp.get("UI", 0) + sp.get("AI", 0) + sp.get("AO", 0) <= (
                tp.get("BI", 0) + tp.get("BIAO", 0) + tp.get("UI", 0) + tp.get("UIAO", 0) + tp.get("AI", 0)
            ),
            sp.get("PRESSURE", 0) <= tp.get("PRESSURE", 0)
        ]
        return all(checks)

    def filter_combinations(self, combinations):
        # Always return a DataFrame with expected columns (even if empty)
        if not combinations:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)

        df = pd.DataFrame(combinations).sort_values(by="Price").reset_index(drop=True).head(500)

        # Add any missing columns with zeros, then reorder
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = 0.0 if col in ("Price", "Width") else 0
        df = df[EXPECTED_COLUMNS].copy()

        # Non-dominated filtering (Pareto) by price & module counts
        expansion_cols = ["XM90", "XM70", "XM30", "XM32", "PM014"]
        keep_rows = []
        for i, row_i in df.iterrows():
            is_redundant = False
            for j, row_j in df.iterrows():
                if i == j:
                    continue
                cheaper_or_equal = row_j["Price"] <= row_i["Price"]
                strictly_better_modules = all(row_j[c] <= row_i[c] for c in expansion_cols) and any(
                    row_j[c] < row_i[c] for c in expansion_cols
                )
                if cheaper_or_equal and strictly_better_modules:
                    is_redundant = True
                    break
            if not is_redundant:
                keep_rows.append(i)

        filtered_df = df.loc[keep_rows].copy()
        count_cols = [c for c in filtered_df.columns if c not in ("Price", "Width")]
        filtered_df[count_cols] = filtered_df[count_cols].astype(int)
        filtered_df = filtered_df.sort_values(by="Price").reset_index(drop=True)
        return filtered_df

class Enclosure:
    def __init__(self, rail_qty=0, rail_size=0, tx_qty=0):
        self.rail_qty = rail_qty
        self.rail_size = rail_size
        self.tx_qty = tx_qty

def fetch_prices(prices_url):
    try:
        response = requests.get(url=prices_url)
        response.raise_for_status()
        return pd.read_csv(StringIO(response.text), encoding="utf-8", sep=",", header=None)
    except Exception as e:
        raise RuntimeError("Failed to fetch prices") from e

def run_calculations(system_points, system_controller, expansions_list, pm014, include_pm014):
    return System(system_points, system_controller, expansions_list, pm014, include_pm014).find_combinations()

def run_building_calculations(building_df, system_controller, expansions_list, pm014, include_pm014, spare_points):
    building_df.columns = ["System Name", "BO", "BI", "UI", "AO", "AI", "PRESSURE"]
    for col in ["BO", "BI", "UI", "AO", "AI", "PRESSURE"]:
        building_df[col] = building_df[col].apply(lambda x: math.ceil(x * (1 + spare_points / 100)))
    results_list = []
    for row in building_df.itertuples(index=False):
        system_points = {"BO": row[1], "BI": row[2], "UI": row[3], "AO": row[4], "AI": row[5], "PRESSURE": row[6]}
        results = run_calculations(system_points, system_controller, expansions_list, pm014, include_pm014)
        results.reset_index(inplace=True, drop=True)
        row_result = results.iloc[0].tolist()
        row_result.insert(0, row[0])
        results_list.append(row_result)

    columns = ["System Name"] + EXPECTED_COLUMNS
    results_df = pd.DataFrame(results_list, columns=columns)
    totals = results_df.iloc[:, 1:].sum()
    totals.loc["System Name"] = "Total"
    results_df.loc[len(results_df.index)] = totals
    return results_df

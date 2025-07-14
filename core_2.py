import pandas as pd
from itertools import product, permutations
import math
import requests
from io import StringIO
from collections import OrderedDict


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
    def __init__(self, system_points, system_controller, expansions_list, expansions_max, pm014, include_pm014):
        self.system_points = system_points
        self.system_controller = system_controller
        self.expansions = expansions_list
        self.expansions_max = expansions_max
        self.include_pm014 = include_pm014
        self.pm014 = pm014

    def find_combinations(self):
        total_combinations = []
        range_lists = [range(x + 1) for x in self.expansions_max]

        for counts in product(*range_lists):
            combination = {exp: qty for exp, qty in zip(self.expansions, counts)}
            combination_points = self.get_combination_points(combination)
            if self.valid_combination(combination_points):
                price = sum(exp.price * qty for exp, qty in combination.items())
                width = sum(exp.width * qty for exp, qty in combination.items())
                qty_pm014 = 0

                if self.include_pm014:
                    total_xm30_32 = counts[2] + counts[3]
                    total_xm90_70 = counts[0] + counts[1]
                    qty_pm014 = max(0, math.ceil((total_xm30_32 - (2 * total_xm90_70) - 2) / 11))

                controller_name = self.system_controller.name
                combination_ordered = OrderedDict({"S500": 0, "UC600": 0})
                combination_ordered[controller_name] = 1

                for exp in self.expansions:
                    combination_ordered[exp.name] = combination[exp]
                combination_ordered["PM014"] = qty_pm014
                combination_ordered["Total Price"] = round(price + self.system_controller.price + (self.pm014.price * qty_pm014), 2)
                combination_ordered["Total Width"] = round(width + self.system_controller.width + (self.pm014.width * qty_pm014), 2)
                total_combinations.append(combination_ordered)

        return self.filter_combinations(total_combinations)

    def get_combination_points(self, combination):
        total_points = self.system_controller.get_points(1)
        for expansion, quantity in combination.items():
            expansion_points = expansion.get_points(quantity)
            for key in total_points:
                total_points[key] += expansion_points[key]
        return total_points

    def valid_combination(self, total_points):
        # Compare required system points against available points
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
        if not combinations:
            return pd.DataFrame(columns=["S500", "UC600", "XM90", "XM70", "XM30", "XM32", "PM014", "Price", "Width"])
        df = pd.DataFrame(combinations)
        df.columns = ["S500", "UC600", "XM90", "XM70", "XM30", "XM32", "PM014", "Price", "Width"]
        filtered = []
        for order in permutations(["XM90", "XM70", "XM30", "XM32"]):
            data = df.copy()
            for col in order:
                data = data[data[col] == data[col].min()]
            filtered.append(data)
        final = pd.concat(filtered, ignore_index=True).drop_duplicates().sort_values(by="Price")
        final.reset_index(drop=True, inplace=True)
        count_cols = [c for c in final.columns if c not in ("Price", "Width")]
        final[count_cols] = final[count_cols].astype(int)
        #print(final)
        return final


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


def run_calculations(system_points, system_controller, expansions_list, expansions_max, pm014, include_pm014):
    return System(system_points, system_controller, expansions_list, expansions_max, pm014, include_pm014).find_combinations()


def run_building_calculations(building_df, system_controller, expansions_list, expansions_max, pm014, include_pm014, spare_points):
    building_df.iloc[:, 1:-1] = building_df.iloc[:, 1:-1].applymap(lambda x: math.ceil(x * (1 + spare_points / 100)))
    building_df.columns = ["System Name", "BO", "BI", "UI", "AO", "AI", "PRESSURE"]
    results_list = []
    for row in building_df.itertuples(index=False):
        system_points = {"BO": row[1], "BI": row[2], "UI": row[3], "AO": row[4], "AI": row[5], "PRESSURE": row[6]}
        results = run_calculations(system_points, system_controller, expansions_list, expansions_max, pm014, include_pm014)
        results.reset_index(inplace=True, drop=True)
        row_result = results.iloc[0].tolist()
        row_result.insert(0, row[0])
        results_list.append(row_result)

# Build column headers
    columns = ["System Name"] + results.columns.tolist()
    results_df = pd.DataFrame(results_list, columns=columns)
    totals = results_df.iloc[:, 1:].sum()
    totals.loc["System Name"] = "Total"
    results_df.loc[len(results_df.index)] = totals
    return results_df

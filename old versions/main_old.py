import pandas as pd
from itertools import product,permutations
import tkinter as tk
from tkinter import ttk,messagebox

class Controller:
    def __init__(self,name,price=0,power_AC=0,power_DC=0,width=0,UI=0,UIAO=0,BO=0,AI=0,BI=0,BIAO=0,pressure=0,max_point_capacity=0):
        self.name=name
        self.price=price
        self.power_AC=power_AC
        self.power_DC=power_DC
        self.width=width
        self.BO=BO
        self.BI=BI
        self.UI=UI
        self.AI=AI
        self.UIAO=UIAO
        self.BIAO=BIAO
        self.pressure=pressure
        self.max_point_capacity=max_point_capacity

    def get_points(self,quantity):
        return {"BO":self.BO*quantity,
                "BI":self.BI*quantity,
                "UI":self.UI*quantity,
                "AI":self.AI*quantity,
                "UIAO":self.UIAO*quantity,
                "BIAO":self.BIAO*quantity,
                "pressure":self.pressure*quantity}
    
class System:
    def __init__(self,system_points,system_controller,expansions_list):
        self.system_points=system_points
        self.system_controller=system_controller
        self.expansions=expansions_list
    
    def find_combinations(self):
        total_combinations=[]
        max_xm90=5
        max_xm70=7
        max_xm30=34
        max_xm32=34
        for counts in product(range(max_xm90+1),range(max_xm70+1),range(max_xm30+1),range(max_xm32+1)): #Get all the possible options of expansions in a list of tuples
            combination={self.expansions[0]:counts[0],self.expansions[1]:counts[1],self.expansions[2]:counts[2],self.expansions[3]:counts[3]} #Create a dict with the quantity of each expansion
            combination_points=self.get_combination_points(combination) #get a dictionary with the total points per key
            if self.valid_combination(combination_points): #Verify if those total points meet the system requirements
                price=self.expansions[0].price*counts[0]+self.expansions[1].price*counts[1]+self.expansions[2].price*counts[2]+self.expansions[3].price*counts[3]
                width=self.expansions[0].width*counts[0]+self.expansions[1].width*counts[1]+self.expansions[2].width*counts[2]+self.expansions[3].width*counts[3]
                combination["Total Price"]=price
                combination["Total Width"]=width
                total_combinations.append(combination) #If True add the combination to the results
        sorted=self.filter_combinations(total_combinations) #Filter all the possible combinations to eliminate redundant options
        return sorted

    def get_combination_points(self,combination):
        total_points=self.system_controller.get_points(1) #Get the points of 1 controller
        for expansion,quantity in combination.items(): #Iterate the combination dict items to get the expasion type and qty
            expansion_points=expansion.get_points(quantity) #Of each exp type get the points
            for key in total_points: #Iterate for each Key of the points results (BO,BI, etc)
                total_points[key]+=expansion_points[key] #add to each key of the controller the expansion points
        return total_points #return a dictionary with all the points per key
    
    def valid_combination(self,total_points):
        points=[
        self.system_points["BO"]<=total_points["BO"],
        self.system_points["BI"]<=total_points["BI"]+total_points["BIAO"]+total_points["UI"]+total_points["UIAO"],
        self.system_points["UI"]<=total_points["UI"]+total_points["UIAO"],
        self.system_points["AO"]<=total_points["UIAO"]+total_points["BIAO"],
        self.system_points["AI"]<=total_points["UI"]+total_points["UIAO"]+total_points["AI"],
        self.system_points["pressure"]<=total_points["pressure"],
        (self.system_points["UI"]+self.system_points["AO"]+self.system_points["BI"]+self.system_points["AI"])<=(total_points["UI"]+total_points["UIAO"]+total_points["BI"]+total_points["BIAO"]+total_points["AI"])     
        ]
        return all(points) #Return True if the combination points meet all the system requirements

    def filter_combinations(self,total_combinations_dict):
        total_combinations_df=pd.DataFrame(total_combinations_dict) #Convert dictionary of Dataframe
        total_combinations_df.columns=["XM90","XM70","XM30","XM32","Total Price","Total Width"] 
        #total_combinations_df["Notes"]=None
        filter_order=list(permutations(["XM90","XM70","XM30","XM32"])) #Create a list with all the possible filter orders
        filetered_combinations=[]
        for order in filter_order: #Iterate each filter order
            filtered_data=total_combinations_df.copy()
            for column in order: #iterate each expansion
                min_value=filtered_data[column].min() #Find the lowest quantity of the expansion
                filtered_data=filtered_data[filtered_data[column]==min_value] #filtered the data per that min value
            filetered_combinations.append(filtered_data)
        total_filtered_data=pd.concat(filetered_combinations,ignore_index=True).drop_duplicates() #Eliminate duplicates
        sorted_by_price=total_filtered_data.sort_values(by="Total Price")
        sorted_by_price.reset_index(drop=True,inplace=True)
        print(sorted_by_price)
        return sorted_by_price

    def find_enclosures(self,enclosures,combination):
        max_24in=combination.sum()
        max_16in=combination.sum()
        #print(combination)
        for quantity in product(range(max_24in+1),range(max_16in+1)):
            combination_enclosures={enclosures[0]:quantity[0],enclosures[1]:quantity[1]}
            remaining_controllers=combination.sum()
            #while remaining_controllers>0:
            #    pass

        print(combination_enclosures)

class Enclosure:
    def __init__(self,rail_qty=0,rail_size=0,tx_qty=0):
        self.rail_qty=rail_qty
        self.rail_size=rail_size
        self.tx_qty=tx_qty

class GUI():
    def __init__(self,root):
        self.root=root
        self.root.title("Controller/Expansions Calculator")
        self.root.geometry("400x300")
        #System points
        tk.Label(self.root,text="System Points").grid(row=0,column=0,pady=10,columnspan=11)
        tk.Label(root,text="BO:").grid(row=1,column=0,sticky="e",padx=5)
        self.bo_entry=tk.Entry(root,width=2)
        self.bo_entry.grid(row=1,column=1)
        tk.Label(root,text="BI:").grid(row=1,column=2,sticky="e")
        self.bi_entry=tk.Entry(root,width=2)
        self.bi_entry.grid(row=1,column=3)
        tk.Label(root,text="UI:").grid(row=1,column=4,sticky="e")
        self.ui_entry=tk.Entry(root,width=2)
        self.ui_entry.grid(row=1,column=5)
        tk.Label(root,text="AO:").grid(row=1,column=6,sticky="e")
        self.ao_entry=tk.Entry(root,width=2)
        self.ao_entry.grid(row=1,column=7)
        tk.Label(root,text="AI:").grid(row=1,column=8,sticky="e")
        self.ai_entry=tk.Entry(root,width=2)
        self.ai_entry.grid(row=1,column=9)
        tk.Label(root,text="Pressure:").grid(row=1,column=10,sticky="e")
        self.pressure_entry=tk.Entry(root,width=2)
        self.pressure_entry.grid(row=1,column=11)
        #Dropdown for controller
        tk.Label(self.root,text="Select Controller:").grid(row=2,column=0,pady=10,columnspan=6)
        self.controller_type = tk.StringVar()
        self.controller_dropdown = ttk.Combobox(root, textvariable=self.controller_type, state="readonly")
        self.controller_dropdown['values'] = ("UC600", "S500")
        self.controller_dropdown.grid(row=2, column=5, columnspan=6)
        #Dropdown for filter type
        tk.Label(self.root,text="Filter Results by:").grid(row=3,column=0,pady=10,columnspan=6)
        self.filter_by = tk.StringVar()
        self.filter_dropdown = ttk.Combobox(root, textvariable=self.filter_by, state="readonly")
        self.filter_dropdown['values'] = ("By Price", "By Din lenght")
        self.filter_dropdown.grid(row=3, column=5, columnspan=6)
        #Default values
        self.bo_entry.insert(0,"5")
        self.bi_entry.insert(0,"5")
        self.ui_entry.insert(0,"5")
        self.ai_entry.insert(0,"5")
        self.ao_entry.insert(0,"5")
        self.pressure_entry.insert(0,"5")
        self.controller_dropdown.set("S500")
        self.filter_dropdown.set("By Price")
        #Generate button
        generate_button=tk.Button(root,text="Calculate",command=self.process_input)
        generate_button.grid(row=4,column=0,columnspan=11)
        #Create results table
        frame=tk.Frame(self.root, padx=10, pady=10)
        frame.grid(row=10, column=0)
        self.table = ttk.Treeview(frame, columns=("Result","XM90","XM70","XM30","XM32","Total Price","Total Width"), show="headings")
        self.table.heading("Result", text="Result")
        self.table.column("Result", width=10)
        self.table.heading("XM90", text="XM90")
        self.table.heading("XM70", text="XM70")
        self.table.heading("XM30", text="XM30")
        self.table.heading("XM32", text="XM32")
        self.table.heading("Total Price", text="Total Price")
        self.table.heading("Total Width", text="Total Width")
        self.table.grid(row=0, column=0, sticky="nsew")
        #comment here
    
    def process_input(self):
        try:
            bo=int(self.bo_entry.get())
            bi=int(self.bi_entry.get())
            ui=int(self.ui_entry.get())
            ao=int(self.ao_entry.get())
            ai=int(self.ai_entry.get())
            pressure=int(self.pressure_entry.get())
            controller=self.controller_type.get()
            if not controller:
                messagebox.showerror()


        except ValueError:
            messagebox.showerror("Please enter valid integer values points for system points")


def main():
    print("\nTrane Technologies")
    print("Controller/Expansions Calculator")
    #Initialize devices
    uc600=Controller(name="UC600",price=1500,power_AC=26,width=8.5,UI=8,UIAO=6,BO=4,pressure=1,max_point_capacity=120)
    S500=Controller(name="S500",price=1300,power_AC=24,width=5.65,AI=5,UI=2,BI=3,BO=9,BIAO=2,pressure=2,max_point_capacity=133)
    xm90=Controller(name="XM90",price=900,power_AC=50,width=8.5,UI=16,UIAO=8,BO=8)
    xm70=Controller(name="XM70",price=700,power_AC=26,width=8.5,UI=8,UIAO=6,BO=4,pressure=1)
    xm30=Controller(name="XM30",price=300,power_DC=120,width=2.11,UIAO=4)
    xm32=Controller(name="XM32",price=320,power_DC=100,width=2.82,BO=4)
    expansions=[xm90,xm70,xm30,xm32]
    #Define system points
    system_points={"BO":20,"BI":0,"UI":25,"AO":30,"AI":2,"pressure":1}
    chws=System(system_points,uc600,expansions)
    #Run Calculations
    print("Combinations:\n")
    results=chws.find_combinations()
    #Initialize Enclosures
    enc_24in=Enclosure(rail_qty=2,rail_size=14.88,tx_qty=2)
    enc_16in=Enclosure(rail_qty=1,rail_size=12,tx_qty=1)
    #chws.find_enclosures([enc_16in,enc_24in],results.loc[0])


if __name__=="__main__":
    main()
    root=tk.Tk()
    root.geometry("300x300")
    app=GUI(root)
    root.mainloop()



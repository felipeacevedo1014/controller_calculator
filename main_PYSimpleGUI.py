import pandas as pd
from itertools import product,permutations
import PySimpleGUI as sg
import threading
import math
import pathlib as Path
import requests
from io import BytesIO,StringIO
from collections import OrderedDict


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
    def __init__(self,system_points,system_controller,expansions_list,expansions_max,pm014,include_pm014):
        self.system_points=system_points
        self.system_controller=system_controller
        self.expansions=expansions_list
        self.expansions_max=expansions_max
        self.include_pm014=include_pm014
        self.pm014=pm014
    
    def find_combinations(self):
        total_combinations=[]
        for counts in product(range(self.expansions_max[0]+1),range(self.expansions_max[1]+1),range(self.expansions_max[2]+1),range(self.expansions_max[3]+1)): #Get all the possible options of expansions in a list of tuples
            combination={self.expansions[0]:counts[0],self.expansions[1]:counts[1],self.expansions[2]:counts[2],self.expansions[3]:counts[3]} #Create a dict with the quantity of each expansion
            combination_points=self.get_combination_points(combination) #get a dictionary with the total points per key
            if self.valid_combination(combination_points): #Verify if those total points meet the system requirements
                price=self.expansions[0].price*counts[0]+self.expansions[1].price*counts[1]+self.expansions[2].price*counts[2]+self.expansions[3].price*counts[3]
                width=self.expansions[0].width*counts[0]+self.expansions[1].width*counts[1]+self.expansions[2].width*counts[2]+self.expansions[3].width*counts[3]
                if self.include_pm014==True: #Calculations in user wants to include the PM014
                    total_xm30_32=counts[2]+counts[3]
                    total_xm90_70=counts[0]+counts[1]
                    qty_pm014=max(0,math.ceil((total_xm30_32-(2*total_xm90_70)-2)/11)) #each controller, XM70 or XM90 can power 2 XM30/32. so if there are more we need PM014
                    ##11 is the max ammount of expansiones the pm014 can power up
                if self.system_controller.name=="S500":
                    combination=OrderedDict([("S500",1),("UC600",0)]+list(combination.items()))
                else:
                    combination=OrderedDict([("S500",0),("UC600",1)]+list(combination.items()))
                combination["PM014"]=qty_pm014
                combination["Total Price"]=round((price+self.system_controller.price+(self.pm014.price)*qty_pm014),2)
                combination["Total Width"]=round((width+self.system_controller.width+(self.pm014.width)*qty_pm014),2)
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
        total_combinations_df.columns=["S500","UC600","XM90","XM70","XM30","XM32","PM014","Total Price","Total Width"] 
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
        print("Options:")
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

class GUI:
    def __init__(self):
        self.frame_system=sg.Frame("System Points",[
                    [sg.Text("BO:"),sg.InputText(default_text="5",size=(3),key="BO"),sg.Text("BI:"),sg.InputText(default_text="5",size=(3),key="BI"),
                     sg.Text("UI:"),sg.InputText(default_text="5",size=(3),key="UI"),sg.Text("AI:"),sg.InputText(default_text="5",size=(3),key="AI"),
                     sg.Text("AO:"),sg.InputText(default_text="5",size=(3),key="AO"),sg.Text("Pressure:"),sg.InputText(default_text="0",size=(2),key="pressure")],
                     [sg.Text("Select Controller: "),sg.DropDown(["S500","UC600"],default_value="S500",key="controller"),sg.Text("Spare Points [%]"),sg.Spin(values=list(range(0,100,1)),initial_value=0,key="-Spare_Points-",size=3)],
                     [sg.CB("Include XM90",default=True,key="inc_XM90"),sg.CB("Include XM70",default=True,key="inc_XM70"),sg.CB("Include XM30",default=True,key="inc_XM30"),sg.CB("Include XM32",default=True,key="inc_XM32")]],expand_x=True)
        self.frame_results=sg.Frame("Results",[
                    [sg.Table(values=[],headings=["Options","S500","UC600","XM90","XM70","XM30","XM32","PM014","Price","Width[in]"],justification="center",key="results_table",expand_x=True,enable_click_events=True,col_widths=[6,6,6,6,6,6,6,8,8],auto_size_columns=False,)],
                    ])
        self.tab_system=[[self.frame_system],
                     [sg.B("Calculate",key="-Calculate_System-"),sg.B("Exit",key="Exit")],
                     [self.frame_results],
                     [sg.B("Save Results",key="-Save_System-",visible=False),sg.B("Calculate Enclosures",key="bt_enclosures",visible=False)]]
        self.tab_multiple=[[sg.Frame("Load File",[
                        [sg.Text("Select Controller: "),sg.DropDown(["S500","UC600"],default_value="S500",key="Building_controller"),sg.Text("Spare Points [%]"),sg.Spin(values=list(range(0,100,1)),initial_value=0,key="-Spare_Building_Points-",size=3)],
                        [sg.CB("Include XM90",default=True,key="Building_inc_XM90"),sg.CB("Include XM70",default=True,key="Building_inc_XM70"),sg.CB("Include XM30",default=True,key="Building_inc_XM30"),sg.CB("Include XM32",default=True,key="Building_inc_XM32")],
                        [sg.InputText(key="-Building_File-",enable_events=True),sg.FileBrowse("Open Points",file_types=((("CSV File","*.csv"),("Excel File","*.xlsx"))),key="-Building_File-"),sg.B("Calculate",key="-Calculate_Building-")],
                        [sg.Table(values=[],headings=["System Name","BO","BI","UI","AO","AI","Pressure"],num_rows=8,justification="center",key="-Building_points-",expand_x=True,enable_click_events=True,col_widths=[14,6,6,6,6,6,10],auto_size_columns=False,)]
                        ],expand_x=True)],
                        [sg.Frame("Results",[
                        [sg.Table(values=[],headings=["System Name","S500","UC600","XM90","XM70","XM30","XM32","PM014","Total Price","Total Width [in]"],num_rows=8,justification="center",key="-Building_Results-",expand_x=True,enable_click_events=True,col_widths=[10,6,6,5,5,5,5,8,8],auto_size_columns=False)],
                        [sg.B("Save Results",key="-Save_building-",visible=True)]
                        ])]]
        self.prices=[1100,1000,600,500,400,300]
        self.col1=[[sg.Text("S500")],[sg.Text("UC600")],[sg.Text("XM90")],[sg.Text("XM70")],[sg.Text("XM30")],[sg.Text("XM32")]]
        self.col2=[[sg.Input(default_text=self.prices[0],key="S500_price",size=10)],
                   [sg.Input(default_text=self.prices[1],key="UC600_price",size=10)],
                   [sg.Input(default_text=self.prices[2],key="XM90_price",size=10)],
                   [sg.Input(default_text=self.prices[3],key="XM70_price",size=10)],
                   [sg.Input(default_text=self.prices[4],key="XM30_price",size=10)],
                   [sg.Input(default_text=self.prices[5],key="XM32_price",size=10)]
                   ]
        # self.tab_settings=[[sg.Frame("Prices",[
        #                 [sg.Col(self.col1),sg.Col(self.col2)]
        #])]]
        #self.layout = [[sg.TabGroup([[sg.Tab("Single System",self.tab_system),sg.Tab("Multiple Systems",self.tab_multiple),sg.Tab("Settings",self.tab_settings)]])
        #            ]]
        self.layout = [[sg.TabGroup([[sg.Tab("Single System",self.tab_system),sg.Tab("Multiple Systems",self.tab_multiple)]])
                    ]]

    def create_window(self):
        # Create the Window
        window = sg.Window(title="Trane Controller/Expansions Calculator",layout=self.layout,resizable=False,size=(560,440))
        return window

    def get_system_points(self):
        return self.system_points,self.controller

def run_calculations(window,system_points, system_controller, expansions_list,expansions_max,pm014,include_pm014):
    #system_points={"BO":20,"BI":0,"UI":25,"AO":30,"AI":2,"pressure":1}
    try:
        chws=System(system_points,system_controller,expansions_list,expansions_max,pm014,include_pm014)
        print("Combinations:\n")
        results=chws.find_combinations()
        results.reset_index(inplace=True)
        def convert_to_int(results):
            formatted_data=[]
            for row in results.values.tolist():
                formatted_row=[]
                for index,item in enumerate(row):
                    if index<6:
                        formatted_row.append(int(item))
                    else: 
                        formatted_row.append(item)
                    if index==0:
                        formatted_row[0]+=1
                formatted_data.append(formatted_row)
            return formatted_data
        window["results_table"].update(values=convert_to_int(results))

    except Exception as e:
        sg.popup_error("Combination not found! ")

def run_building_calculations(window,building_points_df, system_controller, expansions_list,expansions_max,pm014,include_pm014,spare_points):
    #system_points={"BO":20,"BI":0,"UI":25,"AO":30,"AI":2,"pressure":1}
    try:
        building_results=[]
        building_points_df.iloc[:,1:-1]=building_points_df.iloc[:,1:-1].map(lambda x: math.ceil(x*(1+spare_points/100)))
        building_points_df.columns=["System Name","BO","BI","UI","AO","AI","Pressure"]
        print(f"\n Spare Points: {spare_points}%")
        print(building_points_df)
        for row in building_points_df.itertuples(index=False):
            system_name=row[0]
            system_points={"BO":row[1],"BI":row[2],"UI":row[3],"AO":row[4],"AI":row[5],"pressure":row[6]}
            system=System(system_points,system_controller,expansions_list,expansions_max,pm014,include_pm014)
            results=system.find_combinations()
            results.reset_index(inplace=True,drop=True)
            system_results=results.iloc[0].tolist()
            system_results.insert(0,system_name)
            building_results.append(system_results)  
        building_results_df=pd.DataFrame(building_results)
        column_total=building_results_df.sum()
        building_results_df.loc["Total"]=column_total
        building_results_df.iloc[-1,0]="Total"
        print(building_results_df)
        window["-Building_Results-"].update(values=building_results_df.values.tolist())
    except Exception as e:
        sg.popup_error("Combination not found! ")

def main():
    print("\nTrane Technologies")
    print("Controller/Expansions Calculator")
    #Initialize devices
    uc600=Controller(name="UC600",price=955.04,power_AC=26,width=8.5,UI=8,UIAO=6,BO=4,pressure=1,max_point_capacity=120)
    s500=Controller(name="S500",price=436.72,power_AC=24,width=5.65,AI=5,UI=2,BI=3,BO=9,BIAO=2,pressure=2,max_point_capacity=133)
    xm90=Controller(name="XM90",price=1116.25,power_AC=50,width=8.5,UI=16,UIAO=8,BO=8)
    xm70=Controller(name="XM70",price=908.01,power_AC=26,width=8.5,UI=8,UIAO=6,BO=4,pressure=1)
    xm30=Controller(name="XM30",price=290.16,power_DC=120,width=2.11,UIAO=4)
    xm32=Controller(name="XM32",price=290.16,power_DC=100,width=2.82,BO=4)
    pm014=Controller(name="PM014",price=198.31,power_AC=20,width=5)
    uc600.price,s500.price,xm90.price,xm70.price,xm30.price,xm32.price,pm014.price=30,30,20,20,10,10,5    
    prices_url="https://raw.githubusercontent.com/felipeacevedo1014/controller_calculator/refs/heads/main/prices.csv"
    def fetch_prices(prices_url):
        try:
            response=requests.get(url=prices_url,verify=False)
            response.raise_for_status()
            url_data=StringIO(response.text)
            prices_df=pd.read_csv(url_data,encoding="utf-8",sep=",",header=None)
            return prices_df
        except Exception as e:
            sg.popup_error("Error updating the prices ",e)
            return None
    prices_df=fetch_prices(prices_url)
    print(prices_df)
    uc600.price,s500.price,xm90.price,xm70.price,xm30.price,xm32.price,pm014.price=list(prices_df.iloc[:,2])
    expansions_list=[xm90,xm70,xm30,xm32]
    expansions_max_default=[5,7,34,34]
    expansions_max=[0,0,0,0]
    app=GUI()
    window=app.create_window()
    while True:
        event,values=window.read()
        #print(event,values)        
        if event == sg.WIN_CLOSED:
            break
        if event == "Exit":
            if sg.popup_yes_no("Do you want to exit")=="Yes":
                exit()
        if "-Calculate_System-" in event:
            try:
                system_points={
                "BO":math.ceil((int(values["BO"]))*(1+int(values["-Spare_Points-"])/100)),
                "BI":math.ceil((int(values["BI"]))*(1+int(values["-Spare_Points-"])/100)),
                "UI":math.ceil((int(values["UI"]))*(1+int(values["-Spare_Points-"])/100)),
                "AO":math.ceil((int(values["AO"]))*(1+int(values["-Spare_Points-"])/100)),
                "AI":math.ceil((int(values["AI"]))*(1+int(values["-Spare_Points-"])/100)),
                "pressure":math.ceil((int(values["pressure"]))*(1+int(values["-Spare_Points-"])/100)),}
                print(system_points)  
                include_pm014=True
                system_controller=s500 if values["controller"]=="S500" else uc600
                expansions_max[0]=0 if values["inc_XM90"]==False else expansions_max_default[0]
                expansions_max[1]=0 if values["inc_XM70"]==False else expansions_max_default[1]
                expansions_max[2]=0 if values["inc_XM30"]==False else expansions_max_default[2]
                expansions_max[3]=0 if values["inc_XM32"]==False else expansions_max_default[3]
                if sum(system_points.values())>system_controller.max_point_capacity:
                   raise ValueError(f"The total system points {sum(system_points.values())} exceeds the controller capacity {system_controller.max_point_capacity}")
                threading.Thread(target=run_calculations, args=(window,system_points, system_controller, expansions_list,expansions_max,pm014,include_pm014), daemon=True).start() 
                window["-Save_System-"].update(visible=True)
            except Exception as e:
                sg.popup_error("Enter a valid input: ",e)

        #if "+CLICKED+" in event:
        #    window["bt_enclosures"].update(visible=True)
        if "-Save_System-" in event:
            file_name=sg.popup_get_file("Save As",save_as=True,no_window=True,file_types=((("CSV File","*.csv"),("Excel File","*.xlsx"))))
            if file_name:
                print(file_name)
                try:
                    table_values=window["results_table"].Values
                    data=pd.DataFrame(table_values,columns=["Option","S500","UC600","XM90","XM70","XM30","XM32","PM014","Total Price","Total Width [in]"])
                    if file_name.endswith(".csv"):
                        data.to_csv(file_name)
                        sg.popup("Results saved succesfully!")
                    elif file_name.endswith(".xlsx"):
                        data.to_excel(file_name,index=False)
                        sg.popup("Results saved succesfully!")
                    else: 
                        file_name+=".csv"
                        data.to_csv(file_name)
                        sg.popup("Results saved succesfully!")
                except Exception as e:
                    sg.popup_error("Error saving the results: ",e)
        if event == "-Building_File-":
            try:
                building_points_path=values["-Building_File-"]
                building_df=pd.read_excel(building_points_path)
                data=building_df.values.tolist()
                window["-Building_points-"].update(values=data)
            except Exception as e:
                sg.popup_error("Error loading the file: ",e)
        if "-Calculate_Building-" in event:
            building_points_path=values["-Building_File-"]
            if building_points_path:
                try:
                    building_df=pd.read_excel(building_points_path)
                    include_pm014=True
                    system_controller=s500 if values["Building_controller"]=="S500" else uc600
                    expansions_max[0]=0 if values["Building_inc_XM90"]==False else expansions_max_default[0]
                    expansions_max[1]=0 if values["Building_inc_XM70"]==False else expansions_max_default[1]
                    expansions_max[2]=0 if values["Building_inc_XM30"]==False else expansions_max_default[2]
                    expansions_max[3]=0 if values["Building_inc_XM32"]==False else expansions_max_default[3]
                    spare_points=int(values["-Spare_Building_Points-"])
                    threading.Thread(target=run_building_calculations, args=(window,building_df, system_controller, expansions_list,expansions_max,pm014,include_pm014,spare_points), daemon=True).start() 
                except Exception as e:
                    sg.popup_error("Error calculating the building points: ",e)
        if "-Save_building-" in event:
            file_name=sg.popup_get_file("Save As",save_as=True,no_window=True,file_types=((("CSV File","*.csv"),("Excel File","*.xlsx"))))
            if file_name:
                print(file_name)
                try:
                    table_values=window["-Building_Results-"].values
                    data=pd.DataFrame(table_values,columns=["System Name","S500","UC600","XM90","XM70","XM30","XM32","PM014","Total Price","Total Width [in]"])
                    if file_name.endswith(".csv"):
                        data.to_csv(file_name)
                        sg.popup("Results saved succesfully!")
                    elif file_name.endswith(".xlsx"):
                        data.to_excel(file_name,index=False)
                        sg.popup("Results saved succesfully!")
                    else: 
                        file_name+=".csv"
                        data.to_csv(file_name)
                        sg.popup("Results saved succesfully!")
                except Exception as e:
                    sg.popup_error("Error saving the results: ",e)

    window.close()

    #Define system points

    #Initialize Enclosures
    #enc_24in=Enclosure(rail_qty=2,rail_size=14.88,tx_qty=2)
    #enc_16in=Enclosure(rail_qty=1,rail_size=12,tx_qty=1)
    #chws.find_enclosures([enc_16in,enc_24in],results.loc[0])


if __name__=="__main__":
    main()


##Configure Settings
##Add spares to the Multiple systems




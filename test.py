import pandas as pd

dc={"Name":["Luis","Felipe"],"Last_name":["Acevedo","Gonzalez"]}
dataframe=pd.DataFrame(dc)
list=dataframe.values
print(list)
print(type(list))
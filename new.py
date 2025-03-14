import pyodbc
import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt

conn = pyodbc.connect('DRIVER={SQL Server};'
                      'SERVER=DESKTOP-SKCP13O\\SQLEXPRESS;'
                      'DATABASE=airbnb;'
                      'Trusted_connection=yes;')

cursor = conn.cursor()
query = 'select * from order'
cursor1 = cursor.execute("select * from orders")
for row in cursor1:
    print(row)

 # update city as null for order ids :  CA-2020-161389 , US-2021-156909
query = "update orders set city=NULL where order_id in ('CA-2020-161389' , 'US-2021-156909')"
cursor.execute(query)

# write a query to find orders where city is null (2 rows)
query1 = "select * from orders where city is null"
cursor_new = cursor.execute(query1)
for row in cursor_new:
    print(row)

# 3- write a query to get total profit, first order date and latest order date for each category
query_profit = "select Category,sum(Profit) from orders group by Category"
print(cursor.execute(query_profit))
for row in cursor_new:
    print(row)


columns = [column[0] for column in cursor.description]  
print("Column Names:", columns)
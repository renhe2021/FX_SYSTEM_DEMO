import openpyxl
wb = openpyxl.load_workbook('32463012_20260311_213038_eco.xlsx')
ws = wb.active
for row in ws.iter_rows(values_only=True):
    print(list(row))

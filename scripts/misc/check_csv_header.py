import csv
f = open(r"C:\Users\eli6-admin\Documents\eli6-surveillance\controllable_Webcams.csv")
r = csv.reader(f)
h = next(r)
print(h)
f.close()
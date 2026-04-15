import pandas as pd
import numpy as np
import os

print("="*60)
print("UAC CARE SYSTEM DATA PROCESSOR")
print("="*60)

# Load data
df = pd.read_csv('data/raw/HHS_Unaccompanied_Alien_Children_Program.csv', 
                 skipfooter=300, 
                 engine='python',
                 thousands=',')

df = df.dropna(how='all')
df['Date'] = pd.to_datetime(df['Date'])
df = df.dropna(subset=['Date'])
df = df.sort_values('Date').reset_index(drop=True)

# Clean column names
df.columns = df.columns.str.replace('*', '').str.strip()

# Convert numeric columns
numeric_cols = [
    'Children apprehended and placed in CBP custody',
    'Children in CBP custody',
    'Children transferred out of CBP custody',
    'Children in HHS Care',
    'Children discharged from HHS Care'
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')

df = df.dropna(subset=numeric_cols)

# Calculate metrics
df['Total_System_Load'] = df['Children in CBP custody'] + df['Children in HHS Care']
df['Net_Daily_Intake'] = df['Children transferred out of CBP custody'] - df['Children discharged from HHS Care']
df['7day_avg_load'] = df['Total_System_Load'].rolling(7).mean()
df['30day_avg_load'] = df['Total_System_Load'].rolling(30).mean()

# Save
os.makedirs('data/processed', exist_ok=True)
df.to_csv('data/processed/uac_data_clean.csv', index=False)

print(f"\n✅ SUCCESS!")
print(f"Records: {len(df)}")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
print(f"Avg load: {df['Total_System_Load'].mean():,.0f}")
print(f"File saved: data/processed/uac_data_clean.csv")

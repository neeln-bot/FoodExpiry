import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import os

if os.name == "nt":
    from winotify import Notification
else:
    Notification = None

# App settings
st.set_page_config(
    page_title="Food Expiry Alert System",
    page_icon="🥗",
    layout="wide"
)

st.title("🥗 Food Waste & Expiry Alert System")
st.write("Manage your food items and reduce food waste.")

# Connect to database
conn = sqlite3.connect("food.db")
cursor = conn.cursor()

# Create food table
cursor.execute("""
CREATE TABLE IF NOT EXISTS food (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    expiry_date TEXT NOT NULL
)
""")
conn.commit()

# Add food form
st.header("Add Food")

with st.form("food_form", clear_on_submit=True):
    name = st.text_input("Food Name")
    quantity = st.number_input(
        "Quantity", min_value=1, value=1, step=1
    )
    expiry = st.date_input(
        "Expiry Date",
        min_value=date.today(),
        value=date.today() + timedelta(days=1)
    )

    submitted = st.form_submit_button("Save Food")

    if submitted:
        if name.strip():
            cursor.execute(
                """
                INSERT INTO food (name, quantity, expiry_date)
                VALUES (?, ?, ?)
                """,
                (name.strip(), int(quantity), expiry.isoformat())
            )
            conn.commit()
            st.success("Food saved successfully!")
        else:
            st.error("Please enter a food name.")

# Read food items
cursor.execute("""
SELECT id, name, quantity, expiry_date
FROM food
ORDER BY expiry_date
""")
rows = cursor.fetchall()

st.header("My Food List")

if rows:
    data = []

    for item_id, food_name, qty, expiry_text in rows:
        expiry_date = date.fromisoformat(expiry_text)
        days_left = (expiry_date - date.today()).days

        if 0 <= days_left <= 3:
            toast = Notification(
                app_id="Food Expiry Alert",
                title="Food Expiry Alert",
                msg=f"{food_name} expires in {days_left} day(s)!",
                duration="short"
                )
            toast.show()
        
        if days_left < 0:
            status = "Expired"
        elif days_left <= 3:
            status = "Expiring Soon"
        else:
            status = "Fresh"

        data.append({
            "ID": item_id,
            "Food Name": food_name,
            "Quantity": qty,
            "Expiry Date": expiry_text,
            "Days Left": days_left,
            "Status": status
        })

    df = pd.DataFrame(data)
    st.dataframe(df, hide_index=True, use_container_width=True)

    # Summary
    st.header("Food Summary")
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Items", len(df))
    col2.metric(
        "Expiring Soon",
        int((df["Status"] == "Expiring Soon").sum())
    )
    col3.metric(
        "Expired Items",
        int((df["Status"] == "Expired").sum())
    )

    # Expiry alerts
    st.header("Expiry Alerts")
    alerts = df[
        df["Status"].isin(["Expired", "Expiring Soon"])
    ]

    if alerts.empty:
        st.success("No expiry alerts right now.")
    else:
        for _, item in alerts.iterrows():
            if item["Status"] == "Expired":
                st.error(f'{item["Food Name"]} has expired!')
            else:
                st.warning(
                    f'{item["Food Name"]} expires in '
                    f'{item["Days Left"]} day(s)!'
                )

    # Delete food item
    st.header("Delete Food")

    options = {
        f'{item["Food Name"]} (ID: {item["ID"]})': item["ID"]
        for _, item in df.iterrows()
    }

    selected = st.selectbox(
        "Select food item",
        list(options.keys())
    )

    if st.button("Delete Selected Food"):
        cursor.execute(
            "DELETE FROM food WHERE id = ?",
            (options[selected],)
        )
        conn.commit()
        conn.close()
        st.rerun()

else:
    st.info("No food items saved yet. Add your first food item.")

conn.close()

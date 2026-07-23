import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

# ===================== CONFIG =====================
CHROME_DRIVER_PATH = r"D:\FH5\chromedriver.exe"
URL = "http://116.58.20.67:1118/"
EXCEL_FILE = "ChildData City E.xlsx"

USERNAME = "ceo.rahimyarkhan@pshealthpunjab.com"
PASSWORD = "ceo.031003"
# =================================================

def age_in_weeks(dob):
    return (pd.Timestamp.today() - dob).days // 7

def vaccine_map(weeks):
    return {
        "penta1": weeks >= 6,
        "penta2": weeks >= 10,
        "penta3": weeks >= 14,
        "mr1": weeks >= 36,
        "mr2": weeks >= 60,
        "dpt": weeks >= 72
    }

# ---------- READ EXCEL ----------
df = pd.read_excel(EXCEL_FILE)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
df = df.dropna(subset=["child_id", "date_of_birth"])

print(f"📊 Records to process: {len(df)}")

# ---------- SETUP CHROME ----------
options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(
    service=Service(CHROME_DRIVER_PATH),
    options=options
)
wait = WebDriverWait(driver, 30)

# ---------- OPEN SITE ----------
driver.get(URL)

# ---------- LOGIN ----------
print("🔐 Logging in...")

wait.until(EC.element_to_be_clickable((By.NAME, "Email"))).send_keys(USERNAME)
driver.find_element(By.NAME, "Password").send_keys(PASSWORD)
driver.find_element(By.XPATH, "//button|//input[@type='submit']").click()

# Wait until dashboard loads
wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
time.sleep(3)
print("✅ Login successful")

# ---------- NAVIGATION (CRITICAL PART) ----------
print("📂 Navigating menu (JS click)...")

# Ensure submenu is visible (already expanded, but safe)
parent_menu = wait.until(
    EC.presence_of_element_located((
        By.XPATH,
        "//span[contains(text(),'Print Form') or contains(text(),'Validate Child')]"
    ))
)

# Find "Validate Data" link (sidebar)
validate_data = wait.until(
    EC.presence_of_element_located((
        By.XPATH,
        "//a[.//text()[contains(.,'Validate Data')]]"
    ))
)

# Scroll into view
driver.execute_script("arguments[0].scrollIntoView({block:'center'});", validate_data)
time.sleep(0.5)

# JavaScript click (MOST IMPORTANT)
driver.execute_script("arguments[0].click();", validate_data)

# Wait for Child ID input to confirm page load
wait.until(
    EC.presence_of_element_located((
        By.XPATH,
        "//input[@placeholder='Enter ChildId']"
    ))
)

print("✅ Validate Data page opened successfully")



# ---------- MAIN LOOP ----------
for index, row in df.iterrows():
    child_id = "UNKNOWN"
    try:
        child_id = str(row["child_id"]).strip()
        dob = pd.to_datetime(row["date_of_birth"], dayfirst=True, errors="coerce")

        if not child_id or pd.isna(dob):
            print(f"⏭️ Skipping row {index}")
            continue

        weeks = age_in_weeks(dob)
        status = vaccine_map(weeks)

        print(f"\n➡️ Processing Child ID: {child_id} | Age: {weeks} weeks")

        # ---------- CHILD ID INPUT ----------
        # Enter Child ID
        child_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Enter ChildId']"))
        )
        child_input.clear()
        child_input.send_keys(child_id)

        # 🔥 REAL SEARCH (ENTER)
        child_input.send_keys(Keys.ENTER)

        # Wait for result
        wait.until(EC.presence_of_element_located((By.XPATH, "//table//select")))


        # ---------- DROPDOWN HELPER ----------
        def set_dropdown(pos, val):
            dropdown = wait.until(
                EC.presence_of_element_located((By.XPATH, f"(//table//select)[{pos}]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dropdown)
            Select(dropdown).select_by_visible_text("Yes" if val else "No")

        # ---------- SET VACCINES ----------
        set_dropdown(1, status["penta1"])
        set_dropdown(2, status["penta2"])
        set_dropdown(3, status["penta3"])
        set_dropdown(4, status["mr1"])
        set_dropdown(5, status["mr2"])
        set_dropdown(6, status["dpt"])

        # ---------- UPDATE (JS CLICK) ----------
        update_btn = wait.until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(),'Update')]"))
        )
        driver.execute_script("arguments[0].click();", update_btn)

        time.sleep(2)

        # ---------- RESET FOR NEXT CHILD ----------
        child_input.clear()
        time.sleep(0.5)

        print(f"✅ Updated successfully: {child_id}")

    except Exception as e:
        print(f"❌ Failed Child ID {child_id}: {e}")

# ---------- CLOSE ----------
time.sleep(3)
driver.quit()
print("🎉 ALL CHILD RECORDS PROCESSED")

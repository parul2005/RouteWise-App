
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

np.random.seed(42)
N = 3000

distance = np.random.uniform(0.3, 15, N)   # km
hour = np.random.randint(8, 22, N)         # 8 AM se 9 PM
day = np.random.randint(0, 7, N)           # 0 = Monday ... 6 = Sunday

is_peak = ((hour >= 9) & (hour <= 11)) | ((hour >= 17) & (hour <= 20))
speed = np.where(is_peak, 15, 25)          # km/h
speed = np.where(day >= 5, speed + 3, speed)

travel_time = distance / speed * 60        # minutes
handling_time = 5                          # order dene mein lagne wale minutes
noise = np.random.normal(0, 2, N)
minutes = np.maximum(travel_time + handling_time + noise, 3)

df = pd.DataFrame({
    'distance_km': distance,
    'hour': hour,
    'day_of_week': day,
    'minutes': minutes
})

X = df[['distance_km', 'hour', 'day_of_week']]
y = df['minutes']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = {
    'Linear Regression': LinearRegression(),
    'Random Forest': RandomForestRegressor(n_estimators=100, min_samples_leaf=5, random_state=42)
}

for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    print(f"{name}: MAE = {mean_absolute_error(y_test, pred):.2f} min, R2 = {r2_score(y_test, pred):.3f}")

joblib.dump(models['Random Forest'], 'eta_model.pkl')
print("Model saved as eta_model.pkl")

rf = models['Random Forest']
for label, h, d in [("Monday 3 PM (normal)", 15, 0), ("Monday 6 PM (peak)", 18, 0), ("Sunday 3 PM", 15, 6)]:
    sample = pd.DataFrame([{'distance_km': 5, 'hour': h, 'day_of_week': d}])
    print(f"5 km, {label}: {rf.predict(sample)[0]:.1f} min")
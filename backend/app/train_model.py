import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib
import psycopg2
from config import DB_CONFIG

# Подключение к БД
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    df = pd.read_sql("SELECT * FROM match_features", conn)
    cursor.close()
    conn.close()
except psycopg2.Error as e:
    raise Exception(f"Ошибка подключения к БД: {e}")

# Проверка признаков
features = ["kills_diff", "deaths_diff", "assists_diff", "gold_diff", "damage_diff", 
            "damage_taken_diff", "cs_diff", "vision_diff", "mean_kda_diff", "team_kda_diff"]
print("Признаки в данных:", df.columns.tolist())


# Подготовка данных
X = df[features]
y = df["win_blue"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# Scaling
scaler = StandardScaler()
scaled_X_train = scaler.fit_transform(X_train)
scaled_X_test = scaler.transform(X_test)

# Обучение модели
lr_model = LogisticRegression(max_iter=500, solver="lbfgs")
lr_model.fit(scaled_X_train, y_train)

# Предсказания
y_pred = lr_model.predict(scaled_X_test)
y_proba = lr_model.predict_proba(scaled_X_test)[:, 1]

# Метрики
print(classification_report(y_test, y_pred))

# Коэффициенты модели
coef_df = pd.DataFrame({
    "feature": X.columns,
    "coef": lr_model.coef_[0]
}).sort_values(by="coef", ascending=False)
print("\nВлияние признаков:")
print(coef_df)

# Сохранение модели и scaler
joblib.dump(lr_model, "team_lr_model.pkl")
joblib.dump(scaler, "scaler.pkl")
print("Модель и scaler сохранены: team_lr_model.pkl, scaler.pkl")
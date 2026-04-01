# Import necessary libraries
import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Data pipeline for loading and preprocessing coffee crop sensor data
def load_and_preprocess_data(file_path):
    # Load data
    data = pd.read_csv(file_path)
    
    # Preprocessing steps (modify based on actual data format)
    data.dropna(inplace=True)  # Drop missing values
    # Add more preprocessing steps if necessary

    return data

# 2. Feature engineering for disease prediction
def feature_engineering(data):
    # Example feature engineering steps
    data['feature1'] = data['sensor_value1'] ** 2  # Example feature
    # Add more features as necessary
    features = data.drop('target', axis=1)  # Assuming 'target' is the label
    target = data['target']
    return features, target

# 3. Train/test split and model selection (Random Forest)
def train_model(features, target):
    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, random_state=42)
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    return model, X_test, y_test

# 4. Model evaluation with precision, recall, F1-score
def evaluate_model(model, X_test, y_test):
    y_pred = model.predict(X_test)
    print(classification_report(y_test, y_pred))
    print(confusion_matrix(y_test, y_pred))

# 5. Prediction functionality
def make_prediction(model, new_data):
    return model.predict(new_data)

# 6. Visualization of results
def visualize_results(y_test, y_pred):
    plt.figure(figsize=(10, 6))
    sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.show()

# 7. Model serialization for deployment
def save_model(model, file_name):
    with open(file_name, 'wb') as file:
        pickle.dump(model, file)

# Example usage
if __name__ == "__main__":
    # File path to the dataset
    file_path = 'path/to/your/coffee_data.csv'
    
    # Load and preprocess data
    data = load_and_preprocess_data(file_path)
    
    # Feature engineering
    features, target = feature_engineering(data)
    
    # Train model
    model, X_test, y_test = train_model(features, target)
    
    # Evaluate model
    evaluate_model(model, X_test, y_test)
    
    # Make predictions (example with a new data point)
    example_data = np.array([[1, 0, 1, ...]])  # Replace with actual feature values
    print("Prediction:", make_prediction(model, example_data))
    
    # Visualize results
    visualize_results(y_test, model.predict(X_test))
    
    # Save model
    save_model(model, 'disease_prediction_model.pkl')

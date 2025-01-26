import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np

from sklearn.preprocessing import StandardScaler


class PredictiveModel(nn.Module):
    def __init__(self, input_size, output_size):
        super(PredictiveModel, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, output_size),
            nn.Softmax(dim=1)  # Outputs probabilities
        )

    def forward(self, x):
        return self.fc(x)

import joblib
scaler = joblib.load("scaler.pkl")

input_size= 7
output_size = 1696
# Load the model from the file
loaded_model = PredictiveModel(input_size, output_size)  # Ensure the structure matches the saved model
loaded_model.load_state_dict(torch.load("newpredictive_model.pth"))
loaded_model.eval()  # Set the model to evaluation mode
print("Model loaded from newpredictive_model.pth")

unique_y = np.load("unique_y.npy")

def predict(data):
    new_data = [data]  # Example list (input without the leftmost number)


    # Preprocess the new data (scaling)
    new_data_scaled = scaler.transform(new_data)  # Use the same scaler from training
    new_data_tensor = torch.tensor(new_data_scaled, dtype=torch.float32)

    # Evaluate the model
    with torch.no_grad():
        predictions = loaded_model(new_data_tensor)
        probabilities = predictions.numpy()  # Convert to numpy array for easy handling


    # Display results
    print("Predicted probabilities:")
    result = {int(unique_y[i]) : float(prob) for i, prob in enumerate(probabilities[0])} #[]
    # for i, prob in enumerate(probabilities[0]):
    #     result.append((unique_y[i], prob))
    return result



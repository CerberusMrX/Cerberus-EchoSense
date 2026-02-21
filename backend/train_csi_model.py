#!/usr/bin/env python3
"""
CSI Model Training Script
Train LSTM model for CSI-based activity classification

Usage:
    python train_csi_model.py --data data/csi_samples/ --epochs 50

Requirements:
    - Collected CSI data files (from collect_csi_data.py)
    - TensorFlow 2.x
"""

import argparse
import json
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import tensorflow as tf
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

class CSIModelTrainer:
    def __init__(self, data_dir: str, window_size: int = 100):
        self.data_dir = Path(data_dir)
        self.window_size = window_size
        self.label_encoder = LabelEncoder()
        
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
    def load_data(self):
        """Load all CSI data files"""
        print(f"\n{'='*60}")
        print(f"Loading CSI Data")
        print(f"{'='*60}")
        print(f"Data directory: {self.data_dir}")
        
        all_samples = []
        all_labels = []
        
        json_files = list(self.data_dir.glob("*.json"))
        print(f"Found {len(json_files)} data files\n")
        
        for json_file in json_files:
            print(f"  Loading {json_file.name}...")
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            label = data['label']
            samples = data['samples']
            
            # Extract CSI sequences
            for sample in samples:
                all_samples.append(sample['csi'])
                all_labels.append(label)
                
            print(f"    ✓ {len(samples)} samples from '{label}' class")
        
        print(f"\n✓ Total samples loaded: {len(all_samples)}")
        
        # Create windowed sequences
        print(f"\nCreating windowed sequences (window size: {self.window_size})...")
        X, y = self._create_windows(all_samples, all_labels)
        
        print(f"  ✓ Created {len(X)} sequences")
        print(f"  ✓ Sequence shape: {X.shape}")
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        print(f"\nClass mapping:")
        for i, label in enumerate(self.label_encoder.classes_):
            count = np.sum(y_encoded == i)
            print(f"  {i}: {label} ({count} samples)")
        
        # Train/test split
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        
        print(f"\nTrain/Test Split:")
        print(f"  Training: {len(self.X_train)} sequences")
        print(f"  Testing: {len(self.X_test)} sequences")
        
    def _create_windows(self, samples, labels):
        """Create sliding windows from samples"""
        X = []
        y = []
        
        # Group by label to create windows
        label_groups = {}
        for sample, label in zip(samples, labels):
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(sample)
        
        # Create windows for each label group
        for label, group_samples in label_groups.items():
            # Sliding window
            for i in range(len(group_samples) - self.window_size + 1):
                window = group_samples[i:i+self.window_size]
                X.append(window)
                y.append(label)
        
        return np.array(X), np.array(y)
    
    def build_model(self, num_classes: int):
        """Build LSTM model architecture"""
        print(f"\n{'='*60}")
        print(f"Building LSTM Model")
        print(f"{'='*60}")
        
        model = models.Sequential([
            # LSTM layers
            layers.LSTM(128, return_sequences=True, input_shape=(self.window_size, 64)),
            layers.Dropout(0.3),
            layers.LSTM(64, return_sequences=True),
            layers.Dropout(0.3),
            layers.LSTM(32),
            layers.Dropout(0.3),
            
            # Dense layers
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(num_classes, activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='sparse_categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print(model.summary())
        
        return model
    
    def train(self, epochs: int = 50, batch_size: int = 32):
        """Train the model"""
        print(f"\n{'='*60}")
        print(f"Training Model")
        print(f"{'='*60}")
        print(f"Epochs: {epochs}")
        print(f"Batch size: {batch_size}\n")
        
        num_classes = len(self.label_encoder.classes_)
        model = self.build_model(num_classes)
        
        # Callbacks
        callbacks = [
            EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True
            ),
            ModelCheckpoint(
                'models/csi_lstm_best.h5',
                monitor='val_accuracy',
                save_best_only=True,
                verbose=1
            )
        ]
        
        # Train
        history = model.fit(
            self.X_train, self.y_train,
            validation_data=(self.X_test, self.y_test),
            epochs=epochs,
            batch_size=batch_size,
            callbacks=callbacks,
            verbose=1
        )
        
        # Evaluate
        print(f"\n{'='*60}")
        print(f"Evaluation")
        print(f"{'='*60}")
        
        test_loss, test_acc = model.evaluate(self.X_test, self.y_test, verbose=0)
        print(f"\nTest Accuracy: {test_acc*100:.2f}%")
        print(f"Test Loss: {test_loss:.4f}")
        
        # Save final model
        model_path = Path("models/csi_lstm.h5")
        model_path.parent.mkdir(exist_ok=True)
        model.save(str(model_path))
        
        print(f"\n✅ Model saved to: {model_path}")
        
        # Save label encoder
        import pickle
        encoder_path = Path("models/label_encoder.pkl")
        with open(encoder_path, 'wb') as f:
            pickle.dump(self.label_encoder, f)
        print(f"✅ Label encoder saved to: {encoder_path}")
        
        return model, history

def main():
    parser = argparse.ArgumentParser(description="Train CSI activity classifier")
    parser.add_argument("--data", "-d", required=True,
                       help="Directory with collected CSI data")
    parser.add_argument("--epochs", "-e", type=int, default=50,
                       help="Number of training epochs (default: 50)")
    parser.add_argument("--batch-size", "-b", type=int, default=32,
                       help="Batch size (default: 32)")
    parser.add_argument("--window-size", "-w", type=int, default=100,
                       help="Window size for sequences (default: 100)")
    
    args = parser.parse_args()
    
    # Check if data directory exists
    if not Path(args.data).exists():
        print(f"❌ Error: Data directory not found: {args.data}")
        print(f"\nCollect data first using:")
        print(f"  python collect_csi_data.py --label walking --duration 60")
        return
    
    # Train
    trainer = CSIModelTrainer(args.data, args.window_size)
    trainer.load_data()
    model, history = trainer.train(args.epochs, args.batch_size)
    
    print(f"\n{'='*60}")
    print(f"Training Complete!")
    print(f"{'='*60}")
    print(f"\nUpdate config.yaml:")
    print(f"  csi:")
    print(f"    use_ml_classifier: true")
    print(f"    model_path: 'models/csi_lstm.h5'")

if __name__ == "__main__":
    main()

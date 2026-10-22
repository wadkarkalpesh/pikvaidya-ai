#!/usr/bin/env python3
"""
PikVaidya AI — Model Architecture Factory
=========================================
Implements:
 - Model A: EfficientNet-B0 (Compound scaling, MBConv blocks)
 - Model B: MobileNetV3-Large (Ultra-efficient edge architecture for Indian farm devices)
 - Optional Baseline: ResNet-50 (Deep residual network benchmark)
Configurable for transfer learning on audited crop pathology classes.
"""

import torch
import torch.nn as nn
from torchvision import models


def build_model(model_name: str, num_classes: int = 5, pretrained: bool = True) -> nn.Module:
    """Builds and returns the requested vision architecture configured for num_classes."""
    name = model_name.lower().replace("-", "_")

    if name in ["model_a", "efficientnet_b0", "efficientnet"]:
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        
        # Replace classification head
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=0.3, inplace=True),
            nn.Linear(in_features, num_classes)
        )
        model.target_conv_layer = model.features[-1]  # Target layer for Grad-CAM
        model.arch_name = "EfficientNet-B0"

    elif name in ["model_b", "mobilenet_v3", "mobilenet_v3_large", "mobilenet"]:
        weights = models.MobileNet_V3_Large_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v3_large(weights=weights)
        
        # Replace classification head
        in_features = model.classifier[0].in_features
        model.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(),
            nn.Dropout(p=0.2),
            nn.Linear(256, num_classes)
        )
        model.target_conv_layer = model.features[-1]  # Target layer for Grad-CAM
        model.arch_name = "MobileNetV3-Large"

    elif name in ["baseline", "resnet50", "resnet_50"]:
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        model = models.resnet50(weights=weights)
        
        # Replace classification head
        in_features = model.fc.in_features
        model.fc = nn.Linear(in_features, num_classes)
        model.target_conv_layer = model.layer4[-1]  # Target layer for Grad-CAM
        model.arch_name = "ResNet-50"

    else:
        raise ValueError(f"Unsupported model architecture: '{model_name}'. Choose from 'efficientnet_b0', 'mobilenet_v3', 'resnet50'.")

    return model

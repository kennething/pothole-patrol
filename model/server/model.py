import torch
import torch.nn as nn
import timm

# Define the model name used during training (e.g., 'efficientnet_b0', 'resnet34', etc.)
MODEL_NAME = "efficientnet_b0" 

class PotholeModel(nn.Module):
    def __init__(self) -> None:
        super(PotholeModel, self).__init__()
        # Create a model via timm with 4 output classes/features for the bounding box coords (xmin, ymin, xmax, ymax)
        self.backbone = timm.create_model(MODEL_NAME, pretrained=False, num_classes=4)

    def forward(self, images, gt_bboxes=None):
        # Returns the predicted bounding box tensor(s)
        return self.backbone(images)
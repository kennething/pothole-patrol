import torch
import torch.nn as nn
import timm

# The checkpoint `length_of_pothole.pt` is a Res2Net-50 with a deep stem.
# Its state_dict keys are backbone.conv1.{0,1,3,4,6} (3-conv deep stem),
# backbone.layer1..4 with block counts [3, 4, 6, 3], Res2Net scale-4 splits
# (convs.0-2 / bns.0-2), an avg-pool downsample at layer2.0.pool, and a final
# backbone.fc of shape [4, 2048]. That is timm's "res2net50d".
MODEL_NAME = "res2net50d"

# Preprocessing used at training time. The checkpoint is an ImageNet-pretrained
# backbone fine-tuned for bounding-box regression, so inputs must be resized to
# IMG_SIZE and normalized with the ImageNet statistics.
IMG_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


class PotholeModel(nn.Module):
    def __init__(self, model_name: str = MODEL_NAME) -> None:
        super(PotholeModel, self).__init__()
        # 4 outputs = the bounding box coords (xmin, ymin, xmax, ymax).
        # The attribute MUST stay named `backbone`: every key in the checkpoint
        # is prefixed with "backbone.".
        self.backbone = timm.create_model(model_name, pretrained=False, num_classes=4)

    def forward(self, images, gt_bboxes=None):
        # Returns the predicted bounding box tensor(s)
        return self.backbone(images)


def load_pothole_model(path: str, device: str = "cpu") -> PotholeModel:
    """Build PotholeModel and load `path` into it once, for reuse across frames.

    Loads with strict=True on purpose: a silent key mismatch would leave the
    backbone at random initialization and produce meaningless severity scores.
    """
    model = PotholeModel()
    state_dict = torch.load(path, map_location=torch.device(device), weights_only=True)

    # Some training scripts wrap the weights in a checkpoint dict; this one does
    # not, but unwrap defensively if a wrapped checkpoint is ever dropped in.
    if isinstance(state_dict, dict) and "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model

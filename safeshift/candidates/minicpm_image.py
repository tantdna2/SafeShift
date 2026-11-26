"""RGB channel-axis repair for the hash-pinned MiniCPM-V-4 preprocessor.

Derived from openbmb/MiniCPM-V-4 image_processing_minicpmv.py at
6f69a8235885be89608f3a71ffd40695b379e1e7, preprocess (Apache-2.0).
The pinned OpenBMB model card licenses code under Apache-2.0. Licensed under the Apache License,
Version 2.0: https://www.apache.org/licenses/LICENSE-2.0
Distributed on an AS IS BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.

Modification: single already-decoded PIL RGB input has a known LAST channel
axis. Never infer it from height (1 or 3) and carry that guess through resizing.
All image operations below use the original pinned processor methods/settings.
"""
from .source import require


def rgb_image_inputs(ip, image):
    import numpy as np
    from transformers.image_utils import ChannelDimension, to_numpy_array
    from transformers.image_transforms import to_channel_dimension_format
    import importlib
    batch_class = importlib.import_module(type(ip).__module__).MiniCPMVBatchFeature
    require(image.mode == "RGB" and min(image.size) > 0, "RGB_NONEMPTY_REQUIRED")
    pixels, grids = [], []
    for tile in ip.get_sliced_images(image, max_slice_nums=None):
        array = to_numpy_array(tile).astype(np.float32) / 255
        require(array.ndim == 3 and array.shape[-1] == 3, "PIL_RGB_HWC_REQUIRED")
        array = ip.normalize(image=array, mean=ip.mean, std=ip.std,
                             input_data_format=ChannelDimension.LAST)
        array = to_channel_dimension_format(array, ChannelDimension.FIRST,
                                            input_channel_dim=ChannelDimension.LAST)
        pixels.append(ip.reshape_by_patch(array))
        grids.append(np.array((array.shape[1] // ip.patch_size, array.shape[2] // ip.patch_size)))
    return batch_class(data={"pixel_values": [pixels], "image_sizes": [[image.size]],
                             "tgt_sizes": [np.vstack(grids)]}, tensor_type="pt")

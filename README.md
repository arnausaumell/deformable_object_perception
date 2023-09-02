# Deformable object manipulation

* `cloth_rendering`: Blender Python API to render clothes. To generate a full dataset:
    * Generate shirt models from Blender using *shirt_generation.py* (open .py from Blender file *shirt_generation.blend*).
    * Run *cloth_blender.py* file to generate hanging-shirt images: `blender -b -P cloth_blender.py`
    * Run *cloth_blender_canonical.py* file to generate canonical-shirt images: `blender -b -P cloth_blender_canonical.py`
    * Run *bash.sh* file: `sh bash.sh scene_name`
    
* `pytorch_dense_correspondence`: code for dense object descriptors. The most relevant files are:
    * config/dense_correspondence/dataset/single_object/scene_name.yaml: specification of the dataset used to train the models
    * config/dense_correspondence/evaluation/evaluation.yaml: specification of the models path
    * config/dense_correspondence/training/training.yaml: specification of the training hyperparameters
    * dense_correspondence/training/training_tutorial.ipynb: train dense object descriptor network
    * dense_correspondence/evaluation/evaluation_quantitative_tutorial.ipynb: evaluate networks quantitatively
    * dense_correspondence/evaluation/evaluation_qualitative_tutorial.ipynb: evaluate networks qualitatively
    * dense_correspondence/evaluation/correspondences_robot.py: module to find correspondences between the canonical image and the image captured by the robot using a model
    * dense_correspondence/evaluation/plotting.py: plot results over robot images

## Dataset description

The dataset is created according to the following structure:
```
├── pdc
│   ├── logs_proto
│   │   ├── scene_name_1
│   │   │   ├── processed
│   │   │   │   ├── depth_values
│   │   │   │   │   ├── depth-cam0-0-119.exr
│   │   │   │   │   ├── depth-cam1-0-119.exr
│   │   │   │   │   ├── depth-cam2-0-119.exr
│   │   │   │   │   ├──         ...
│   │   │   │   ├── image_masks
│   │   │   │   │   ├── mask-cam0-0-119.png
│   │   │   │   │   ├── mask-cam1-0-119.png
│   │   │   │   │   ├── mask-cam2-0-119.png
│   │   │   │   │   ├──         ...
│   │   │   │   │   ├── visible_mask-cam0-0-119.png
│   │   │   │   │   ├── visible_mask-cam1-0-119.png
│   │   │   │   │   ├── visible_mask-cam2-0-119.png
│   │   │   │   │   ├──         ...
│   │   │   │   ├── images
│   │   │   │   │   ├── depth-cam0-0-119.png
│   │   │   │   │   ├── depth-cam1-0-119.png
│   │   │   │   │   ├── depth-cam2-0-119.png
│   │   │   │   │   ├──         ...
│   │   │   │   │   ├── knots_info_pre.json
│   │   │   │   │   ├── knots_info.json
│   │   │   │   │   ├── rgb-cam0-0-119.png
│   │   │   │   │   ├── rgb-cam1-0-119.png
│   │   │   │   │   ├── rgb-cam2-0-119.png
│   │   │   │   │   ├──         ...
│   │   ├── scene_name_2
│   │   ├──     ...
```

The files' naming format is:
* `rgb-cam2-0-119.png`: image taken from camX on episode Y at frame Z
* `depth-cam0-0-119.png`: depth image of the image taken from camX on episode Y at frame Z
* `depth-camX-Y-Z.exr`: depth values of the image taken from camX on episode Y at frame Z
* `mask-cam0-0-119.png`: 0-1 mask of the image taken from camX on episode Y at frame Z
* `visible_mask-cam0-0-119.png`: visible mask of the image taken from camX on episode Y at frame Z
* `knots_info_pre.json`: point annotations before depth correction
* `knots_info.json`: point annotations after depth correction
